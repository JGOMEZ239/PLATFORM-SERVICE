from __future__ import annotations

import uuid
from dataclasses import dataclass

from domain.models.entities import RequestEvent, RequestStatus, ServiceRequest
from domain.policies.validation import RequestValidator
from domain.ports.repository import RequestRepositoryPort
from shared.schemas import CreateRequestPayload


@dataclass
class CreateRequestResult:
    record: ServiceRequest
    created: bool


class RequestService:
    def __init__(self, repository: RequestRepositoryPort, validator: RequestValidator):
        self.repository = repository
        self.validator = validator

    def create(self, payload: CreateRequestPayload, idempotency_key: str | None) -> CreateRequestResult:
        if idempotency_key:
            existing = self.repository.get_by_idempotency_key(idempotency_key)
            if existing:
                return CreateRequestResult(record=existing, created=False)

        request_id = str(uuid.uuid4())

        auto_tags = [
            f"service:{payload.service_name}",
            f"team:{payload.team}",
            f"environment:{payload.environment}",
        ]
        existing_prefixes = {t.split(":", 1)[0] for t in payload.spec.tags if ":" in t}
        for tag in auto_tags:
            if tag.split(":", 1)[0] not in existing_prefixes:
                payload.spec.tags.append(tag)

        validation = self.validator.validate(payload)
        status = RequestStatus.APPROVED if validation.is_valid else RequestStatus.REJECTED
        reason = None if validation.is_valid else "; ".join(validation.errors)

        request = ServiceRequest(
            request_id=request_id,
            request_type=payload.request_type,
            service_name=payload.service_name,
            team=payload.team,
            environment=payload.environment,
            requested_by=payload.requested_by,
            spec=payload.spec.model_dump(),
            status=status,
            status_reason=reason,
            idempotency_key=idempotency_key,
        )
        record = self.repository.create_request(request)

        self._emit_lifecycle_events(request_id, payload, validation)

        return CreateRequestResult(record=record, created=True)

    def _emit_lifecycle_events(self, request_id: str, payload: CreateRequestPayload, validation) -> None:
        events = [
            ("REQUEST_RECEIVED", {"request_type": payload.request_type, "service_name": payload.service_name}),
            ("VALIDATION_STARTED", {"request_type": payload.request_type}),
            ("VALIDATION_FINISHED", {"is_valid": validation.is_valid, "errors": validation.errors}),
        ]

        if validation.is_valid:
            events.append(("REQUEST_APPROVED", {"next_status": RequestStatus.APPROVED.value}))
        else:
            events.append(("REQUEST_REJECTED", {"reason": validation.errors}))

        for event_type, event_payload in events:
            self.repository.add_event(
                RequestEvent(
                    event_id=str(uuid.uuid4()),
                    request_id=request_id,
                    event_type=event_type,
                    event_payload=event_payload,
                )
            )

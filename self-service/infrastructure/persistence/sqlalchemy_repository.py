from __future__ import annotations

from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.models.entities import (
    ProvisionedResource,
    RequestEvent,
    RequestStatus,
    ServiceRequest,
)
from domain.ports.repository import RequestRepositoryPort
from infrastructure.persistence.orm_models import (
    ProvisionedResourceRecord,
    RequestEventRecord,
    ServiceRequestRecord,
)


def _record_to_entity(record: ServiceRequestRecord) -> ServiceRequest:
    return ServiceRequest(
        request_id=record.request_id,
        request_type=record.request_type,
        service_name=record.service_name,
        team=record.team,
        environment=record.environment,
        requested_by=record.requested_by,
        spec=record.spec_json,
        status=record.status,
        status_reason=record.status_reason,
        idempotency_key=record.idempotency_key,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _event_record_to_entity(record: RequestEventRecord) -> RequestEvent:
    return RequestEvent(
        event_id=record.event_id,
        request_id=record.request_id,
        event_type=record.event_type,
        event_payload=record.event_payload,
        correlation_id=record.correlation_id,
        created_at=record.created_at,
    )


def _resource_record_to_entity(record: ProvisionedResourceRecord) -> ProvisionedResource:
    return ProvisionedResource(
        resource_id=record.resource_id,
        request_id=record.request_id,
        resource_type=record.resource_type,
        resource_name=record.resource_name,
        resource_metadata=record.resource_metadata,
        created_at=record.created_at,
    )


class SqlAlchemyRequestRepository(RequestRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def get_by_idempotency_key(self, key: str) -> ServiceRequest | None:
        stmt = select(ServiceRequestRecord).where(ServiceRequestRecord.idempotency_key == key)
        record = self.session.execute(stmt).scalar_one_or_none()
        return _record_to_entity(record) if record else None

    def create_request(self, request: ServiceRequest) -> ServiceRequest:
        record = ServiceRequestRecord(
            request_id=request.request_id,
            request_type=request.request_type,
            service_name=request.service_name,
            team=request.team,
            environment=request.environment,
            requested_by=request.requested_by,
            spec_json=request.spec,
            status=request.status,
            status_reason=request.status_reason,
            idempotency_key=request.idempotency_key,
        )
        self.session.add(record)
        self.session.flush()
        return _record_to_entity(record)

    def get_request(self, request_id: str) -> ServiceRequest | None:
        record = self.session.get(ServiceRequestRecord, request_id)
        return _record_to_entity(record) if record else None

    def list_requests(
        self,
        *,
        status: RequestStatus | None = None,
        team: str | None = None,
        environment: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ServiceRequest]:
        stmt = select(ServiceRequestRecord)
        if status:
            stmt = stmt.where(ServiceRequestRecord.status == status)
        if team:
            stmt = stmt.where(ServiceRequestRecord.team == team)
        if environment:
            stmt = stmt.where(ServiceRequestRecord.environment == environment)
        stmt = stmt.order_by(ServiceRequestRecord.created_at.desc()).limit(limit).offset(offset)
        records = self.session.execute(stmt).scalars().all()
        return [_record_to_entity(r) for r in records]

    def add_event(self, event: RequestEvent) -> RequestEvent:
        record = RequestEventRecord(
            event_id=event.event_id,
            request_id=event.request_id,
            event_type=event.event_type,
            event_payload=event.event_payload,
            correlation_id=event.correlation_id,
        )
        self.session.add(record)
        self.session.flush()
        return _event_record_to_entity(record)

    def list_events(
        self, request_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[RequestEvent]:
        stmt = (
            select(RequestEventRecord)
            .where(RequestEventRecord.request_id == request_id)
            .order_by(RequestEventRecord.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        records = self.session.execute(stmt).scalars().all()
        return [_event_record_to_entity(r) for r in records]

    def count_events(self, request_id: str) -> int:
        stmt = (
            select(sa_func.count())
            .select_from(RequestEventRecord)
            .where(RequestEventRecord.request_id == request_id)
        )
        return self.session.execute(stmt).scalar_one()

    def claim_next_approved(self) -> ServiceRequest | None:
        stmt = (
            select(ServiceRequestRecord)
            .where(ServiceRequestRecord.status == RequestStatus.APPROVED)
            .order_by(ServiceRequestRecord.created_at.asc())
            .limit(1)
        )
        record = self.session.execute(stmt).scalar_one_or_none()
        if not record:
            return None
        record.status = RequestStatus.PROVISIONING
        record.status_reason = None
        self.session.flush()
        return _record_to_entity(record)

    def mark_succeeded(
        self, request_id: str, resource_id: str, metadata: dict[str, Any]
    ) -> ServiceRequest:
        record = self.session.get(ServiceRequestRecord, request_id)
        if record is None:
            raise ValueError(f"request {request_id} not found")
        record.status = RequestStatus.SUCCEEDED
        record.status_reason = None
        self.session.add(
            ProvisionedResourceRecord(
                resource_id=resource_id,
                request_id=request_id,
                resource_type=record.request_type,
                resource_name=metadata.get("bucket_name", resource_id),
                resource_metadata=metadata,
            )
        )
        self.session.flush()
        return _record_to_entity(record)

    def mark_failed(self, request_id: str, reason: str) -> ServiceRequest:
        record = self.session.get(ServiceRequestRecord, request_id)
        if record is None:
            raise ValueError(f"request {request_id} not found")
        record.status = RequestStatus.FAILED
        record.status_reason = reason
        self.session.flush()
        return _record_to_entity(record)

    def get_resource_by_request_id(self, request_id: str) -> ProvisionedResource | None:
        stmt = select(ProvisionedResourceRecord).where(
            ProvisionedResourceRecord.request_id == request_id
        )
        record = self.session.execute(stmt).scalar_one_or_none()
        return _resource_record_to_entity(record) if record else None

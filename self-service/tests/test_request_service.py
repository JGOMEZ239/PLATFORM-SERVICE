from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from domain.models.entities import RequestStatus, ServiceRequest
from domain.policies.validation import RequestValidator, ValidationResult
from domain.ports.repository import RequestRepositoryPort
from domain.services.request_service import RequestService
from shared.schemas import BucketSpec, CreateRequestPayload


def _make_payload() -> CreateRequestPayload:
    return CreateRequestPayload(
        request_type="storage_bucket",
        service_name="my-svc",
        team="platform",
        environment="qa",
        requested_by="tester",
        spec=BucketSpec(
            bucket_name="my-svc-qa-data",
            region="us-east-1",
            versioning=True,
            encryption="AES256",
            public_access=False,
            tags=["team:platform", "env:qa"],
        ),
    )


class FakeRepository(RequestRepositoryPort):
    def __init__(self):
        self.requests: dict[str, ServiceRequest] = {}
        self.events = []
        self._idempotency_map: dict[str, ServiceRequest] = {}

    def get_by_idempotency_key(self, key):
        return self._idempotency_map.get(key)

    def create_request(self, request):
        self.requests[request.request_id] = request
        if request.idempotency_key:
            self._idempotency_map[request.idempotency_key] = request
        return request

    def get_request(self, request_id):
        return self.requests.get(request_id)

    def list_requests(self, **kwargs):
        return list(self.requests.values())

    def add_event(self, event):
        self.events.append(event)
        return event

    def list_events(self, request_id, **kwargs):
        return [e for e in self.events if e.request_id == request_id]

    def count_events(self, request_id):
        return len([e for e in self.events if e.request_id == request_id])

    def claim_next_approved(self):
        return None

    def mark_succeeded(self, request_id, resource_id, metadata):
        r = self.requests[request_id]
        r.status = RequestStatus.SUCCEEDED
        return r

    def mark_failed(self, request_id, reason):
        r = self.requests[request_id]
        r.status = RequestStatus.FAILED
        return r

    def get_resource_by_request_id(self, request_id):
        return None


class TestRequestService:
    def test_create_valid_request_approved(self):
        repo = FakeRepository()
        service = RequestService(repo, RequestValidator())
        result = service.create(_make_payload(), idempotency_key=None)

        assert result.created
        assert result.record.status == RequestStatus.APPROVED
        assert len(repo.events) == 4  # RECEIVED, VAL_STARTED, VAL_FINISHED, APPROVED

    def test_create_invalid_request_rejected(self):
        repo = FakeRepository()
        service = RequestService(repo, RequestValidator())
        payload = _make_payload()
        payload.spec.public_access = True
        result = service.create(payload, idempotency_key=None)

        assert result.created
        assert result.record.status == RequestStatus.REJECTED
        assert len(repo.events) == 4  # RECEIVED, VAL_STARTED, VAL_FINISHED, REJECTED

    def test_idempotency_returns_existing(self):
        repo = FakeRepository()
        service = RequestService(repo, RequestValidator())
        result1 = service.create(_make_payload(), idempotency_key="key-1")
        result2 = service.create(_make_payload(), idempotency_key="key-1")

        assert result1.created
        assert not result2.created
        assert result1.record.request_id == result2.record.request_id

    def test_different_idempotency_keys_create_separate(self):
        repo = FakeRepository()
        service = RequestService(repo, RequestValidator())
        result1 = service.create(_make_payload(), idempotency_key="key-1")
        result2 = service.create(_make_payload(), idempotency_key="key-2")

        assert result1.created
        assert result2.created
        assert result1.record.request_id != result2.record.request_id

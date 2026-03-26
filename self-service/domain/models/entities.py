from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    PROVISIONING = "PROVISIONING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class ServiceRequest:
    request_id: str
    request_type: str
    service_name: str
    team: str
    environment: str
    requested_by: str
    spec: dict[str, Any]
    status: RequestStatus
    status_reason: str | None = None
    idempotency_key: str | None = None
    resource_id: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class RequestEvent:
    event_id: str
    request_id: str
    event_type: str
    event_payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime | None = None


@dataclass
class ProvisionedResource:
    resource_id: str
    request_id: str
    resource_type: str
    resource_name: str
    resource_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

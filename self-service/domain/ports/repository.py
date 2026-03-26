from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from domain.models.entities import (
    ProvisionedResource,
    RequestEvent,
    RequestStatus,
    ServiceRequest,
)


class RequestRepositoryPort(ABC):
    @abstractmethod
    def get_by_idempotency_key(self, key: str) -> ServiceRequest | None: ...

    @abstractmethod
    def create_request(self, request: ServiceRequest) -> ServiceRequest: ...

    @abstractmethod
    def get_request(self, request_id: str) -> ServiceRequest | None: ...

    @abstractmethod
    def list_requests(
        self,
        *,
        status: RequestStatus | None = None,
        team: str | None = None,
        environment: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ServiceRequest]: ...

    @abstractmethod
    def add_event(self, event: RequestEvent) -> RequestEvent: ...

    @abstractmethod
    def list_events(
        self, request_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[RequestEvent]: ...

    @abstractmethod
    def count_events(self, request_id: str) -> int: ...

    @abstractmethod
    def claim_next_approved(self) -> ServiceRequest | None: ...

    @abstractmethod
    def mark_succeeded(
        self, request_id: str, resource_id: str, metadata: dict[str, Any]
    ) -> ServiceRequest: ...

    @abstractmethod
    def mark_failed(self, request_id: str, reason: str) -> ServiceRequest: ...

    @abstractmethod
    def get_resource_by_request_id(self, request_id: str) -> ProvisionedResource | None: ...


class ProvisionerPort(ABC):
    @abstractmethod
    def provision_bucket(self, request_id: str, spec: dict[str, Any]) -> dict[str, Any]: ...


class UnitOfWorkPort(ABC):
    @abstractmethod
    def __enter__(self) -> UnitOfWorkPort: ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @property
    @abstractmethod
    def repository(self) -> RequestRepositoryPort: ...

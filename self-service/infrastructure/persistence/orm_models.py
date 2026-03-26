from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from domain.models.entities import RequestStatus


class Base(DeclarativeBase):
    pass


class ServiceRequestRecord(Base):
    __tablename__ = "service_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_name: Mapped[str] = mapped_column(String(120), nullable=False)
    team: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    spec_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status"), nullable=False
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[RequestEventRecord]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class RequestEventRecord(Base):
    __tablename__ = "request_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_requests.request_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    request: Mapped[ServiceRequestRecord] = relationship(back_populates="events")


class ProvisionedResourceRecord(Base):
    __tablename__ = "provisioned_resources"

    resource_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_requests.request_id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

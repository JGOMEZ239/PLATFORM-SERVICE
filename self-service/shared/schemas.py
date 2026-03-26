from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BucketSpec(BaseModel):
    bucket_name: str = Field(min_length=3, max_length=63)
    region: Literal["us-east-1", "us-east-2"]
    versioning: bool = True
    encryption: Literal["AES256", "aws:kms"]
    public_access: bool = False
    tags: list[str]


class CreateRequestPayload(BaseModel):
    request_type: Literal["storage_bucket"]
    service_name: str = Field(min_length=3, max_length=120)
    team: str = Field(min_length=2, max_length=120)
    environment: Literal["qa", "stg", "prod"]
    requested_by: str = Field(min_length=3, max_length=120)
    spec: BucketSpec


class RequestEventResponse(BaseModel):
    event_id: str
    event_type: str
    event_payload: dict[str, Any]
    correlation_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestResponse(BaseModel):
    request_id: str
    request_type: str
    service_name: str
    team: str
    environment: str
    requested_by: str
    status: str
    status_reason: str | None
    spec: dict[str, Any]
    resource_id: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class CreateRequestAccepted(BaseModel):
    request_id: str
    status: str
    message: str


class PaginatedRequests(BaseModel):
    items: list[RequestResponse]
    limit: int
    offset: int


class PaginatedEvents(BaseModel):
    items: list[RequestEventResponse]
    total: int
    limit: int
    offset: int

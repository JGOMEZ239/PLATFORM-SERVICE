from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from domain.models.entities import RequestStatus
from domain.policies.validation import RequestValidator
from domain.services.request_service import RequestService
from infrastructure.persistence.database import get_session, init_db, ping_database
from infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from infrastructure.observability.logging import configure_logging
from shared.config import settings
from shared.schemas import (
    CreateRequestAccepted,
    CreateRequestPayload,
    PaginatedEvents,
    PaginatedRequests,
    RequestEventResponse,
    RequestResponse,
)

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Platform Self Service API", version="1.0.0", lifespan=lifespan)


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: confirms the process is running."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness probe: confirms the database is reachable."""
    ping_database()
    return {"status": "ready"}


@app.post(
    "/api/v1/requests",
    response_model=CreateRequestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
)
def create_request(
    payload: CreateRequestPayload,
    response: Response,
    session: Session = Depends(get_session),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
):
    correlation_id = x_correlation_id or str(uuid.uuid4())
    response.headers["X-Correlation-Id"] = correlation_id

    with SqlAlchemyUnitOfWork(session) as uow:
        service = RequestService(uow.repository, RequestValidator())
        result = service.create(payload, idempotency_key=idempotency_key)
        uow.commit()

    record = result.record

    if not result.created:
        response.status_code = status.HTTP_200_OK
        return CreateRequestAccepted(
            request_id=record.request_id,
            status=record.status.value,
            message="Request already exists for provided Idempotency-Key",
        )

    logger.info(
        "request stored",
        extra={
            "request_id": record.request_id,
            "correlation_id": correlation_id,
            "stage": "api",
            "status": record.status.value,
        },
    )
    message = (
        "Request accepted and approved for provisioning"
        if record.status == RequestStatus.APPROVED
        else "Request rejected during validation"
    )
    return CreateRequestAccepted(
        request_id=record.request_id, status=record.status.value, message=message
    )


@app.get(
    "/api/v1/requests",
    response_model=PaginatedRequests,
    dependencies=[Depends(require_api_key)],
)
def list_requests(
    session: Session = Depends(get_session),
    request_status: str | None = Query(None, alias="status"),
    team: str | None = Query(None),
    environment: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    parsed_status = None
    if request_status:
        try:
            parsed_status = RequestStatus(request_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid status: {request_status}",
            )

    with SqlAlchemyUnitOfWork(session) as uow:
        items = uow.repository.list_requests(
            status=parsed_status, team=team, environment=environment, limit=limit, offset=offset
        )

    return PaginatedRequests(
        items=[
            RequestResponse(
                request_id=r.request_id,
                request_type=r.request_type,
                service_name=r.service_name,
                team=r.team,
                environment=r.environment,
                requested_by=r.requested_by,
                status=r.status.value,
                status_reason=r.status_reason,
                spec=r.spec,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in items
        ],
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/v1/requests/{request_id}",
    response_model=RequestResponse,
    dependencies=[Depends(require_api_key)],
)
def get_request(request_id: str, session: Session = Depends(get_session)):
    with SqlAlchemyUnitOfWork(session) as uow:
        record = uow.repository.get_request(request_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request not found")
        resource = uow.repository.get_resource_by_request_id(request_id)

    return RequestResponse(
        request_id=record.request_id,
        request_type=record.request_type,
        service_name=record.service_name,
        team=record.team,
        environment=record.environment,
        requested_by=record.requested_by,
        status=record.status.value,
        status_reason=record.status_reason,
        spec=record.spec,
        resource_id=resource.resource_id if resource else None,
        result=resource.resource_metadata if resource else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@app.get(
    "/api/v1/requests/{request_id}/events",
    response_model=PaginatedEvents,
    dependencies=[Depends(require_api_key)],
)
def list_request_events(
    request_id: str,
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        record = uow.repository.get_request(request_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request not found")
        events = uow.repository.list_events(request_id, limit=limit, offset=offset)
        total = uow.repository.count_events(request_id)

    return PaginatedEvents(
        items=[
            RequestEventResponse(
                event_id=e.event_id,
                event_type=e.event_type,
                event_payload=e.event_payload,
                correlation_id=e.correlation_id,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
        limit=limit,
        offset=offset,
    )

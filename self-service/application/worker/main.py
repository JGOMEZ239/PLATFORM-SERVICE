from __future__ import annotations

import logging
import time
import uuid

from domain.models.entities import RequestEvent
from infrastructure.persistence.database import init_db, session_scope
from infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from infrastructure.observability.logging import configure_logging
from infrastructure.provisioners.mock_provisioner import MockProvisioner
from shared.config import settings

configure_logging()
logger = logging.getLogger(__name__)


def process_once() -> bool:
    with session_scope() as session:
        uow = SqlAlchemyUnitOfWork(session)
        record = uow.repository.claim_next_approved()
        if not record:
            return False

        request_id = record.request_id
        correlation_id = str(uuid.uuid4())

        uow.repository.add_event(
            RequestEvent(
                event_id=str(uuid.uuid4()),
                request_id=request_id,
                event_type="PROVISIONING_STARTED",
                event_payload={"request_type": record.request_type},
                correlation_id=correlation_id,
            )
        )
        logger.info(
            "provisioning started",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "stage": "worker",
                "status": record.status.value,
            },
        )

        try:
            provisioner = MockProvisioner()
            result = provisioner.provision_bucket(request_id=request_id, spec=record.spec)
            uow.repository.mark_succeeded(
                request_id=request_id,
                resource_id=result["resource_id"],
                metadata=result,
            )
            uow.repository.add_event(
                RequestEvent(
                    event_id=str(uuid.uuid4()),
                    request_id=request_id,
                    event_type="PROVISIONING_FINISHED",
                    event_payload=result,
                    correlation_id=correlation_id,
                )
            )
            uow.repository.add_event(
                RequestEvent(
                    event_id=str(uuid.uuid4()),
                    request_id=request_id,
                    event_type="REQUEST_COMPLETED",
                    event_payload={"final_status": "SUCCEEDED"},
                    correlation_id=correlation_id,
                )
            )
            logger.info(
                "provisioning finished",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "stage": "worker",
                    "status": "SUCCEEDED",
                },
            )
        except Exception:
            session.rollback()
            uow_retry = SqlAlchemyUnitOfWork(session)
            uow_retry.repository.mark_failed(request_id=request_id, reason="provisioning error")
            uow_retry.repository.add_event(
                RequestEvent(
                    event_id=str(uuid.uuid4()),
                    request_id=request_id,
                    event_type="PROVISIONING_FAILED",
                    event_payload={"error": "provisioning error"},
                    correlation_id=correlation_id,
                )
            )
            logger.exception(
                "provisioning failed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "stage": "worker",
                    "status": "FAILED",
                },
            )
        return True


def main() -> None:
    init_db()
    logger.info("worker started", extra={"stage": "worker"})
    while True:
        processed = process_once()
        if not processed:
            time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()

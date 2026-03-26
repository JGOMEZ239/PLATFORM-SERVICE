from __future__ import annotations

from sqlalchemy.orm import Session

from domain.ports.repository import RequestRepositoryPort, UnitOfWorkPort
from infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRequestRepository


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session: Session):
        self._session = session
        self._repository = SqlAlchemyRequestRepository(session)

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    @property
    def repository(self) -> RequestRepositoryPort:
        return self._repository

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from application.api.main import app
from infrastructure.persistence.database import get_session
from infrastructure.persistence.orm_models import Base

_test_engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False, class_=Session)


def _override_get_session():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = _override_get_session


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def client():
    return TestClient(app)


VALID_PAYLOAD = {
    "request_type": "storage_bucket",
    "service_name": "my-svc",
    "team": "platform",
    "environment": "qa",
    "requested_by": "tester",
    "spec": {
        "bucket_name": "my-svc-qa-data",
        "region": "us-east-1",
        "versioning": True,
        "encryption": "AES256",
        "public_access": False,
        "tags": ["team:platform", "env:qa"],
    },
}


class TestHealthEndpoints:
    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_ready(self, client):
        res = client.get("/ready")
        assert res.status_code == 200
        assert res.json() == {"status": "ready"}


class TestCreateRequest:
    def test_create_valid_returns_202(self, client):
        res = client.post("/api/v1/requests", json=VALID_PAYLOAD)
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "APPROVED"
        assert "request_id" in data
        assert "X-Correlation-Id" in res.headers

    def test_create_invalid_returns_202_rejected(self, client):
        payload = {**VALID_PAYLOAD, "spec": {**VALID_PAYLOAD["spec"], "public_access": True}}
        res = client.post("/api/v1/requests", json=payload)
        assert res.status_code == 202
        assert res.json()["status"] == "REJECTED"

    def test_idempotency_returns_200(self, client):
        headers = {"Idempotency-Key": "test-key-123"}
        res1 = client.post("/api/v1/requests", json=VALID_PAYLOAD, headers=headers)
        res2 = client.post("/api/v1/requests", json=VALID_PAYLOAD, headers=headers)
        assert res1.status_code == 202
        assert res2.status_code == 200
        assert res1.json()["request_id"] == res2.json()["request_id"]

    def test_correlation_id_echoed(self, client):
        res = client.post(
            "/api/v1/requests",
            json=VALID_PAYLOAD,
            headers={"X-Correlation-Id": "corr-abc"},
        )
        assert res.headers["X-Correlation-Id"] == "corr-abc"


class TestGetRequest:
    def test_get_existing_request(self, client):
        create_res = client.post("/api/v1/requests", json=VALID_PAYLOAD)
        request_id = create_res.json()["request_id"]
        res = client.get(f"/api/v1/requests/{request_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["request_id"] == request_id
        assert data["service_name"] == "my-svc"

    def test_get_nonexistent_returns_404(self, client):
        res = client.get("/api/v1/requests/nonexistent")
        assert res.status_code == 404


class TestListRequests:
    def test_list_returns_items(self, client):
        client.post("/api/v1/requests", json=VALID_PAYLOAD)
        res = client.get("/api/v1/requests")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert "limit" in data
        assert "offset" in data

    def test_list_filter_by_team(self, client):
        client.post("/api/v1/requests", json=VALID_PAYLOAD)
        res = client.get("/api/v1/requests?team=platform")
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["team"] == "platform"

    def test_list_filter_by_invalid_status(self, client):
        res = client.get("/api/v1/requests?status=INVALID")
        assert res.status_code == 400


class TestListEvents:
    def test_list_events_with_pagination(self, client):
        create_res = client.post("/api/v1/requests", json=VALID_PAYLOAD)
        request_id = create_res.json()["request_id"]
        res = client.get(f"/api/v1/requests/{request_id}/events?limit=2&offset=0")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) <= 2

    def test_list_events_nonexistent_returns_404(self, client):
        res = client.get("/api/v1/requests/nonexistent/events")
        assert res.status_code == 404

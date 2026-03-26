from __future__ import annotations

import pytest

from domain.policies.validation import RequestValidator, ValidationResult
from shared.schemas import BucketSpec, CreateRequestPayload


def _make_payload(**overrides) -> CreateRequestPayload:
    defaults = {
        "request_type": "storage_bucket",
        "service_name": "my-svc",
        "team": "platform",
        "environment": "qa",
        "requested_by": "tester",
        "spec": BucketSpec(
            bucket_name="my-svc-qa-data",
            region="us-east-1",
            versioning=True,
            encryption="AES256",
            public_access=False,
            tags=["team:platform", "env:qa"],
        ),
    }
    spec_overrides = overrides.pop("spec_overrides", {})
    defaults.update(overrides)
    if spec_overrides:
        spec_dict = defaults["spec"].model_dump()
        spec_dict.update(spec_overrides)
        defaults["spec"] = BucketSpec(**spec_dict)
    return CreateRequestPayload(**defaults)


class TestRequestValidator:
    def setup_method(self):
        self.validator = RequestValidator()

    def test_valid_payload_passes(self):
        result = self.validator.validate(_make_payload())
        assert result.is_valid
        assert result.errors == []

    def test_invalid_bucket_name_pattern(self):
        result = self.validator.validate(
            _make_payload(spec_overrides={"bucket_name": "AB-INVALID!"})
        )
        assert not result.is_valid
        assert any("lowercase" in e for e in result.errors)

    def test_bucket_name_wrong_prefix(self):
        result = self.validator.validate(
            _make_payload(spec_overrides={"bucket_name": "wrong-prefix-data"})
        )
        assert not result.is_valid
        assert any("must start with" in e for e in result.errors)

    def test_public_access_rejected(self):
        result = self.validator.validate(
            _make_payload(spec_overrides={"public_access": True})
        )
        assert not result.is_valid
        assert any("public_access" in e for e in result.errors)

    def test_invalid_encryption(self):
        payload = _make_payload()
        payload.spec.encryption = "INVALID"
        result = self.validator.validate(payload)
        assert not result.is_valid
        assert any("encryption" in e for e in result.errors)

    def test_missing_tags(self):
        result = self.validator.validate(
            _make_payload(spec_overrides={"tags": ["notvalid"]})
        )
        assert not result.is_valid
        assert any("key:value" in e for e in result.errors)

    def test_prod_requires_us_east_1(self):
        result = self.validator.validate(
            _make_payload(
                environment="prod",
                spec_overrides={"bucket_name": "my-svc-prod-data", "region": "us-east-2"},
            )
        )
        assert not result.is_valid
        assert any("us-east-1" in e for e in result.errors)

    def test_prod_us_east_1_passes(self):
        result = self.validator.validate(
            _make_payload(
                environment="prod",
                spec_overrides={"bucket_name": "my-svc-prod-data", "region": "us-east-1"},
            )
        )
        assert result.is_valid

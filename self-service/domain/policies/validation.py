from __future__ import annotations

import re
from dataclasses import dataclass

from shared.schemas import CreateRequestPayload


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]


BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


class RequestValidator:
    def validate(self, payload: CreateRequestPayload) -> ValidationResult:
        errors: list[str] = []

        bucket_name = payload.spec.bucket_name
        if not BUCKET_PATTERN.match(bucket_name):
            errors.append(
                "bucket_name must use lowercase letters, numbers, dots or hyphens only"
            )

        expected_prefix = f"{payload.service_name}-{payload.environment}-"
        if not bucket_name.startswith(expected_prefix):
            errors.append(
                f"bucket_name must start with '{expected_prefix}'"
            )

        if payload.spec.public_access:
            errors.append("public_access must be false")

        if payload.spec.encryption not in {"AES256", "aws:kms"}:
            errors.append("encryption must be AES256 or aws:kms")

        for tag in payload.spec.tags:
            if ":" not in tag:
                errors.append(f"tag '{tag}' must follow key:value format")

        if payload.environment == "prod" and payload.spec.region != "us-east-1":
            errors.append("prod requests must target us-east-1")

        return ValidationResult(is_valid=not errors, errors=errors)

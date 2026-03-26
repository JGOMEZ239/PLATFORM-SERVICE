from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.ports.repository import ProvisionerPort
from shared.config import settings


class MockProvisioner(ProvisionerPort):
    def provision_bucket(self, request_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        resource_id = f"bucket/{spec['bucket_name']}"
        result = {
            "resource_id": resource_id,
            "bucket_name": spec["bucket_name"],
            "region": spec["region"],
            "versioning": spec["versioning"],
            "encryption": spec["encryption"],
            "public_access": spec["public_access"],
            "tags": spec["tags"],
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
            "provisioner": "mock",
        }

        artifacts_dir = Path(settings.artifacts_dir)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / f"{request_id}.json"
        artifact_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

"""In-memory mock dataset (reseedable without process restart)."""

from __future__ import annotations

import os
from typing import Any

from mock_connectors.fixtures.company_generator import dataset_to_json_dict, generate_dataset


class ConnectorState:
    """Holds the active dataset + seed; used by GitHub/Linear routers and /admin."""

    def __init__(self) -> None:
        self.seed = int(os.environ.get("VECTOR_MOCK_SEED", "42"))
        self.data: dict[str, Any] = dataset_to_json_dict(generate_dataset(self.seed))

    def reseed(self, seed: int) -> None:
        self.seed = seed
        self.data = dataset_to_json_dict(generate_dataset(seed))


state = ConnectorState()

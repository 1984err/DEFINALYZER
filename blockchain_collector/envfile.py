"""Small `.env` loader for RPC endpoints without an external dependency."""

from __future__ import annotations

import os
from pathlib import Path


def load_environment_file(path: str | Path) -> None:
    """Load simple KEY=VALUE entries without replacing existing variables."""

    env_path = Path(path)

    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(
                f"Invalid environment entry at {env_path}:{line_number}."
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ValueError(
                f"Invalid environment variable name at "
                f"{env_path}:{line_number}."
            )

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)

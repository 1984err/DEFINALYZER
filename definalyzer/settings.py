"""Non-secret application settings stored beneath the generated workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


SETTINGS_SCHEMA_VERSION = 1
DEFAULT_SETTINGS = {
    "schema_version": SETTINGS_SCHEMA_VERSION,
    "llm": {
        "provider": "hermes",
        "executable": None,
        "timeout_seconds": 900,
    },
}


class SettingsManager:
    def __init__(self, workspace_root: str | Path) -> None:
        self.path = Path(workspace_root).resolve() / "settings.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": SETTINGS_SCHEMA_VERSION,
                "llm": dict(DEFAULT_SETTINGS["llm"]),
            }

        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Settings are invalid JSON: {self.path}: {exc.msg}"
            ) from exc

        self._validate(document)
        return document

    def configure_hermes(
        self,
        *,
        executable: str | None = None,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        if timeout_seconds <= 0:
            raise ValueError("Provider timeout must be positive.")

        document = {
            "schema_version": SETTINGS_SCHEMA_VERSION,
            "llm": {
                "provider": "hermes",
                "executable": executable,
                "timeout_seconds": timeout_seconds,
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(document, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return document

    @staticmethod
    def _validate(document: Any) -> None:
        if not isinstance(document, dict):
            raise ValueError("Settings must be a JSON object.")
        if document.get("schema_version") != SETTINGS_SCHEMA_VERSION:
            raise ValueError("Unsupported settings schema version.")
        llm = document.get("llm")
        if not isinstance(llm, dict):
            raise ValueError("Settings must contain an llm object.")
        if llm.get("provider") != "hermes":
            raise ValueError("Configured LLM provider is not supported.")
        executable = llm.get("executable")
        if executable is not None and not isinstance(executable, str):
            raise ValueError("LLM executable must be text or null.")
        timeout = llm.get("timeout_seconds")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("LLM timeout_seconds must be a positive integer.")

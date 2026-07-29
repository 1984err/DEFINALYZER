"""Provider-neutral text generation with a Hermes CLI implementation."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


WINDOWS_SAFE_PROMPT_CHARS = 28_000


class ProviderError(RuntimeError):
    """Raised when an external model provider cannot complete a request."""


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    command: tuple[str, ...]


class TextProvider(Protocol):
    name: str

    def generate(
        self,
        prompt: str,
        *,
        working_directory: str | Path,
    ) -> ProviderResponse:
        ...


class HermesCliProvider:
    """Call the user's separately installed Hermes configuration."""

    name = "hermes"

    def __init__(
        self,
        *,
        executable: str | Path | None = None,
        timeout_seconds: int = 900,
        command_runner=subprocess.run,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Provider timeout must be positive.")

        self.executable = resolve_hermes_executable(executable)
        self.timeout_seconds = timeout_seconds
        self._command_runner = command_runner

    def generate(
        self,
        prompt: str,
        *,
        working_directory: str | Path,
    ) -> ProviderResponse:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Provider prompt cannot be empty.")
        if os.name == "nt" and len(prompt) > WINDOWS_SAFE_PROMPT_CHARS:
            raise ProviderError(
                "This extraction prompt is too large for Hermes one-shot mode "
                f"on Windows ({len(prompt):,} characters; safe limit "
                f"{WINDOWS_SAFE_PROMPT_CHARS:,}). Reduce the source set or use "
                "the planned chunked extraction workflow."
            )

        command = (
            str(self.executable),
            "--ignore-rules",
            "-z",
            prompt,
        )
        environment = dict(os.environ)
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"

        try:
            result = self._command_runner(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                cwd=str(Path(working_directory).resolve()),
                env=environment,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                f"Hermes timed out after {self.timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            raise ProviderError(f"Hermes could not be started: {exc}") from exc

        output = result.stdout.strip()
        error_output = result.stderr.strip()

        if result.returncode != 0:
            detail = error_output or output or "No error details were returned."
            raise ProviderError(
                f"Hermes exited with code {result.returncode}: {detail}"
            )
        if not output:
            raise ProviderError(
                "Hermes completed without returning response text."
            )

        return ProviderResponse(
            text=output,
            provider=self.name,
            command=command,
        )

    def diagnostic(self) -> Mapping[str, str | bool]:
        return {
            "provider": self.name,
            "available": self.executable.exists(),
            "executable": str(self.executable),
            "authentication": (
                "Managed by Hermes; no credentials are stored by DEFINALYZER."
            ),
        }


def resolve_hermes_executable(
    configured: str | Path | None = None,
) -> Path:
    candidates: list[Path] = []

    if configured:
        candidates.append(Path(configured).expanduser())

    discovered = shutil.which("hermes")
    if discovered:
        candidates.append(Path(discovered))

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        hermes_root = Path(local_app_data) / "hermes"
        candidates.extend(
            (
                hermes_root / "bin" / "hermes.cmd",
                hermes_root
                / "hermes-agent"
                / "venv"
                / "Scripts"
                / "hermes.exe",
                hermes_root
                / "hermes-agent"
                / "venv"
                / "Scripts"
                / "hermes.cmd",
            )
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise ProviderError(
        "Hermes was not found. Install Hermes, open a new terminal, and run "
        "'hermes --version'. You may also configure an explicit executable."
    )


def create_provider(settings: Mapping[str, object]) -> TextProvider:
    provider_name = settings.get("provider")

    if provider_name != "hermes":
        raise ProviderError(
            f"Unsupported configured provider {provider_name!r}. "
            "Available provider: hermes."
        )

    executable = settings.get("executable")
    timeout = settings.get("timeout_seconds", 900)

    if executable is not None and not isinstance(executable, str):
        raise ValueError("Provider executable must be text or null.")
    if isinstance(timeout, bool) or not isinstance(timeout, int):
        raise ValueError("Provider timeout_seconds must be an integer.")

    return HermesCliProvider(
        executable=executable,
        timeout_seconds=timeout,
    )

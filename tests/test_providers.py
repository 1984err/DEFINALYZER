import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from definalyzer.providers import (
    HermesCliProvider,
    ProviderError,
    resolve_hermes_executable,
)


class HermesProviderTests(unittest.TestCase):
    def test_generates_with_oneshot_and_isolated_rules(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout="# Protocol Overview\n",
                stderr="",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "hermes.exe"
            executable.write_bytes(b"placeholder")
            provider = HermesCliProvider(
                executable=executable,
                command_runner=runner,
            )
            response = provider.generate(
                "full extraction prompt",
                working_directory=directory,
            )

        self.assertEqual(response.text, "# Protocol Overview")
        call = runner.call_args
        command = call.args[0]
        self.assertIn("--ignore-rules", command)
        self.assertEqual(command[-2:], ("-z", "full extraction prompt"))
        self.assertNotIn("input", call.kwargs)
        self.assertTrue(call.kwargs["capture_output"])
        self.assertFalse(call.kwargs["check"])

    @patch("definalyzer.providers.os.name", "nt")
    def test_rejects_prompt_too_large_for_windows_command_line(self):
        runner = Mock()

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "hermes.exe"
            executable.write_bytes(b"placeholder")
            provider = HermesCliProvider(
                executable=executable,
                command_runner=runner,
            )

            with self.assertRaisesRegex(ProviderError, "too large"):
                provider.generate("x" * 28_001, working_directory=directory)

        runner.assert_not_called()

    def test_reports_nonzero_exit_without_exposing_configuration(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="provider unavailable",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "hermes.exe"
            executable.write_bytes(b"placeholder")
            provider = HermesCliProvider(
                executable=executable,
                command_runner=runner,
            )

            with self.assertRaisesRegex(ProviderError, "provider unavailable"):
                provider.generate("prompt", working_directory=directory)

    def test_reports_timeout(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired("hermes", 5))

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "hermes.exe"
            executable.write_bytes(b"placeholder")
            provider = HermesCliProvider(
                executable=executable,
                timeout_seconds=5,
                command_runner=runner,
            )

            with self.assertRaisesRegex(ProviderError, "timed out"):
                provider.generate("prompt", working_directory=directory)

    @patch("definalyzer.providers.shutil.which", return_value=None)
    def test_resolves_standard_windows_desktop_install(self, which):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            executable = (
                local
                / "hermes"
                / "hermes-agent"
                / "venv"
                / "Scripts"
                / "hermes.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"placeholder")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}):
                resolved = resolve_hermes_executable()

        self.assertEqual(resolved, executable.resolve())


if __name__ == "__main__":
    unittest.main()

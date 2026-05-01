"""Run Plotly Python snippets inside the dedicated sandbox subprocess."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import platformdirs

from pdf_epub_reader.services.plotly_sandbox import (
    SandboxCancelledError,
    SandboxOutputError,
    SandboxRuntimeError,
    SandboxStaticCheckError,
    SandboxTimeoutError,
)
from pdf_epub_reader.services.plotly_sandbox.cancel import CancelToken
from pdf_epub_reader.services.plotly_sandbox.venv_provisioner import (
    SandboxVenvProvisioner,
)

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """Execute Python Plotly code in an isolated subprocess and return JSON stdout."""

    def __init__(
        self,
        provisioner: SandboxVenvProvisioner | None = None,
        *,
        log_dir: Path | None = None,
        runner_path: Path | None = None,
    ) -> None:
        self._provisioner = provisioner or SandboxVenvProvisioner()
        self._runner_path = runner_path or Path(__file__).with_name("runner.py")
        self._log_dir = log_dir or Path(
            platformdirs.user_log_dir("gem-read", "gem-read")
        )

    def run(
        self,
        code: str,
        *,
        timeout_s: float,
        cancel_token: CancelToken,
    ) -> str:
        """Execute code in the sandbox and return the final JSON payload from stdout."""
        python_path = self._provisioner.ensure()

        with TemporaryDirectory(prefix="gem_read_plotly_sandbox_") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            code_path = temp_dir / "sandbox_code.py"
            code_path.write_text(code, encoding="utf-8")

            process = subprocess.Popen(
                [
                    str(python_path),
                    "-I",
                    "-S",
                    str(self._runner_path),
                    "--code-path",
                    str(code_path),
                ],
                cwd=temp_dir,
                env={},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            stop_monitor = threading.Event()
            cancelled_by_user = threading.Event()
            monitor = threading.Thread(
                target=self._monitor_cancellation,
                args=(process, cancel_token, cancelled_by_user, stop_monitor),
                daemon=True,
            )
            monitor.start()

            try:
                stdout, stderr = process.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                stdout, stderr = self._terminate_process(process)
                raise SandboxTimeoutError(
                    f"Sandbox execution timed out after {timeout_s:.2f} seconds."
                )
            finally:
                stop_monitor.set()
                monitor.join(timeout=1)

        if cancelled_by_user.is_set():
            raise SandboxCancelledError("Sandbox execution cancelled.")

        if process.returncode == 0:
            return self._extract_json_output(stdout)

        stderr_log_path = self._write_stderr_log(stderr)
        if process.returncode == 3:
            raise SandboxStaticCheckError(
                self._parse_disallowed_names(stderr),
                stderr_log_path,
            )

        raise SandboxRuntimeError(
            self._summarize_stderr(stderr),
            stderr_log_path,
        )

    @staticmethod
    def _monitor_cancellation(
        process: subprocess.Popen[str],
        cancel_token: CancelToken,
        cancelled_by_user: threading.Event,
        stop_monitor: threading.Event,
    ) -> None:
        while not stop_monitor.is_set():
            if not cancel_token.wait(0.05):
                continue
            cancelled_by_user.set()
            if process.poll() is None:
                process.terminate()
            return

    @staticmethod
    def _terminate_process(
        process: subprocess.Popen[str],
    ) -> tuple[str, str]:
        if process.poll() is None:
            process.terminate()
            try:
                return process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
        return process.communicate()

    @staticmethod
    def _extract_json_output(stdout: str) -> str:
        stripped = stdout.strip()
        if stripped:
            try:
                json.loads(stripped)
                return stripped
            except json.JSONDecodeError:
                pass

        for line in reversed(stdout.splitlines()):
            candidate = line.strip()
            if not candidate:
                continue
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

        raise SandboxOutputError(
            "Sandbox stdout did not contain a valid Plotly JSON payload."
        )

    @staticmethod
    def _parse_disallowed_names(stderr: str) -> list[str]:
        names: list[str] = []
        for line in stderr.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = payload.get("name")
            if isinstance(name, str) and name not in names:
                names.append(name)
        return names

    @staticmethod
    def _summarize_stderr(stderr: str) -> str:
        for line in reversed(stderr.splitlines()):
            summary = line.strip()
            if summary:
                return summary
        return "Sandbox execution failed without stderr output."

    def _write_stderr_log(self, stderr: str) -> Path:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        log_path = self._log_dir / f"plotly-sandbox-{timestamp}.log"
        log_path.write_text(stderr, encoding="utf-8")
        logger.warning("Sandbox stderr written to %s", log_path)
        return log_path
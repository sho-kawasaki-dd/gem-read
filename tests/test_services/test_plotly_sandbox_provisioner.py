from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pdf_epub_reader.services.plotly_sandbox import SandboxProvisioningError
from pdf_epub_reader.services.plotly_sandbox.venv_provisioner import (
    SandboxVenvProvisioner,
)


def _touch_python(provisioner: SandboxVenvProvisioner) -> Path:
    python_path = provisioner._python_path(provisioner._venv_dir)
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")
    return python_path


class TestSandboxVenvProvisioner:
    def test_ensure_rebuilds_when_manifest_is_missing(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        provisioner = SandboxVenvProvisioner(tmp_path / "sandbox-venv")
        python_path = provisioner._python_path(provisioner._venv_dir)
        rebuild_calls: list[bool] = []

        def fake_rebuild(_progress_cb=None) -> None:
            rebuild_calls.append(True)
            _touch_python(provisioner)
            provisioner._write_manifest()

        monkeypatch.setattr(provisioner, "_rebuild_environment", fake_rebuild)
        monkeypatch.setattr(provisioner, "_probe_required_imports", lambda _path: True)

        result = provisioner.ensure()

        assert rebuild_calls == [True]
        assert result == python_path

    def test_ensure_installs_packages_when_import_probe_fails(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        provisioner = SandboxVenvProvisioner(tmp_path / "sandbox-venv")
        python_path = _touch_python(provisioner)
        provisioner._venv_dir.mkdir(parents=True, exist_ok=True)
        provisioner._write_manifest()

        install_calls: list[Path] = []
        probe_results = iter([False, True])

        monkeypatch.setattr(
            provisioner,
            "_probe_required_imports",
            lambda _path: next(probe_results),
        )
        monkeypatch.setattr(
            provisioner,
            "_install_packages",
            lambda path: install_calls.append(path),
        )

        result = provisioner.ensure()

        assert result == python_path
        assert install_calls == [python_path]

    def test_ensure_raises_when_install_still_leaves_environment_invalid(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        provisioner = SandboxVenvProvisioner(tmp_path / "sandbox-venv")
        _touch_python(provisioner)
        provisioner._venv_dir.mkdir(parents=True, exist_ok=True)
        provisioner._write_manifest()

        monkeypatch.setattr(provisioner, "_probe_required_imports", lambda _path: False)
        monkeypatch.setattr(provisioner, "_install_packages", lambda _path: None)

        with pytest.raises(SandboxProvisioningError):
            provisioner.ensure()

    def test_probe_required_imports_uses_subprocess_success(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        provisioner = SandboxVenvProvisioner(tmp_path / "sandbox-venv")
        python_path = provisioner._venv_dir / "Scripts" / "python.exe"

        def fake_run(command, capture_output, text, check):
            assert command[0] == str(python_path)
            assert command[1] == "-c"
            assert capture_output is True
            assert text is True
            assert check is False
            return subprocess.CompletedProcess(command, 0, "", "")

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert provisioner._probe_required_imports(python_path) is True

    def test_run_checked_logs_and_raises_on_pip_failure(
        self,
        tmp_path,
        monkeypatch,
        caplog,
    ) -> None:
        provisioner = SandboxVenvProvisioner(tmp_path / "sandbox-venv")

        def fake_run(command, capture_output, text, check):
            raise subprocess.CalledProcessError(
                1,
                command,
                stderr="network unreachable",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(SandboxProvisioningError):
            provisioner._run_checked(["python", "-m", "pip"], "pip failed")

        assert "network unreachable" in caplog.text
"""The Workbench is independent of pCon.planner, the EasternGraphics SDK and any plugin."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PCON_PREFIXES = ("services.pcon_launcher", "services.pcon_sdk_obx")


def test_core_engine_and_obx_modules_load_no_pcon_code():
    code = (
        "import sys\n"
        "import services.ocd_engine.generator, services.ocd_engine.configuration_engine\n"
        "import services.ocd_engine.pricing, services.ocd_engine.catalogue\n"
        "import services.article_obx.ocd_repository_obx, services.article_obx.article_obx_service\n"
        "import services.obx_service, services.engineering, services.loading\n"
        f"bad = [m for m in sys.modules if m.startswith({_PCON_PREFIXES!r})]\n"
        "print('LOADED:' + ','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True,
                            text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("LOADED:"), result.stdout


def test_application_shell_loads_no_pcon_code():
    code = (
        "import os, sys\n"
        "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "import main\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "window = main.MainWindow()\n"
        f"bad = [m for m in sys.modules if m.startswith({_PCON_PREFIXES!r})]\n"
        "print('LOADED:' + ','.join(bad))\n"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True,
                            text=True, timeout=180)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("LOADED:"), result.stdout


def test_plugin_sdk_and_launcher_artifacts_are_gone():
    assert not (ROOT / "tools" / "pcon_obx_plugin").exists()
    assert not (ROOT / "services" / "pcon_sdk_obx").exists()
    assert not (ROOT / "services" / "pcon_launcher.py").exists()


def test_build_files_do_not_reference_plugin_or_sdk():
    for name in ("MK_Workbench_Phase1_Test.spec", "build_phase1_test.ps1", "requirements.txt",
                 "requirements-build.txt"):
        text = (ROOT / name).read_text(encoding="utf-8", errors="ignore").lower()
        for marker in ("pcon_obx_plugin", "x3gplugin", "pcon_sdk_obx", "pcon_launcher", "mkobxgenerator"):
            assert marker not in text, (name, marker)


def test_legacy_varcond_bridge_is_retained():
    assert (ROOT / "tools" / "legacy_varcond_bridge" / "LegacyVarCondBridge.csproj").is_file()
    assert (ROOT / "services" / "legacy_varcond_bridge.py").is_file()

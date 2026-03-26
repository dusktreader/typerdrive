"""
Startup benchmarks for typerdrive.

Measures two distinct costs that matter for CLI responsiveness:

  import time   — time to execute module-level code for each CLI variant,
                  measured in a fresh subprocess per round so sys.modules
                  caching does not mask the real first-import cost.

  --help time   — wall-clock time for the full subprocess round-trip of
                  `python <module> --help`, which is what a user experiences
                  when they first invoke any command including --help.

Each variant is run against three CLI fixtures:

  baseline      — plain typer + pydantic, no typerdrive
  settings      — typerdrive with attach_settings only
  full          — typerdrive with all features attached

Deltas vs the baseline surface typerdrive's net contribution so regressions
are immediately visible.

Run with:
    make qa/benchmark
    uv run pytest tests/benchmarks/ -m benchmark -v
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent  # typerdrive/
_SRC = _REPO_ROOT / "src"  # typerdrive/src/
_BENCH_PKG = _SRC / "typerdrive_benchmarks"

_BASELINE = _BENCH_PKG / "cli_baseline.py"
_SETTINGS = _BENCH_PKG / "cli_settings.py"
_FULL = _BENCH_PKG / "cli_full.py"

_IMPORT_SNIPPETS = {
    "baseline": "import typer; from pydantic import BaseModel",
    "typerdrive_settings": "from typerdrive import attach_settings, set_typerdrive_config",
    "typerdrive_full": (
        "from typerdrive import ("
        "attach_cache, attach_logging, attach_settings, handle_errors,"
        " set_typerdrive_config, add_settings_subcommand,"
        " add_cache_subcommand, add_logs_subcommand)"
    ),
}

_HELP_SCRIPTS = {
    "baseline": _BASELINE,
    "typerdrive_settings": _SETTINGS,
    "typerdrive_full": _FULL,
}

_ENV_WITH_SRC = {"PYTHONPATH": str(_SRC)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_import(snippet: str) -> None:
    """Execute *snippet* in a fresh interpreter. Raises on non-zero exit."""
    code = f"import sys; sys.path.insert(0, {str(_SRC)!r})\n{snippet}"
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
    )


def _run_help(script: Path) -> None:
    """Run `python <script> --help` in a subprocess. Raises on non-zero exit."""
    subprocess.run(
        [sys.executable, str(script), "--help"],
        check=True,
        capture_output=True,
        env={**__import__("os").environ, **_ENV_WITH_SRC},
    )


# ---------------------------------------------------------------------------
# Import-time benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestImportTime:
    """
    Measures the cost of importing each CLI's dependency set from scratch.

    Each round spawns a fresh subprocess so sys.modules state from previous
    rounds does not carry over — this reflects the real first-import cost a
    user pays on every invocation.
    """

    def test_baseline(self, benchmark: pytest.fixture) -> None:
        """Plain typer + pydantic import cost (reference baseline)."""
        benchmark.extra_info["description"] = "typer + pydantic only"
        benchmark(lambda: _run_import(_IMPORT_SNIPPETS["baseline"]))

    def test_typerdrive_settings(self, benchmark: pytest.fixture) -> None:
        """typerdrive import cost with attach_settings only."""
        benchmark.extra_info["description"] = "typerdrive: attach_settings"
        benchmark(lambda: _run_import(_IMPORT_SNIPPETS["typerdrive_settings"]))

    def test_typerdrive_full(self, benchmark: pytest.fixture) -> None:
        """typerdrive import cost with all features attached."""
        benchmark.extra_info["description"] = "typerdrive: all features"
        benchmark(lambda: _run_import(_IMPORT_SNIPPETS["typerdrive_full"]))


# ---------------------------------------------------------------------------
# --help wall-clock benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestHelpStartup:
    """
    Measures the full subprocess round-trip for `python <script> --help`.

    This is the number a user perceives: interpreter startup + all imports +
    typer command-tree construction + help rendering and exit.
    """

    def test_baseline(self, benchmark: pytest.fixture) -> None:
        """Plain typer + pydantic --help round-trip (reference baseline)."""
        benchmark.extra_info["description"] = "typer + pydantic only"
        benchmark(lambda: _run_help(_BASELINE))

    def test_typerdrive_settings(self, benchmark: pytest.fixture) -> None:
        """typerdrive --help round-trip with attach_settings only."""
        benchmark.extra_info["description"] = "typerdrive: attach_settings"
        benchmark(lambda: _run_help(_SETTINGS))

    def test_typerdrive_full(self, benchmark: pytest.fixture) -> None:
        """typerdrive --help round-trip with all features attached."""
        benchmark.extra_info["description"] = "typerdrive: all features"
        benchmark(lambda: _run_help(_FULL))

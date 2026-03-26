# Developer Guide

This page covers the development workflows for contributors to `typerdrive`.


## Setup

Clone the repo and install all dependencies (including dev extras) with [uv](https://docs.astral.sh/uv/):

```shell-ps1
git clone https://github.com/dusktreader/typerdrive
cd typerdrive
uv sync
```


## Quality checks

All quality targets live under the `qa/` namespace in the Makefile.

| Command                    | What it does                                  |
|----------------------------|-----------------------------------------------|
| `make qa`                  | Alias for `make qa/full`                      |
| `make qa/full`             | Tests + lint + type checks                    |
| `make qa/test`             | Unit + integration tests (with coverage)      |
| `make qa/test-unit`        | Unit tests only (no coverage enforcement)     |
| `make qa/test-integration` | Integration tests only (no coverage enforcement) |
| `make qa/lint`             | Ruff linter + typos spell-checker             |
| `make qa/types`            | Static type checking via `ty`                 |
| `make qa/format`           | Auto-format and sort imports with Ruff        |
| `make qa/benchmark`        | Startup performance benchmarks                |


## Startup benchmarks

`typerdrive` is imported on every CLI invocation, so its import-time cost directly affects how fast any app built
with it responds to commands — including `--help`. The benchmark suite exists to catch regressions in that cost,
not to drive optimization work.

### Running benchmarks

```shell-ps1
make qa/benchmark
```

Or directly with pytest:

```shell-ps1
uv run pytest tests/benchmarks/ -m benchmark -v
```

Benchmarks are **excluded from normal test runs** (`make qa/test`, `make qa/full`) via the `benchmark` marker.
They are slower by design — each round spawns a fresh subprocess to simulate a genuine cold-start.

### What is measured

The suite in `tests/benchmarks/test_startup.py` measures two costs across three CLI variants:

**Import time** — the cost of executing module-level code for each variant, measured in a fresh subprocess per
round so `sys.modules` caching does not mask the real first-import cost.

**`--help` wall-clock time** — the full round-trip of `python <script> --help` as a user would experience it:
interpreter startup + all imports + Typer command-tree construction + help rendering and exit.

**CLI variants** defined in `src/typerdrive_benchmarks/`:

| Variant           | Description                                                        |
|-------------------|--------------------------------------------------------------------|
| `cli_baseline.py` | Plain `typer` + `pydantic`, no typerdrive — the zero-overhead reference |
| `cli_settings.py` | `typerdrive` with `attach_settings` only                           |
| `cli_full.py`     | `typerdrive` with all features and management subcommands attached |

The delta between the baseline and the typerdrive variants is typerdrive's net contribution. A significant
increase in that delta across commits indicates a regression worth investigating.

### Interpreting results

`pytest-benchmark` prints a summary table after each run. The columns to focus on are `Mean` and `Median`.
`StdDev` will naturally be higher for the `--help` tests because subprocess scheduling adds noise.

Current baseline figures (approximate, M-series Mac):

| Variant    | Import time | `--help` time |
|------------|-------------|---------------|
| `baseline` | ~97 ms      | ~110 ms       |
| `settings` | ~149 ms     | ~153 ms       |
| `full`     | ~152 ms     | ~163 ms       |

typerdrive adds roughly **50–55 ms** over the plain typer/pydantic baseline. This is imperceptible to humans
and is not worth optimizing at this time.

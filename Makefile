PACKAGE_TARGET:=src/typerdrive

default: help


## ==== Quality Control ================================================================================================

qa: qa/full  ## Shortcut for qa/full

qa/test: qa/test-unit qa/test-integration  ## Run all tests (with combined coverage)
	@uv run pytest tests/unit tests/integration

qa/test-unit:  ## Run unit tests only (no coverage enforcement)
	@uv run pytest tests/unit --no-cov

qa/test-integration:  ## Run integration tests only (no coverage enforcement)
	@uv run pytest tests/integration --no-cov

qa/types:  ## Run static type checks
	@uv run ty check ${PACKAGE_TARGET} tests src/typerdrive_demo

qa/lint:  ## Run linters
	@uv run ruff check ${PACKAGE_TARGET} tests src/typerdrive_demo
	@uv run typos ${PACKAGE_TARGET} tests src/typerdrive_demo docs/source

qa/full: qa/test qa/lint qa/types  ## Run the full set of quality checks
	@echo "All quality checks pass!"

qa/format:  ## Run code formatter
	@uv run ruff check --select I --fix ${PACKAGE_TARGET} tests src/typerdrive_demo examples
	@uv run ruff format ${PACKAGE_TARGET} tests src/typerdrive_demo examples

qa/benchmark:  ## Run startup benchmarks
	@uv run pytest tests/benchmarks/ -m benchmark --no-cov --benchmark-min-rounds=10


## ==== Documentation ==================================================================================================

docs: docs/serve  ## Shortcut for docs/serve

docs/build:  ## Build the documentation
	@uv run mkdocs build --config-file=docs/mkdocs.yaml

docs/serve:  ## Build the docs and start a local dev server
	@uv run mkdocs serve --config-file=docs/mkdocs.yaml --dev-addr=localhost:10000


## ==== Demo ===========================================================================================================

demo: demo/run  ## Shortcut for demo/run

demo/run:  ## Run the demo application
	@uv run typerdrive-demo

demo/debug:  ## Run the demo application in debug mode
	@uv run debugpy --listen localhost:5678 --wait-for-client src/typerdrive_demo/main.py


## ==== Other Commands =================================================================================================

publish: _confirm  ## Publish the package by pushing a tag with the current version
	@if [[ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then \
		echo "You must be on the main branch to publish." && exit 1; \
	fi
	@git tag v$$(uv version --short) && git push origin v$$(uv version --short)


## ==== Helpers ========================================================================================================

clean:  ## Clean up build artifacts and other junk
	@rm -rf .venv
	@uv run pyclean . --debris
	@rm -rf dist
	@rm -rf .ruff_cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -f .coverage*
	@rm -f .junit.xml

help:  ## Show help message
	@awk "$$PRINT_HELP_PREAMBLE" $(MAKEFILE_LIST)


# ..... Make configuration .............................................................................................

.ONESHELL:
SHELL:=/bin/bash
.PHONY: qa qa/test qa/test-unit qa/test-integration qa/types qa/lint qa/full qa/format \
	docs docs/build docs/serve \
	demo demo/run demo/debug \
	qa/benchmark \
	publish \
	clean help


# ..... Color table for pretty printing ................................................................................

RED    := \033[31m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
TEAL   := \033[36m
GRAY   := \033[90m
CLEAR  := \033[0m
ITALIC := \033[3m


# ..... Hidden auxiliary targets .......................................................................................

_confirm:  # Requires confirmation before proceeding (Do not use directly)
	@if [[ -z "$(CONFIRM)" ]]; then \
		echo -n "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]; \
	fi


# ..... Help printer ...................................................................................................

define PRINT_HELP_PREAMBLE
BEGIN {
	print "Usage: $(YELLOW)make <target>$(CLEAR)"
	print
	print "Targets:"
}
/^## =+ .+( =+)?/ {
    s = $$0
    sub(/^## =+ /, "", s)
    sub(/ =+/, "", s)
	printf("\n  %s:\n", s)
}
/^## -+ .+( -+)?/ {
    s = $$0
    sub(/^## -+ /, "", s)
    sub(/ -+/, "", s)
	printf("\n    $(TEAL)> %s$(CLEAR)\n", s)
}
/^[$$()% 0-9a-zA-Z_\/-]+(\\:[$$()% 0-9a-zA-Z_\/-]+)*:.*?##/ {
    t = $$0
    sub(/:.*/, "", t)
    h = $$0
    sub(/.?*##/, "", h)
    printf("    $(YELLOW)%-19s$(CLEAR) $(GRAY)$(ITALIC)%s$(CLEAR)\n", t, h)
}
endef
export PRINT_HELP_PREAMBLE

.ONESHELL:
.DEFAULT_GOAL:=help
SHELL:=/bin/bash
PACKAGE_TARGET:=src/typerdrive


# ==== Helpers =========================================================================================================
.PHONY: confirm
confirm:  ## Don't use this directly
	@echo -n "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]


.PHONY: help
help:  ## Show help message
	@awk 'BEGIN {FS = ": .*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% 0-9a-zA-Z_\/-]+(\\:[$$()% 0-9a-zA-Z_\/-]+)*:.*?##/ { gsub(/\\:/,":", $$1); printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: clean
clean:  ## Clean up build artifacts and other junk
	@rm -rf .venv
	@uv run pyclean . --debris
	@rm -rf dist
	@rm -rf .ruff_cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -f .coverage*
	@rm -f .junit.xml


# ==== Quality Control =================================================================================================
.PHONY: qa
qa: qa/full ## Shortcut to qa/full

.PHONY: qa/test
qa/test:  ## Run the tests
	uv run pytest

.PHONY: qa/types
qa/types:  ## Run static type checks
	uv run mypy ${PACKAGE_TARGET} tests src/typerdrive_demo --pretty
	uv run basedpyright ${PACKAGE_TARGET} tests src/typerdrive_demo

.PHONY: qa/lint
qa/lint:  ## Run linters
	uv run ruff check ${PACKAGE_TARGET} tests src/typerdrive_demo
	uv run typos ${PACKAGE_TARGET} tests src/typerdrive_demo docs/source

.PHONY: qa/full
qa/full: qa/test qa/lint qa/types  ## Run the full set of quality checks
	@echo "All quality checks pass!"

.PHONY: qa/format
qa/format:  ## RUn code formatter
	uv run ruff check --select I --fix ${PACKAGE_TARGET} tests src/typerdrive_demo examples
	uv run ruff format ${PACKAGE_TARGET} tests src/typerdrive_demo examples


# ==== Documentation ===================================================================================================
.PHONY: docs
docs: docs/build ## Shortcut to docs/build

.PHONY: docs/build
docs/build:  ## Build the documentation
	uv run mkdocs build --config-file=docs/mkdocs.yaml

.PHONY: docs/serve
docs/serve:  ## Build the docs and start a local dev server
	uv run mkdocs serve --config-file=docs/mkdocs.yaml --dev-addr=localhost:10000


# ==== Demo Commands ===================================================================================================
.PHONY: demo
demo: demo/run  ## Shortcut for demo/run

.PHONY: demo/run
demo/run:  ## Run the app in debug mode
	uv run typerdrive-demo

.PHONY: demo/debug
demo/debug:  ## Run the app in debug mode
	uv run debugpy --listen localhost:5678 --wait-for-client src/typerdrive_demo/main.py


# ==== Other Commands ==================================================================================================
.PHONY: publish
publish: confirm
	@if [[ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]] then \
		echo "You must be on the main branch to publish." && exit 1; \
	fi
	@git tag v$$(uv version --short) && git push origin v$$(uv version --short)

.PHONY: help
help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+::' Makefile | grep -E '#.*$$' | sed -E 's/([a-zA-Z_-]+)::(.*)#(.*)/\1: \3/' | column -t -s ':'

###################
# Primary targets #
###################

# These targets represent the main actions you can take with this project. Each
# comprises a set of steps as determined by the internal targets below. I do
# this to keep the concern of illustrating project actions separate from the
# concern of actually performing those actions.

.PHONY: sync
sync:: # Sync the project dependencies.

.PHONY: build
build:: # Build the project.

.PHONY: test
test:: # Run the tests.

.PHONY: run
run:: # Run the project.

.PHONY: clean
clean:: # Clean the project.

.PHONY: lint
lint:: # Lint the code.


####################
# Internal targets #
####################

# Sync phase

sync::
	uv sync --all-groups

# Build phase

build:: sync
	uv build

# Test phase

test:: sync
	uv run pytest --doctest-modules --cov=src/rd --cov-report=term-missing --cov-report=html

# Run phase

run:: sync
	uv run rd cache

# Maintenance

clean::
	rm -rf dist build .pytest_cache
	rm -f tests/*.received.*

lint:: sync
	uv run black --line-length 100 src/ tests/
	uv run isort --profile black --line-length 100 src/ tests/
	uv run flake8 --max-line-length 100 --extend-ignore E203,W503 src/ tests/

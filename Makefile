.PHONY: help
help:
    @echo "Available targets:"
    @grep -E '^[a-zA-Z_-]+::' Makefile | grep -E '#.*$$' | sed -E 's/([a-zA-Z_-]+)::(.*)#(.*)/\1: \3/' | column -t -s ':'

.PHONY: build
build:: # Build the project.

.PHONY: test
test:: # Run the tests.

.PHONY: run
run:: # Run the project.

.PHONY: clean
clean:: # Clean the project.
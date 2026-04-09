# Evolution — Installation targets
#
# Usage:
#   make install WORKSPACE=/path/to/your/project
#

WORKSPACE ?= $(error WORKSPACE is required. Usage: make install WORKSPACE=/path/to/workspace)
EVOLUTION_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: install check-workspace

check-workspace:
	@test -d "$(WORKSPACE)" || (echo "Creating workspace directory: $(WORKSPACE)" && mkdir -p "$(WORKSPACE)")

install: check-workspace
	@echo "Installing Evolution into $(WORKSPACE)..."
	@mkdir -p "$(WORKSPACE)/.claude/skills"
	@cp -r "$(EVOLUTION_ROOT)/.claude/skills/"* "$(WORKSPACE)/.claude/skills/"
	@cp -r "$(EVOLUTION_ROOT)/evolution" "$(WORKSPACE)/evolution"
	@cp -r "$(EVOLUTION_ROOT)/engine" "$(WORKSPACE)/engine"
	@chmod +x "$(WORKSPACE)/engine/evolve" "$(WORKSPACE)/engine/"*.sh
	@echo "Done. Run: cd $(WORKSPACE) && ./engine/evolve help"

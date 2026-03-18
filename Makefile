# Evolution — Installation targets
#
# Usage:
#   make install-claude-code WORKSPACE=/path/to/your/project
#   make install-openclaw WORKSPACE=~/.openclaw/workspace
#

WORKSPACE ?= $(error WORKSPACE is required. Usage: make install-openclaw WORKSPACE=/path/to/workspace)
EVOLUTION_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: install-claude-code install-openclaw check-workspace

check-workspace:
	@test -d "$(WORKSPACE)" || (echo "Creating workspace directory: $(WORKSPACE)" && mkdir -p "$(WORKSPACE)")

install-claude-code: check-workspace
	@echo "Installing Evolution for Claude Code into $(WORKSPACE)..."
	@mkdir -p "$(WORKSPACE)/.claude/skills"
	@cp -r "$(EVOLUTION_ROOT)/.claude/skills/"* "$(WORKSPACE)/.claude/skills/"
	@cp -r "$(EVOLUTION_ROOT)/evolution" "$(WORKSPACE)/evolution"
	@cp -r "$(EVOLUTION_ROOT)/engine" "$(WORKSPACE)/engine"
	@chmod +x "$(WORKSPACE)/engine/evolve" "$(WORKSPACE)/engine/"*.sh
	@echo "Done. Run: cd $(WORKSPACE) && ./engine/evolve help"

install-openclaw: check-workspace
	@echo "Installing Evolution for OpenClaw into $(WORKSPACE)..."
	@# Copy engine and evolution runtime
	@cp -r "$(EVOLUTION_ROOT)/engine" "$(WORKSPACE)/engine"
	@cp -r "$(EVOLUTION_ROOT)/evolution" "$(WORKSPACE)/evolution"
	@chmod +x "$(WORKSPACE)/engine/evolve" "$(WORKSPACE)/engine/"*.sh
	@# Copy OpenClaw workspace files as references (never overwrite existing SOUL.md)
	@if [ -f "$(WORKSPACE)/SOUL.md" ]; then \
		echo "SOUL.md exists — copying as SOUL-EVOLUTION-REFERENCE.md (will NOT overwrite yours)"; \
		cp "$(EVOLUTION_ROOT)/openclaw/SOUL-REFERENCE.md" "$(WORKSPACE)/SOUL-EVOLUTION-REFERENCE.md"; \
	else \
		echo "No existing SOUL.md — copying Evolution SOUL-REFERENCE.md as starting point"; \
		cp "$(EVOLUTION_ROOT)/openclaw/SOUL-REFERENCE.md" "$(WORKSPACE)/SOUL.md"; \
	fi
	@cp "$(EVOLUTION_ROOT)/openclaw/ONBOARDING.md" "$(WORKSPACE)/ONBOARDING.md"
	@cp "$(EVOLUTION_ROOT)/openclaw/AGENTS.md" "$(WORKSPACE)/AGENTS.md"
	@cp "$(EVOLUTION_ROOT)/openclaw/MEMORY.md" "$(WORKSPACE)/MEMORY.md"
	@cp "$(EVOLUTION_ROOT)/openclaw/TOOLS.md" "$(WORKSPACE)/TOOLS.md"
	@cp "$(EVOLUTION_ROOT)/openclaw/OPENCLAW-SETUP.md" "$(WORKSPACE)/OPENCLAW-SETUP.md"
	@echo ""
	@echo "Installation complete."
	@echo ""
	@echo "Next steps:"
	@echo "  1. Read OPENCLAW-SETUP.md for agent registration instructions"
	@echo "  2. If you have an existing SOUL.md, integrate sections from SOUL-EVOLUTION-REFERENCE.md"
	@echo "  3. Keep total workspace files under 20K chars to avoid silent truncation"
	@echo "  4. Test: cd $(WORKSPACE) && ./engine/evolve help"

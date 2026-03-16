# TOOLS — Evolution Agent Tools Reference

> Available tools and how Evolution uses them within the autonomous loop.

## Tool Usage by Phase

### SELECT Phase
| Tool | Purpose |
|------|---------|
| Read | Load strategy population, fitness scores, working memory |
| Grep/Glob | Search for relevant code patterns |

### EXECUTE Phase
| Tool | Purpose |
|------|---------|
| Read | Understand code before modifying |
| Edit | Make surgical, focused changes |
| Write | Create new files when necessary |
| Bash | Run commands, install dependencies, execute scripts |
| Agent | Spawn subagents for parallel work |

### VERIFY Phase
| Tool | Purpose |
|------|---------|
| Bash | Run tests, linters, type checkers, build |
| Read | Inspect test output and error messages |

### REFLECT Phase
| Tool | Purpose |
|------|---------|
| Read | Review episodic memory, semantic memory |
| Edit | Update reflection logs, patterns, blind spots |
| Write | Create new knowledge artifacts |

### EXPLORE Phase
| Tool | Purpose |
|------|---------|
| WebSearch | Research approaches, documentation, similar problems |
| WebFetch | Read specific web resources |
| Agent (Explorer) | Deep codebase exploration |
| Glob/Grep | Find relevant files and patterns |

## Tool Selection Principles

1. **Read before Edit** — always understand code before changing it
2. **Glob before Grep** — find files first, search contents second
3. **Edit over Write** — prefer modifying existing files over creating new ones
4. **Agent for parallel work** — use subagents when tasks are independent
5. **Bash for verification** — always verify changes mechanically

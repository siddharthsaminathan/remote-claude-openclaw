# Claude Code — Siddharth's Configuration

## Model Routing

The local proxy at `http://localhost:8082` maps Claude aliases to DeepSeek models:

| Alias | Real Model | Use For |
|-------|-----------|---------|
| `opus` | deepseek-v4-pro | Complex coding, architecture, critical fixes, planning |
| `sonnet` | deepseek-v4-flash | Reading, documentation, info gathering |
| `haiku` | deepseek-v4-flash | Sub-agents, exploration, simple searches |

## Sub-Agent Rules — CRITICAL

**Always use sub-agents for parallel or scoped work.** When spawning agents:

- **Explore/research tasks** → use `model: "haiku"` — cheap, fast, good enough for reading files and finding things
- **Code review / second opinion** → use `model: "haiku"` — reviewing doesn't need v4 Pro
- **Complex coding / architecture** → use `model: "opus"` or inherit main model

**Default sub-agent model is `haiku`** unless the task clearly needs v4 Pro intelligence.

When using the Agent tool, always set the model explicitly:
- `model: "haiku"` for exploration, reading, searching, simple checks
- `model: "opus"` for writing code, debugging, complex reasoning

## Parallel Execution

When tasks are independent, run sub-agents in PARALLEL (single message, multiple Agent tool calls). This saves time. Example: if you need to explore 3 different directories, spawn 3 haiku agents simultaneously.

## Model Selection Heuristic

| Task Type | Model | Reasoning |
|-----------|-------|-----------|
| Writing/editing code | opus | Needs precision |
| Debugging complex bugs | opus | Needs deep reasoning |
| Reading files for context | haiku | Fast and cheap |
| Searching/grepping codebase | haiku | Don't overpay |
| Planning architecture | opus | Needs big-picture thinking |
| Code review | haiku | Checking patterns |
| Running tests/shell | haiku | Mechanical, not creative |
| Documentation generation | haiku | Straightforward translation |

## Tools & Skills

- **graphify** (`~/.claude/skills/graphify/SKILL.md`) — knowledge graph queries. Trigger: `/graphify`
- When working in a project with `graphify-out/`, read GRAPH_REPORT.md before answering codebase questions

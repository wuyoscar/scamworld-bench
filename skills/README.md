# ScamWorld skill

`skills/scamworld/` is an [Agent Skill](https://github.com/agentskills/agentskills): a folder with a `SKILL.md` that a coding agent reads. It describes how to install ScamWorld (Docker or source), run a task and read the result, give a website your own request or a question, score runs with your own function, compare models and observation settings, see what the agent receives on a page, write tasks and websites of your own, and connect your own agent or model API.

| file | content |
|---|---|
| `SKILL.md` | what can be changed and how, the three most common requests, the rules |
| `references/install.md` | Docker, source, the full task set, a check without a model |
| `references/recipes.md` | one recipe per request: first run, your own request, a question with your scoring, a comparison, what the agent sees, the warning signs, a task of your own, many tasks and models, your own agent, a new website |
| `references/commands.md` | every command and option, the environment variables, the Python calls |
| `references/evaluator.md` | writing a scoring function; what `episode` has |
| `references/task-folder.md` | the files of a task, the page markup, `verify` |
| `references/troubleshooting.md` | what a failure or an odd result usually means |

[AGENTS.md](../AGENTS.md) at the top of the repository is the one-page map an agent finds in a clone; it sends the agent here.

## With any coding agent

Open your agent in a clone of this repository and give it one sentence:

```text
Read skills/scamworld/SKILL.md in this repository and follow it: run shop-11 on my model (<model id>, <base URL>) with a request where the user first asks to read the Delivery page and then to buy, and tell me what the agent did.
```

Without a clone, one sentence sets everything up, the skill included:

```text
Set up ScamWorld for me: https://raw.githubusercontent.com/wuyoscar/scamworld-bench/main/docs/install.md
```

[docs/install.md](../docs/install.md) is written for the agent: install, a check without a model, the copy of this skill into its skills folder, and what to report. The agent needs a shell and a way to fetch a web address.

## Install it as a skill

Copy the folder to where your agent looks for skills. From the root of a clone, for this project:

```bash
mkdir -p .claude/skills .agents/skills
cp -R skills/scamworld .claude/skills/scamworld    # Claude Code (OpenCode reads it too)
cp -R skills/scamworld .agents/skills/scamworld    # Codex CLI, Cursor, OpenCode
```

| agent | project | all projects | then |
|---|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `.claude/skills/scamworld/` | `~/.claude/skills/scamworld/` | the agent loads it when the task matches; `/scamworld` runs it |
| [Codex CLI](https://learn.chatgpt.com/docs/build-skills) | `.agents/skills/scamworld/` | `~/.agents/skills/scamworld/` | `/skills` lists it; `$scamworld` mentions it; restart Codex if it does not appear |
| [Cursor](https://cursor.com/docs/skills) | `.agents/skills/scamworld/` | `~/.cursor/skills/scamworld/` | the agent loads it when the task matches |
| [OpenCode](https://opencode.ai/docs/skills) | `.opencode/skills/scamworld/`, `.claude/skills/scamworld/` or `.agents/skills/scamworld/` | `~/.config/opencode/skills/scamworld/`, `~/.claude/skills/scamworld/` or `~/.agents/skills/scamworld/` | the agent calls its `skill` tool; `@scamworld` loads it |

The skill points at `docs/` and `examples/` of this repository, so run the agent in a clone (the skill clones it if you have none), or point it at where the clone is.

## With the `skills` installer

`skills` is a third-party command-line installer ([vercel-labs/skills](https://github.com/vercel-labs/skills), MIT, needs Node.js 22.20 or later). Its documentation says it finds skills in a `skills/` folder of a GitHub repository and installs them for the agent you name (`claude-code`, `codex`, `cursor`, `opencode`, among others):

```bash
npx skills add wuyoscar/scamworld-bench --skill scamworld -a claude-code      # this project
npx skills add wuyoscar/scamworld-bench --skill scamworld -a codex -g         # all projects
```

Read its README before you run it.

## Sources

- Claude Code: <https://code.claude.com/docs/en/skills>
- Codex CLI: <https://developers.openai.com/codex/skills> (now <https://learn.chatgpt.com/docs/build-skills>)
- Cursor: <https://cursor.com/docs/skills>
- OpenCode: <https://opencode.ai/docs/skills>
- The `skills` installer: <https://github.com/vercel-labs/skills> (`README.md`, `docs/agents.md`, `docs/creating-skills.md`)
- The SKILL.md format: <https://github.com/agentskills/agentskills> (`docs/specification.mdx`)

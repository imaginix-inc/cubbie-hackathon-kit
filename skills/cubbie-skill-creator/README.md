# Cubbie Skill Creator

A skill for Claude Code and Codex that helps you write Skills for [Cubbie](https://cubbie.ai), the AI assistant in
students' iMessage. It is Anthropic's [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
with Cubbie additions: it asks which Cubbie abilities your Skill needs, picks the lightest sign-in, writes
`cubbie.yaml` only when scripts need it, checks the folder against Cubbie's install rules, and gives you the GitHub
link to text to Cubbie plus a checklist of test conversations.

The Skills it writes stay standard [Agent Skills](https://agentskills.io): the same folder works in Cubbie, Claude
Code, Codex and other agents.

## Install

Copy this folder, keeping its name `cubbie-skill-creator`:

| Agent | For one project | For all projects |
| --- | --- | --- |
| Claude Code | `<project>/.claude/skills/cubbie-skill-creator/` | `~/.claude/skills/cubbie-skill-creator/` |
| Codex | `<project>/.agents/skills/cubbie-skill-creator/` | `~/.agents/skills/cubbie-skill-creator/` |

Start a new session after copying. Then ask, for example: "Use cubbie-skill-creator to make a Cubbie Skill that
reminds me what's due before my 9 pm study block." In Codex you can also type `$cubbie-skill-creator`.

## Requirements

- Python 3.9+ with PyYAML (`pip install pyyaml`), or [uv](https://docs.astral.sh/uv/) to run the scripts with
  `uv run`.
- git, and a public GitHub repository to publish your Skill.
- Optional: the `claude` CLI, used only by the description optimizer (`scripts/run_loop.py`).

## Scripts

```bash
python3 scripts/validate_cubbie_skill.py path/to/my-skill   # the checks Cubbie runs when a student sends the link
python3 scripts/github_link.py path/to/my-skill             # confirms the push and prints the pinned install link
```

## License

Apache License 2.0, see [LICENSE.txt](LICENSE.txt). See [NOTICE](NOTICE) for the source commit and the changes.

# Cubbie Hackathon Kit

Skills for your coding agent (Claude Code or Codex) for the [Cubbie Hackathon](https://hackathon.cubbie.ai).
[Cubbie](https://cubbie.ai) lives in students' iMessage and handles everyday college life; the hackathon asks you to
teach it a new trick.

| Skill | What it does |
| --- | --- |
| [`cubbie-hackathon`](skills/cubbie-hackathon) | Explains the three tracks, what each needs and how it is judged; reads the open and close times live from the hackathon site; walks your team through Track 1 and then Tracks 2 and 3; signs you in with Google or an email code and submits or edits your team's entry, so you don't need the website for that. |
| [`cubbie-skill-creator`](skills/cubbie-skill-creator) | Writes your Track 1 Cubbie Skill with you: interview, draft, checks against Cubbie's install rules, publishing to GitHub, and the link you text to Cubbie to install it. Based on Anthropic's skill-creator. |

Both are standard [Agent Skills](https://agentskills.io).

## Install

### Claude Code

As a plugin (inside Claude Code):

```text
/plugin marketplace add imaginix-inc/cubbie-hackathon-kit
/plugin install cubbie-hackathon@cubbie-hackathon-kit
```

The skills then show up as `/cubbie-hackathon:cubbie-hackathon` and `/cubbie-hackathon:cubbie-skill-creator`.
Get updates with `/plugin marketplace update cubbie-hackathon-kit`.

Or copy the folders, for all your projects:

```bash
git clone https://github.com/imaginix-inc/cubbie-hackathon-kit.git
mkdir -p ~/.claude/skills && cp -R cubbie-hackathon-kit/skills/* ~/.claude/skills/
```

(For one project only, copy them into `<project>/.claude/skills/` instead.)

### Codex

```bash
git clone https://github.com/imaginix-inc/cubbie-hackathon-kit.git
mkdir -p ~/.agents/skills && cp -R cubbie-hackathon-kit/skills/* ~/.agents/skills/
```

(For one project only, use `<project>/.agents/skills/`.) Mention a skill with `$cubbie-hackathon` or
`$cubbie-skill-creator`.

Start a new session after installing, then ask something like:

> What's open in the Cubbie hackathon right now, and what does our team need for Track 1?

> Help us build our Track 1 Skill, then submit it.

To update a copied install, `git pull` in the clone and copy the folders again.

## Requirements

- Python 3.9 or newer. The submit script uses only the standard library.
- For `cubbie-skill-creator`'s checks: PyYAML (`pip install pyyaml`), or [uv](https://docs.astral.sh/uv/).
- git and a GitHub account: Track 1 Skills are installed from a public GitHub repo, and every track asks for one.

## Submitting from the terminal

The agent runs this for you, but it works on its own too:

```bash
cd skills/cubbie-hackathon
python3 scripts/hackathon.py status                              # what's open right now
python3 scripts/hackathon.py login --google                      # Google in your browser
python3 scripts/hackathon.py login --email you@school.edu        # or: emails you a 6-digit code
python3 scripts/hackathon.py mine                                # your team's entries
python3 scripts/hackathon.py submit --track skills --help        # every field
python3 scripts/hackathon.py gallery --track skills
python3 scripts/hackathon.py logout
```

`submit` and `posts` show a preview and send nothing until you add `--yes`. An entry is public in the gallery
the moment it's sent (team name, project name, one-liner and links; member emails stay private), and your team
can keep editing it while the track is open.

Sign in with the same email address you use on the website: Google or an email code for one address reach the
same account, but another address (an alias, a personal Gmail) is a different account and can't edit your team's
entry. `whoami` shows which address and account you're on.

What the script keeps on your computer: only the sign-in's access token, which expires after about an hour, in
`~/.config/cubbie-hackathon/session.json` (readable only by you). `logout` deletes it and ends only that sign-in. The key inside the script is
the website's public key; all rules are enforced by the hackathon's database.

## Questions

Rules, prizes and dates are on [hackathon.cubbie.ai](https://hackathon.cubbie.ai), and the organizers are on
[Discord](https://discord.gg/7eJADTbQMT). If the site and this kit disagree, the site wins.

## For maintainers

```bash
python3 -m unittest discover -s tests   # offline tests of the submit script
python3 tests/live_test.py              # against the hosted project; needs `supabase login` with project access
```

The live test creates two `@cubbie.test` users through the admin API, submits, edits and checks the public
gallery, then deletes every submission, audit row and user it created. It needs the submission windows to be open
and doesn't change settings. When the database's `submit_entry`, `my_submissions`, `get_gallery`,
`get_leaderboard` or `update_launch_links` change, update `skills/cubbie-hackathon/scripts/hackathon.py` and
run both.

`cubbie-skill-creator`'s validator and references follow Cubbie's Skill installer as of 2026-10-23. When the
installer's rules change (PokeCampus `services/agent-engine/app/skills/package.py`, `source.py`,
`dependencies.py`, or `docs/hackathon/skill-format.md`), update
`skills/cubbie-skill-creator/scripts/validate_cubbie_skill.py` and the `references/cubbie-*.md` files to match.

## License

Apache License 2.0, see [LICENSE](LICENSE). `cubbie-skill-creator` is a modified version of Anthropic's
skill-creator; see its [NOTICE](skills/cubbie-skill-creator/NOTICE).

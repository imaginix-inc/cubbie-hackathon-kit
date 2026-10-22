# Testing and publishing a Cubbie Skill

Cubbie's abilities (Canvas, reminders, the browser, memory...) exist only inside Cubbie, so a local agent cannot
run a Cubbie Skill end to end. Test in three layers: structure locally, scripts locally, the whole flow on Cubbie.

## 1. Structure

```bash
python3 <creator>/scripts/validate_cubbie_skill.py <skill-folder>
```

`<creator>` is this skill-creator's folder. The script needs PyYAML (`pip install pyyaml`), or run it with
`uv run <creator>/scripts/validate_cubbie_skill.py <skill-folder>`.

- `FAIL` lines are what Cubbie would reply when a student sends the link; fix every one.
- `warning:` lines do not block the install, but fix them anyway: install commands in `SKILL.md`, files the
  instructions mention that do not exist, uncommitted changes, and fields other agents may reject.
- It does not install packages, run scripts or contact websites.

## 2. Scripts

Run each script the way `SKILL.md` tells Cubbie to, from the Skill folder:

- Give scripts a `--sample` (or similar) mode that uses a bundled file under `assets/`, so they run without a key
  or network. Run that mode first. A sample run must not overwrite or mix with the student's real saved state;
  write sample state to a separate file or not at all.
- Set `SKILL_DATA_DIR` to a temporary folder and check that saved state lands there:
  `SKILL_DATA_DIR=$(mktemp -d) python3 scripts/<name>.py --sample`.
- Run without the key or login to check the error path prints one clear line and exits with the code `SKILL.md`
  maps to a reply.
- Install the pinned packages into a throwaway environment to prove the versions exist, ideally in the same
  runtime as Cubbie: `docker run --rm -v "$PWD":/skill -w /skill python:3.12-slim sh -c "pip install
  requests==2.32.3 && python3 scripts/<name>.py --sample"`. Without Docker, use a fresh virtualenv.
- Keep output short; Cubbie reads only the first 8,000 characters.

## 3. Publish

1. Put the Skill folder in a **public** GitHub repository, either as the repository root (the repository name must
   then equal the Skill name) or as a folder inside it (the folder name equals the Skill name).
2. Commit and push. Cubbie installs the pushed commit, never the working copy.
3. Get the install link:

   ```bash
   python3 <creator>/scripts/github_link.py <skill-folder>
   ```

   It re-runs the structure checks, confirms the commit is pushed and that GitHub serves the repository without a
   login, then prints a link pinned to the commit (`https://github.com/<owner>/<repo>/tree/<commit>/<folder>`) and,
   when possible, a branch link. Submit the pinned link; use either for testing.

Never push, create repositories or change visibility without the user's go-ahead; tell them the exact commands
instead if they prefer to run them.

## 4. On Cubbie

The user texts the link to their own Cubbie and walks through a checklist. Write the checklist for **this** Skill
from the template below: fill in the real trigger phrases, abilities, keys and failure cases, and drop rows that
do not apply. Hand it to the user as a short numbered list they can follow on their phone.

| # | Text Cubbie | Expect |
| --- | --- | --- |
| 1 | The pinned GitHub link | A summary with the Skill's description, the commit, packages, websites, keys and logins, then a question asking to install. Check that every host and key is expected. |
| 2 | "yes" | Installed. If the Skill needs a key or login, a secure page or sign-in link arrives next. |
| 3 | (Key or login) | Open the secure page and save the key, or tap the sign-in link and approve. Nothing sensitive is typed into the chat. |
| 4 | A realistic request that should trigger the Skill, phrased the way a student would ("<trigger phrase>") | The Skill's main flow runs and the reply follows its reply rules (short, plain text, links on their own line). |
| 5 | A second phrasing of the same need, without the obvious keywords | The Skill still triggers. |
| 6 | A near-miss request the Skill should not handle | Cubbie answers normally, without the Skill. |
| 7 | A step that acts for the student (send, book, submit, pay) | Cubbie asks first and acts only after "yes"; payment is handed to the student. |
| 8 | The failure case: account not connected, nothing matches, or a bad key | One clear line telling the student what to do. |
| 9 | Accept a recurring check-in, if the Skill offers one | The schedule is created at the time the student chose; the first check-in arrives. |
| 10 | Start a new conversation the next day and repeat step 4 | Saved settings, logins and keys are reused; nothing is asked twice. |
| 11 | After pushing a fix: "update <skill-name>" | A new summary with the new commit, then a question; the fix works after "yes". |
| 12 | "What Skills do I have?", then "remove <skill-name>" | The Skill is listed, then removed. |

When something fails on Cubbie, fix it locally, rerun sections 1–3, then "update <skill-name>" and repeat the rows
that failed.

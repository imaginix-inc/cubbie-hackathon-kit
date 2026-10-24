# Sign-in and keys for a Cubbie Skill

Cubbie installs Skills in personal mode: the student who installs a Skill provides whatever sign-in or key it
needs. Every sign-in step costs the Skill installs, so pick the **first** approach on this list that works for the
service, and stop there.

| # | Approach | Use it when | What the student does | What the Skill contains |
| --- | --- | --- | --- | --- |
| 1 | No sign-in | The data is public: menus, events, transit, weather, open APIs | Nothing | Nothing extra |
| 2 | Accounts already connected to Cubbie | The Skill needs Canvas or Google data | Nothing, or connects once when Cubbie asks | Name the ability in `SKILL.md` |
| 3 | Sign in on the website in Cubbie's browser | The service is a website with no API: campus portals, room booking, food ordering | Fills a secure login page once, or signs in by taking over the browser; takes over again for payment or two-factor codes | The site, the steps, and where the student must confirm, in `SKILL.md` |
| 4 | Command-line login with a link | A CLI signs in through a browser link (device-code style) | Taps the link and approves in their own browser | The login and status commands, in `SKILL.md` |
| 5 | API key from the student | The service only issues personal API keys | Opens a secure page, pastes the key once, chooses Save | The variable name and where the key is created, in `SKILL.md` |

## Choosing

Ask these in order and take the first yes:

1. Can the Skill do its job with public data, or with Cubbie's own web and browser abilities without signing in? → 1
2. Is the data in Canvas or Google (Gmail, Calendar, Drive, Docs, Sheets, Tasks, Contacts)? → 2
3. Is it a website the student already logs into, with no public API? → 3
4. Does the service have a CLI that signs in through a browser link (one command that waits for approval, or a start
   step and a check step)? → 4
5. Otherwise, does the service let each student create a personal API key? → 5

If none fits, the Skill probably needs a team-owned backend; see "Team keys" below before going further.

## How they behave

- **Saved for next time.** Logins from approaches 3 and 4 and keys from approach 5 stay with that student and are
  reused in later conversations.
- **Keys are matched by variable name.** A student who already saved `OPENAI_API_KEY` for another Skill is not asked
  again, so use the conventional name when one exists (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`,
  `NOTION_API_KEY`, ...). The name must end in `_API_KEY`, `_TOKEN`, `_SECRET`, `_CLIENT_ID`, `_USERNAME`,
  `_PASSWORD`, `_EMAIL` or `_PHONE`.
- **A command gets a key only when it names it.** `curl -H "Authorization: Bearer $EXAMPLE_API_KEY" ...` works as
  written; for a script that reads the variable itself, write the run command as
  `EXAMPLE_API_KEY="$EXAMPLE_API_KEY" python3 scripts/<name>.py ...` so Cubbie copies it.
- **CLI logins run in the background.** Cubbie starts the login command in the background and texts the student the
  link (and code) as soon as it is printed; the command can keep waiting for approval, for up to an hour. A two-step
  form (start, then check) works too. Standard input is closed, so the command must not ask questions; pass answers
  as flags. A login command that needs a key names it like any other command.
- **Team keys are not hosted.** Cubbie cannot keep the team's key and use it on behalf of every student. Use a
  backend that does not need a secret from the client, or ship a restricted, quota-limited key and assume anyone
  who installs the Skill can read it.
- **Never** ask the student to paste a password or key in the chat, hard-code a student's credentials, or send them
  to the team's own server.

## Writing each approach

### 1. No sign-in

Nothing extra. Scripts can reach any website over HTTPS.

### 2. Connected accounts

Name the ability in plain words and say what to do when it is not connected:

```markdown
1. Read the student's Canvas assignments due in the next 7 days.
   If Canvas is not connected, ask the student to connect it and stop here.
```

### 3. Cubbie's browser

Describe the site, the steps, and each point where the student must take over or confirm:

```markdown
1. Open https://library.example.edu/rooms in the browser.
2. If the site asks for a login, ask the student to sign in (secure login page or take over the browser).
3. Pick the room and time the student chose, then show the summary and ask "Book it?".
4. Book only after the student says yes. If the site asks for a two-factor code, hand the browser to the student.
```

Say which schools or sites the Skill supports; campus systems differ.

### 4. CLI login

```markdown
## Sign in (first time only)

1. Run `python3 scripts/publish.py status`. Exit code 0 means the student is signed in; skip the rest.
2. Start the sign-in: `netlify login --request "Cubbie wants to publish web pages for you" --json`.
   Send the student the `url` it prints and end your turn.
3. When the student replies, run `netlify login --check <ticket_id> --json` and read `status`.
```

- The login command prints the link (and code, if any). It may wait for approval (`gh auth login --web`) or exit and
  leave a second step to finish it; describe that step.
- Give a status command that exits with 0 when the student is signed in; a small wrapper script is fine.
- Login state is written under `HOME`, which persists per student.

### 5. Student API key

```markdown
## Key

This Skill needs the student's own free OpenWeather API key, saved in Cubbie as `OPENWEATHER_API_KEY`
(created at https://home.openweathermap.org/api_keys). Run the script as
`OPENWEATHER_API_KEY="$OPENWEATHER_API_KEY" python3 scripts/forecast.py ...`.
```

- Scripts read the key with `os.environ["OPENWEATHER_API_KEY"]` (Python) or `process.env.OPENWEATHER_API_KEY`
  (Node), and never print it. Cubbie masks it in output too.
- Link the exact page where the key is created, and say how long it takes and whether it is free.
- If the Skill can run without the key, say what works without it.
- When a script reports the key is missing or rejected, the Skill tells Cubbie to ask the student to update it
  through the secure page, never in the chat.

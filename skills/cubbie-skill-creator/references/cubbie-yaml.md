# cubbie.yaml

`cubbie.yaml` sits next to `SKILL.md` and declares what the Skill's scripts need on Cubbie: packages, websites,
keys and logins. Other agents ignore it, so `SKILL.md` stays a standard Agent Skill.

**Only create it when needed.** A Skill that only uses Cubbie's own abilities, or scripts that use nothing but the
Python or Node standard library and no network, needs no `cubbie.yaml`. Omit any section that is not needed.

`scripts/validate_cubbie_skill.py` applies the same rules as Cubbie's installer (as of 2026-10-23); run it after
every change.

## Contents

- [Example](#example)
- [Fields](#fields)
- [Rules Cubbie enforces](#rules-cubbie-enforces)
- [What scripts can rely on](#what-scripts-can-rely-on)
- [Common mistakes](#common-mistakes)

## Example

```yaml
cubbie: 1

dependencies:
  pip: ["requests==2.32.3"]           # exact versions only
  npm: ["netlify-cli@27.12.1"]
  download:
    - url: https://github.com/example/tool/releases/download/v1.2.0/tool-linux-amd64.tar.gz
      sha256: "<64 hex characters>"
      bin: tool

network:
  install: []                         # extra hosts needed only while installing
  runtime: ["api.example.com"]        # hosts the scripts call

secrets:
  - env: EXAMPLE_API_KEY              # arrives as an environment variable
    label: Example API key
    help_url: https://example.com/account/api-keys

login:
  - id: example
    command: example-cli login --web       # prints a sign-in link; may wait for approval
    status: example-cli whoami
```

## Fields

| Field | Meaning | Rules |
| --- | --- | --- |
| `cubbie` | Format version | Required; must be `1` |
| `dependencies.pip` | Python packages | Exact versions only: `name==1.2.3` or `name[extra]==1.2.3`; at most 20 |
| `dependencies.npm` | npm packages, including CLIs | Exact versions only: `name@1.2.3` or `@scope/name@1.2.3` (pre-release and build tags allowed); lowercase names; at most 20 |
| `dependencies.download` | A prebuilt binary or archive | Each entry needs `url` (`https://`, no spaces, at most 2,048 characters), `sha256` (64 hex characters) and `bin` (the executable name to put on `PATH`, no slashes); at most 5 |
| `network.install` | Extra hosts needed only while installing | PyPI, npm and GitHub downloads are already allowed; at most 10 |
| `network.runtime` | Hosts the scripts call | Host names only; at most 10; shown to the student in the install summary |
| `secrets` | Keys the student provides | `env`, `label` (1–120 characters), optional `help_url` (`https://`), optional `required` (default `true`); at most 5; `env` names unique |
| `login` | A CLI sign-in Cubbie starts for the student | `id` (lowercase letters, digits, `-`; at most 32), `command` (1–500 characters; prints a sign-in link, may wait for approval, never asks for input), optional `status` (at most 500 characters; exits 0 when signed in); at most 3 |

## Rules Cubbie enforces

- **Unknown fields are rejected** at every level, so a typo never silently does nothing.
- **Host names** (`network.install`, `network.runtime`): no scheme, port or path (`api.example.com`, not
  `https://api.example.com/v1`); no IP addresses; at least two labels; labels use letters, digits and `-` only;
  `*.example.com` is allowed, but not on a shared suffix such as `*.github.io`, `*.vercel.app`,
  `*.netlify.app`, `*.amazonaws.com` or `*.co.uk`. Case and a trailing dot are ignored.
- **`secrets.env`**: an uppercase letter followed by 1–63 uppercase letters, digits or `_`. Reserved and rejected:
  `PATH`, `HOME`, `PWD`, `SHELL`, `USER`, `TMPDIR`, `LANG`, `LC_ALL`, `TZ`, `PYTHONPATH`, `PYTHONHOME`,
  `PYTHONSTARTUP`, `NODE_PATH`, `NODE_OPTIONS`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `SSL_CERT_DIR`,
  `REQUESTS_CA_BUNDLE`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `ALL_PROXY`, `MPLBACKEND`, `SAL_USE_VCLPLUGIN`,
  and anything starting with `LD_`, `DYLD_`, `CUBBIE_`, `SKILL_`, `MODAL_`, `BASH_`, `NPM_CONFIG_` or `PIP_`.
- **Pinned means pinned**: no `>=`, `~=`, `^`, `latest`, git URLs, tarball URLs or local paths.
- **Downloads** must match their `sha256`; compute it with `shasum -a 256 <file>` (macOS) or `sha256sum <file>`.
  Pick the Linux x86-64 build.

## What scripts can rely on

- Debian Linux with Python 3.12 and Node.js 22. Packages from `cubbie.yaml` are already on `PATH`, `PYTHONPATH` and
  `NODE_PATH`; never install anything at run time.
- The working directory is a fresh copy of the Skill folder each time the sandbox starts; changes there are lost.
  Save state under `$SKILL_DATA_DIR`. `HOME` also persists per student, so CLI config and logins survive.
- HTTPS (port 443) to the hosts in `network.runtime` and to PyPI and npm. For any other host Cubbie has to stop and
  ask the student to allow it, so declare every host up front.
- `curl` and `git` are installed. Each run gets 2 minutes by default (up to 10), 1 CPU and 2 GB of memory. Cubbie can
  also run a command in the background for up to an hour (a login, a long build); background runs get no saved keys.
- Do not assume the sandbox clock is in the student's time zone; have Cubbie pass the local date and time as
  arguments.
- Print a short result to standard output; Cubbie reads the first 8,000 characters. Exit with a non-zero code on
  failure and say in `SKILL.md` what each code means for the reply. Don't use 97 or 98: Cubbie reserves them for
  "the installed files are missing or changed" and asks the student to reinstall.
- Declared keys arrive as environment variables; never print them.
- Scripts cannot call Cubbie's abilities; Cubbie passes data in as arguments or files.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| `pip install requests` in `SKILL.md` | Remove it; declare `requests==<version>` under `dependencies.pip` |
| `requests>=2` or `netlify-cli@^27` | Pin one exact version |
| `https://api.example.com` in `network.runtime` | `api.example.com` |
| A host the script calls is missing from `network.runtime` | Add it; otherwise Cubbie has to stop and ask the student to allow it |
| `network:` left with nothing under it | Delete the section; an empty key is an error |
| `env: api_key` | `API_KEY` |
| A key requested in chat | Declare it under `secrets`; Cubbie collects it on a secure page |
| A login command that asks a question (y/n, pick an account) | Pass the answers as flags; standard input is closed |

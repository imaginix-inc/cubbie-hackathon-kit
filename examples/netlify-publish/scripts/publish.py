#!/usr/bin/env python3
"""Publish a folder of web pages to the student's own Netlify account and print the public link.

The Netlify CLI (installed with npm install -g, see SKILL.md) does the work. Its sign-in is stored under $HOME,
which Cubbie keeps for the student, so they sign in once. Site IDs are remembered under HOME
(~/.config/netlify-publish) so publishing again under the same name updates the same site instead of creating a new one.

    python3 scripts/publish.py status
    python3 scripts/publish.py deploy --dir /workspace/your_files/portfolio --name maya-portfolio

Exit codes: 0 ok, 2 bad site name, 3 not signed in, 4 folder problem, 5 Netlify error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SITE_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SIGNED_OUT = ("Authentication required", "Not logged in", "re-authenticate")


def fail(message: str, code: int):
    print(message, file=sys.stderr)
    sys.exit(code)


def netlify(*args: str) -> tuple[int, dict, str]:
    """Run the CLI with --json; return the exit code, the parsed JSON and the last lines of any error text."""
    try:
        result = subprocess.run(["netlify", *args, "--json"], capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        fail("The Netlify CLI is missing; install it with: npm install -g netlify-cli@27.12.1", 5)
    except subprocess.TimeoutExpired:
        fail("Netlify took too long to answer; try again later.", 5)
    out = result.stdout
    try:
        data = json.loads(out[out.index("{"):out.rindex("}") + 1]) if "{" in out else {}
    except ValueError:
        data = {}
    error = "\n".join((result.stderr or out).strip().splitlines()[-5:])
    return result.returncode, data, error


def sites_file() -> Path:
    # SKILL_DATA_DIR is where Skills installed before folders kept their data.
    return Path(os.environ.get("SKILL_DATA_DIR") or Path.home() / ".config" / "netlify-publish") / "sites.json"


def load_sites() -> dict:
    try:
        return json.loads(sites_file().read_text())
    except (OSError, ValueError):
        return {}


def status() -> int:
    _, data, _ = netlify("status")
    if not data.get("loggedIn"):
        print("Not signed in to Netlify.")
        return 3
    account = data.get("account") or {}
    print(f"Signed in to Netlify as {account.get('Name') or 'unknown name'} ({account.get('Email') or 'no email'}).")
    return 0


def deploy(folder: str, name: str, team: str | None, new_site: bool) -> int:
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        fail(f"{folder} is not a folder.", 4)
    if not (path / "index.html").is_file():
        fail(f"{folder} has no index.html, so the site would show a 404 page.", 4)
    if not SITE_NAME.match(name):
        fail("Site names use lowercase letters, digits and hyphens, at most 63 characters.", 2)
    sites = {} if new_site else load_sites()
    args = ["deploy", "--dir", str(path), "--prod", "--no-build", "--message", "Published by Cubbie"]
    if name in sites:
        args += ["--site", sites[name]]
    else:
        # --site-name creates a new site every time, so the ID is saved below and used from then on.
        args += ["--site-name", name] + (["--team", team] if team else [])
    code, data, error = netlify(*args)
    if code != 0 or not data.get("site_id"):
        if any(marker.lower() in error.lower() for marker in SIGNED_OUT):
            fail("Not signed in to Netlify.", 3)
        fail(f"Netlify could not publish the site:\n{error}", 5)
    sites = load_sites() | {name: data["site_id"]}
    sites_file().parent.mkdir(parents=True, exist_ok=True)
    sites_file().write_text(json.dumps(sites, indent=2))
    print(f"Published {data.get('site_name') or name}: {data.get('url') or data.get('deploy_url')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="say whether the student is signed in to Netlify")
    publish = commands.add_parser("deploy", help="publish a folder that contains index.html")
    publish.add_argument("--dir", required=True, help="folder to publish")
    publish.add_argument("--name", required=True, help="site name; the same name updates the same site")
    publish.add_argument("--team", help="Netlify team slug, only needed when the account has several teams")
    publish.add_argument("--new-site", action="store_true", help="forget the saved site and create a new one")
    args = parser.parse_args(argv)
    if args.command == "status":
        return status()
    return deploy(args.dir, args.name, args.team, args.new_site)


if __name__ == "__main__":
    sys.exit(main())

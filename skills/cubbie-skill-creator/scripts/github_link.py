#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Print the link a student texts to Cubbie to install a Skill, pinned to the pushed commit.

    python3 scripts/github_link.py <skill-folder>            # asks the git host too
    python3 scripts/github_link.py <skill-folder> --offline  # local git checks only

The folder (one Skill, or a folder of Skills that one link installs together) must be committed
and pushed. Cubbie fetches links with git over HTTPS from any host (as of 2026-10-24); GitHub, Gitee
and GitLab links can name a folder and a branch, tag or commit, other hosts only the repository.
The script runs the Cubbie checks from validate_cubbie_skill.py, then lists the repository with git
without a sign-in, as anyone installing the link would. It never pushes or changes anything.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

# Repository path segments Cubbie accepts in a link (app/skills/source.py).
SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
REMOTE = re.compile(r"^(?:(?:https|ssh)://(?:[^@/]+@)?(?P<host>[^/:]+)(?::\d+)?/|(?:[^@/]+@)?(?P<scp>[^/:]+):)"
                    r"(?P<path>[^:]+?)(?:\.git)?/?$")


def _load_validator():
    path = Path(__file__).resolve().with_name("validate_cubbie_skill.py")
    spec = importlib.util.spec_from_file_location("validate_cubbie_skill", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(folder: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, check=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def remote_access(url: str) -> str:
    """List the repository with git and no sign-in, as Cubbie does: "public", "sign-in", "not-found" or "unreachable"."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")
    try:
        result = subprocess.run(["git", "-c", "credential.helper=", "ls-remote", "--heads", "--", url],
                                capture_output=True, text=True, env=env, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "unreachable"
    if result.returncode == 0:
        return "public"
    if "could not read Username" in result.stderr or "Authentication failed" in result.stderr or "403" in result.stderr:
        return "sign-in"
    if "not found" in result.stderr.lower() or "does not exist" in result.stderr or "404" in result.stderr:
        return "not-found"
    return "unreachable"


def web_link(host: str, project: str, ref: str | None, subpath: str) -> str | None:
    """The link Cubbie reads as this ref and folder; None where the host's links name only the repository."""
    base = f"https://{host}/{project}"
    if not ref:
        return base
    tail = "".join(f"/{quote(segment)}" for segment in (*ref.split("/"), *(subpath.split("/") if subpath else ())))
    if host in ("github.com", "gitee.com"):
        return f"{base}/tree{tail}"
    if "gitlab" in host:
        return f"{base}/-/tree{tail}"
    return None


def link_for(folder: Path, remote: str = "origin", offline: bool = False) -> dict:
    folder = folder.resolve()
    problems, notes = [], []
    result = {"folder": str(folder), "ok": False, "problems": problems, "notes": notes}
    root = git(folder, "rev-parse", "--show-toplevel")
    if root is None:
        problems.append("This folder is not in a git repository. Create a public repository (on GitHub for the hackathon), "
                        "commit the Skill and push it.")
        return result
    subpath = folder.relative_to(Path(root).resolve()).as_posix()
    subpath = "" if subpath == "." else subpath
    remote_url = git(folder, "remote", "get-url", remote)
    match = REMOTE.match(remote_url or "")
    host = (match["host"] or match["scp"]).lower().removeprefix("www.") if match else ""
    if "." not in host:
        problems.append(f"The git remote {remote!r} is {remote_url or 'missing'}; Cubbie fetches from https://<host>/<repository>, "
                        "so push to a remote with a web address.")
        return result
    project = match["path"].strip("/")
    for segment in project.split("/"):
        if not SEGMENT.match(segment):
            problems.append(f"{segment!r} cannot appear in a Cubbie install link; use letters, digits, '.', '_' and '-' only.")
    commit = git(folder, "rev-parse", "HEAD")
    if commit is None:
        problems.append("The repository has no commits yet; commit the Skill and push it.")
        return result
    if git(folder, "status", "--porcelain", "--", "."):
        problems.append("The Skill folder has uncommitted changes; commit and push them first. Cubbie installs the pushed commit.")
    pushed = bool(git(folder, "branch", "-r", "--contains", commit))
    if not pushed:
        problems.append(f"Commit {commit[:12]} is not on any branch of the remote yet; push it first.")

    validator = _load_validator()
    for checked in validator.check_all(folder):  # a folder of Skills: one link installs them together
        if not checked["ok"]:
            problems.append(f"Cubbie would refuse this: {checked['error']}")
        notes.extend(note for note in checked.get("warnings", []) if not note.startswith("There are uncommitted changes"))
        if checked.get("name"):
            result.setdefault("skills", []).append(checked["name"])

    url = f"https://{host}/{project}"
    if not offline and not problems:
        access = remote_access(url)
        if access == "sign-in":
            notes.append(f"{url} needs a sign-in, so its link installs only for a student who signed in to git on Cubbie's "
                         "computer (Cubbie can run gh auth login for them). Make the repository public so anyone can install it.")
        elif access == "not-found":
            problems.append(f"{url} was not found without a sign-in. Check the remote; if the repository is private, make it public.")
        elif access == "unreachable":
            notes.append(f"Could not reach {host} to check the repository; open {url} in a private browser window to check.")

    branch = git(folder, "rev-parse", "--abbrev-ref", "HEAD")
    pinned = web_link(host, project, commit, subpath)
    result.update(host=host, repository=url, commit=commit, subpath=subpath, pinned=pinned or url)
    if branch and branch != "HEAD" and pinned:
        result["latest"] = web_link(host, project, branch, subpath)
    if not pinned:
        notes.append(f"Links to {host} can name only the repository: Cubbie installs every Skill in it (up to 40) from the "
                     "newest commit of its default branch. Use GitHub, Gitee or GitLab to link one folder or pin a commit.")
    result["ok"] = not problems
    return result


def render(result: dict) -> str:
    lines = []
    if result["ok"]:
        if len(result.get("skills") or []) > 1:
            lines.append(f"One link installs {len(result['skills'])} Skills together: {', '.join(result['skills'])}")
        if result["pinned"] == result["repository"]:
            lines += ["Repository link (installs the newest commit of the default branch):", f"  {result['pinned']}"]
        else:
            lines += ["Pinned link (always this commit; share it and use it for submission once it works):",
                      f"  {result['pinned']}"]
        if result.get("latest"):
            lines += ["Branch link (the newest push; test with it, and text it again after each push to update):",
                      f"  {result['latest']}"]
    else:
        lines.append(f"Not ready: {result['folder']}")
        lines += [f"  - {problem}" for problem in result["problems"]]
    lines += [f"  note: {note}" for note in result["notes"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the Cubbie install link for a pushed Skill folder.")
    parser.add_argument("folder", type=Path,
                        help="the Skill folder, or a folder of Skills")
    parser.add_argument("--remote", default="origin", help="git remote Cubbie fetches from (default: origin)")
    parser.add_argument("--offline", action="store_true", help="skip asking the git host")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)
    result = link_for(args.folder, remote=args.remote, offline=args.offline)
    print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

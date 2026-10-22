#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Print the GitHub link a student texts to Cubbie to install a Skill, pinned to the pushed commit.

    python3 scripts/github_link.py <skill-folder>            # checks GitHub too
    python3 scripts/github_link.py <skill-folder> --offline  # local git checks only

The folder (one Skill, or a folder of Skills that one link installs together) must be committed
and pushed to a public GitHub repository. The script runs the Cubbie checks from
validate_cubbie_skill.py, then downloads the commit's archive the way Cubbie does (no login, no
redirects, at most 30 MiB). It never pushes or changes anything.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# The link forms Cubbie accepts: github.com/<owner>/<repo>[/tree/<ref>/<folder>].
SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
REMOTE = re.compile(r"^(?:https://(?:[^@/]+@)?(?:www\.)?github\.com/|git@github\.com:|ssh://git@github\.com/)"
                    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


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


MAX_ARCHIVE_BYTES = 30 * 1024 * 1024  # Cubbie refuses larger repository archives


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # Cubbie does not follow redirects either
        return None


def archive_status(owner: str, repo: str, commit: str) -> tuple[int | None, int | None]:
    """(HTTP status, size in bytes or None when over the limit) of the archive Cubbie downloads from codeload."""
    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{commit}"
    request = urllib.request.Request(url, headers={"User-Agent": "cubbie-skill-creator"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=30) as response:
            size = 0
            while chunk := response.read(1 << 16):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    return response.status, None
            return response.status, size
    except urllib.error.HTTPError as exc:
        return exc.code, 0
    except (urllib.error.URLError, OSError):
        return None, 0


def link_for(folder: Path, remote: str = "origin", offline: bool = False) -> dict:
    folder = folder.resolve()
    problems, notes = [], []
    result = {"folder": str(folder), "ok": False, "problems": problems, "notes": notes}
    root = git(folder, "rev-parse", "--show-toplevel")
    if root is None:
        problems.append("This folder is not in a git repository. Create a public GitHub repository, commit the Skill and push it.")
        return result
    subpath = folder.relative_to(Path(root).resolve()).as_posix()
    subpath = "" if subpath == "." else subpath
    remote_url = git(folder, "remote", "get-url", remote)
    match = REMOTE.match(remote_url or "")
    if not match:
        problems.append(f"The git remote {remote!r} is {remote_url or 'missing'}; Cubbie installs only from github.com.")
        return result
    owner, repo = match["owner"], match["repo"]
    for segment in (owner, repo, *(subpath.split("/") if subpath else ())):
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
    at_root = not subpath and (folder / "SKILL.md").exists()
    if (folder / "SKILL.md").exists():
        # For a Skill at the repository root, Cubbie compares the name with the repository name, not the local folder.
        results = [validator.check(folder, directory_name=repo if at_root else None)]
    else:
        results = validator.check_all(folder)  # a folder of Skills: one link installs them together
    for checked in results:
        if not checked["ok"]:
            hint = " (the Skill is the repository root, so the repository name counts as its folder name)" \
                if at_root and "must equal the folder name" in checked["error"] else ""
            problems.append(f"Cubbie would refuse this: {checked['error']}{hint}")
        notes.extend(note for note in checked.get("warnings", []) if not note.startswith("There are uncommitted changes"))
    result["skills"] = [checked["name"] for checked in results if checked.get("name")]

    if not offline and not problems:
        status, size = archive_status(owner, repo, commit)
        if status == 404:
            problems.append(f"GitHub does not serve commit {commit[:12]} of {owner}/{repo} without a login. "
                            "Make the repository public; if it is, push the commit.")
        elif status == 200 and size is None:
            problems.append("The repository archive is over 30 MiB, so Cubbie would refuse it; "
                            "put the Skill in a smaller repository.")
        elif status is not None and 300 <= status < 400:
            problems.append(f"GitHub redirects the archive (HTTP {status}), which Cubbie does not follow; "
                            "check that the repository was not renamed or moved and use its current name.")
        elif status != 200:
            notes.append("Could not reach GitHub to confirm the commit is public; open the link in a private browser window to check.")

    tail = f"/{subpath}" if subpath else ""
    result.update(owner=owner, repo=repo, commit=commit, subpath=subpath,
                  pinned=f"https://github.com/{owner}/{repo}/tree/{commit}{tail}")
    branch = git(folder, "rev-parse", "--abbrev-ref", "HEAD")
    if branch and branch != "HEAD" and "/" not in branch:
        result["latest"] = f"https://github.com/{owner}/{repo}/tree/{branch}{tail}"
    result["ok"] = not problems
    return result


def render(result: dict) -> str:
    lines = []
    if result["ok"]:
        if len(result.get("skills") or []) > 1:
            lines.append(f"One link installs {len(result['skills'])} Skills together: {', '.join(result['skills'])}")
        lines += ["Pinned link (always this commit; share it and use it for submission once it works):", f"  {result['pinned']}"]
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
                        help="the Skill folder (its name must equal the Skill name), or a folder of Skills")
    parser.add_argument("--remote", default="origin", help="git remote that points at GitHub (default: origin)")
    parser.add_argument("--offline", action="store_true", help="skip the GitHub checks")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)
    result = link_for(args.folder, remote=args.remote, offline=args.offline)
    print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Check Skill folders before you publish them for Cubbie (or any agent that reads Agent Skills).

    python3 scripts/validate_cubbie_skill.py <skill-folder>...    # needs PyYAML
    uv run scripts/validate_cubbie_skill.py <skill-folder>...     # installs PyYAML on the fly

The checks follow the Agent Skills format (https://agentskills.io/specification). A Skill is any folder
with a SKILL.md, and a folder without a readable one is the only FAIL. Everything else is a warning,
because Cubbie copes: it lists a Skill by the `name` and `description` in its frontmatter, and without
them by the folder name and the first paragraph. Cubbie has no install rules of its own (no cubbie.yaml,
no limits on files, size or the number of Skills): it fetches a link with ordinary commands such as
`git clone`. The warnings point out what makes a Skill harder to find, harder to read or slower to fetch.

A folder without SKILL.md is checked as a folder of Skills: every folder inside it that has one, however
deep, the outermost where Skills nest. Nothing is installed or run, and no website is contacted.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by hand
    sys.exit("PyYAML is missing: run `pip install pyyaml`, or use `uv run scripts/validate_cubbie_skill.py`.")

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # the Agent Skills name rule
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 1024  # the Agent Skills limit
LIST_DESCRIPTION_CHARS = 200  # about what Cubbie's Skill list shows of a description
MAX_BODY_LINES = 500  # recommended by the Agent Skills spec
LARGE_FILE_BYTES = 10 * 1024 * 1024
LARGE_REPOSITORY_BYTES = 100 * 1024 * 1024
LARGE_REPOSITORY_FILES = 10_000
SKIPPED_DIRS = {".git", "node_modules"}  # never searched for Skills
FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(?:|(.*?)\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
PACKAGE_PATH = re.compile(r"(?<![\w./-])(?:scripts|references|assets)/[A-Za-z0-9._/-]*[A-Za-z0-9_]")
MIB = 1024 * 1024


class SkillError(ValueError):
    """Why a folder is not a Skill."""


# ---------------------------------------------------------------- files


def _git(folder: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, check=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def folder_files(folder: Path) -> list[str]:
    """Paths a push would publish: git's view inside a repository (ignored files left out), else every file but .git."""
    listed = _git(folder, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".")
    paths = sorted(path for path in (listed or "").split("\0") if path and os.path.lexists(folder / path))
    if paths:
        return paths
    for root, dirs, names in os.walk(folder):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in names + [name for name in dirs if os.path.islink(os.path.join(root, name))]:
            paths.append(Path(root, name).relative_to(folder).as_posix())
    return sorted(paths)


def _skipped(path: str) -> bool:
    return bool(SKIPPED_DIRS & set(path.split("/")[:-1]))


def _size(path: Path) -> int:
    try:
        return os.lstat(path).st_size
    except OSError:
        return 0


@functools.lru_cache(maxsize=None)
def repository_size(root: Path) -> tuple:
    """(files, bytes) of what a clone of the repository at `root` checks out."""
    paths = folder_files(root)
    return len(paths), sum(_size(root / path) for path in paths)


def outside_links(folder: Path, paths: list) -> list:
    """Links that break when the Skill folder is copied on its own: absolute, leaving the folder, or pointing at nothing."""
    notes = []
    for path in paths:
        source = folder / path
        if not os.path.islink(source):
            continue
        link = os.readlink(source)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), link))
        if link.startswith("/") or target == ".." or target.startswith("../") or not os.path.exists(source):
            notes.append(f"{path} is a link to {link}, outside the Skill folder or to nothing; a copy of the folder "
                         "won't have that file. Put the file itself in the folder.")
    return notes


# ---------------------------------------------------------------- SKILL.md


def read_skill_md(folder: Path) -> tuple:
    """(SKILL.md text, frontmatter or None, body, problem with the frontmatter or None)."""
    if not (folder / "SKILL.md").is_file():
        raise SkillError("No SKILL.md in this folder.")
    try:
        text = (folder / "SKILL.md").read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise SkillError("SKILL.md is not UTF-8 text.") from None
    content = text.removeprefix("\ufeff")
    match = FRONTMATTER.match(content)
    if not match:
        return text, None, content, "missing"
    block, body = match.group(1) or "", content[match.end():]
    try:
        data = yaml.safe_load(block) if block.strip() else {}
    except yaml.YAMLError as exc:
        problem = str(getattr(exc, "problem", "") or "").strip()
        return text, None, body, problem or "not valid YAML"
    if not isinstance(data, dict):
        return text, None, body, "not a list of fields"
    return text, data, body, None


def first_paragraph(body: str) -> str:
    lines, heading, fenced = [], "", False
    for raw in body.splitlines():
        line = raw.strip()
        fence = line.startswith(("```", "~~~"))
        if fence:
            fenced = not fenced
        if fence or fenced or not line.strip("-*_=> ") or line.startswith(("#", "|", "<", "![")):
            if lines:
                break
            if not (fence or fenced) and line.startswith("#"):
                heading = heading or line.lstrip("#").strip()
            continue
        lines.append(line.lstrip("> "))
    return " ".join(lines) or heading


def _text(value) -> str:
    return "" if value is None or isinstance(value, (dict, list)) else str(value).strip()


# ---------------------------------------------------------------- checks


def check_skill(folder: Path, shown: str) -> dict:
    """Check one Skill folder: FAIL only without a readable SKILL.md, warnings for the rest."""
    if not folder.is_dir():
        return {"folder": shown, "ok": False, "error": "Not a folder."}
    try:
        text, frontmatter, body, problem = read_skill_md(folder)
    except SkillError as exc:
        return {"folder": shown, "ok": False, "error": str(exc)}
    paths = folder_files(folder)
    notes = []
    if problem == "missing":
        notes.append("SKILL.md has no frontmatter (a block between --- lines at the top with name and description); "
                     "Cubbie lists the Skill by its folder name and first paragraph instead.")
    elif problem:
        notes.append(f"SKILL.md frontmatter can't be read as YAML ({problem}); Cubbie and other agents may not see its "
                     "name and description. Quote values that contain a colon.")
    fields = frontmatter or {}
    name, description = _text(fields.get("name")), _text(fields.get("description"))
    if frontmatter is not None and not name:
        notes.append(f"SKILL.md gives no name; Cubbie lists the Skill as {folder.name!r}, its folder name.")
    if name and (len(name) > MAX_NAME_CHARS or not NAME_PATTERN.match(name)):
        notes.append(f"The name {name!r} isn't lowercase letters, digits and single hyphens (at most {MAX_NAME_CHARS} "
                     "characters), as the Agent Skills format asks; other agents may reject it.")
    listed = description or first_paragraph(body)
    if frontmatter is not None and not description:
        notes.append("SKILL.md gives no description; Cubbie uses its first paragraph instead. "
                     "Write one that says what the Skill does and when to use it." if listed else
                     "SKILL.md gives no description and has no paragraph to take one from; "
                     "write one that says what the Skill does and when to use it.")
    if len(description) > MAX_DESCRIPTION_CHARS:
        notes.append(f"The description has {len(description)} characters; the Agent Skills format allows "
                     f"{MAX_DESCRIPTION_CHARS}, and Cubbie's Skill list shows about the first {LIST_DESCRIPTION_CHARS}.")
    elif len(description) > LIST_DESCRIPTION_CHARS:
        notes.append(f"The description has {len(description)} characters; Cubbie's Skill list shows about the first "
                     f"{LIST_DESCRIPTION_CHARS}, so say what the Skill does and when to use it within them.")
    extra = sorted(str(key) for key in fields if key not in SPEC_FIELDS)
    if extra:
        notes.append(f"Frontmatter field(s) {', '.join(extra)} are not in the Agent Skills format; other agents may reject them.")
    lines = len(text.splitlines())
    if lines > MAX_BODY_LINES:
        notes.append(f"SKILL.md has {lines} lines; the Agent Skills format recommends under {MAX_BODY_LINES}. "
                     "Move details into other files.")
    if "cubbie.yaml" in paths:
        notes.append("cubbie.yaml is not needed and Cubbie ignores it; write setup commands, keys and sign-in steps in SKILL.md.")
    for path in sorted(set(PACKAGE_PATH.findall(text))):
        if path not in paths and not any(name.startswith(path + "/") for name in paths):
            notes.append(f"SKILL.md refers to {path}, which is not in the folder.")
    notes += outside_links(folder, paths)
    sizes = {path: _size(folder / path) for path in paths}
    large = sorted((path for path, size in sizes.items() if size > LARGE_FILE_BYTES), key=lambda path: -sizes[path])
    for path in large[:5]:
        notes.append(f"{path} is {sizes[path] / MIB:.0f} MiB; large files make the Skill slow to fetch.")
    top = _git(folder, "rev-parse", "--show-toplevel")
    count, total = repository_size(Path(top.strip()).resolve()) if top else (len(sizes), sum(sizes.values()))
    if count > LARGE_REPOSITORY_FILES or total > LARGE_REPOSITORY_BYTES:
        notes.append(f"The repository has {count:,} files and {total / MIB:.0f} MiB; Cubbie clones all of it, so it will "
                     "be slow to install. A repository with just the Skill installs faster.")
    if _git(folder, "status", "--porcelain", "--", "."):
        notes.append("There are uncommitted changes; Cubbie fetches the pushed commit, not your working copy.")
    return {"folder": shown, "ok": True, "name": name or folder.name, "description": listed,
            "files": len(sizes), "bytes": sum(sizes.values()), "warnings": notes}


def expand(folder: Path) -> tuple:
    """The Skill folders inside `folder`: itself when it has SKILL.md, else every folder inside it that has one,
    however deep, the outermost where Skills nest; .git and node_modules are not searched."""
    if not folder.is_dir() or (folder / "SKILL.md").is_file():
        return [folder], None
    root = folder.resolve()
    found = sorted({posixpath.dirname(path) for path in folder_files(root)
                    if posixpath.basename(path) == "SKILL.md" and not _skipped(path) and (root / path).is_file()},
                   key=lambda path: (path.count("/"), path))
    outer = []
    for path in found:
        if not any(path.startswith(parent + "/") for parent in outer):
            outer.append(path)
    if not outer:
        return [], "No SKILL.md in this folder or the folders inside it."
    return [folder / path for path in sorted(outer)], None


def check_all(folder: Path) -> list:
    """Check a Skill folder, or every Skill in a folder of Skills."""
    skills, error = expand(folder)
    if error:
        return [{"folder": str(folder), "ok": False, "error": error}]
    return [check_skill(skill.resolve(), str(skill)) for skill in skills]


def render(result: dict) -> str:
    if not result["ok"]:
        return f"FAIL {result['folder']}\n  {result['error']}"
    rows = [
        ("description", result["description"]),
        ("files", f"{result['files']} file{'s' * (result['files'] != 1)}, {result['bytes']:,} bytes"),
    ]
    lines = [f"OK   {result['name']}  {result['folder']}"]
    lines += [f"  {label + ':':15}{value}" for label, value in rows if value]
    lines += [f"  warning: {note}" for note in result["warnings"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check Skill folders against the Agent Skills format before pushing them.")
    parser.add_argument("folders", nargs="+", type=Path, help="Skill folders, or a folder of Skills")
    parser.add_argument("--json", action="store_true", help="print one JSON object per folder")
    args = parser.parse_args(argv)
    results = [result for folder in args.folders for result in check_all(folder)]
    for result in results:
        print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

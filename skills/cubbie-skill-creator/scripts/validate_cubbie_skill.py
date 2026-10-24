#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Check Skill folders with the rules Cubbie applies when a student installs a Skill from a link.

    python3 scripts/validate_cubbie_skill.py <skill-folder>...    # needs PyYAML
    uv run scripts/validate_cubbie_skill.py <skill-folder>...     # installs PyYAML on the fly

The checks follow Cubbie's installer (app/skills/source.py and package.py) as of 2026-10-24: a Skill
is a plain folder installed as it is. Cubbie refuses only a folder without a readable SKILL.md (or
with no description and no text to take one from) and folders over 1000 files or 50 MiB; it repairs
the rest (a name that is not lowercase, missing or already taken; a missing description; frontmatter
that is not valid YAML) and says so in the install summary. A link to a file elsewhere in the
repository is installed as a copy of it; other links, git submodules and the large files behind Git
LFS pointers are left out, also said in the summary. .git and node_modules are never copied, and
cubbie.yaml is no longer read. A folder without SKILL.md is checked the way a link to it installs:
every folder inside it that has one, however deep (.claude/skills/<name>, .agents/skills/<name>, ...),
the outermost where Skills nest, at most 40.
The report also lists what the student sees before confirming: the install commands your files give,
the commands SKILL.md says it needs, and the environment variables (keys) your files read.
Nothing is installed or run, and no website is contacted.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by hand
    sys.exit("PyYAML is missing: run `pip install pyyaml`, or use `uv run scripts/validate_cubbie_skill.py`.")

# Names of Skills built into Cubbie; a user Skill with one of them gets -2.
BUILTIN_SKILL_NAMES = frozenset({"email-to-professor", "study-plan-builder"})

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
NOT_NAME = re.compile(r"[^a-z0-9]+")
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 1024  # the Agent Skills limit
MAX_LIST_DESCRIPTION_CHARS = 200  # what the per-turn Skill list shows: the first sentence, cut to this
MAX_BODY_LINES = 500  # recommended by the Agent Skills spec; a warning only
MAX_FILES = 1000
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_BUNDLE_SKILLS = 40
SKIPPED_DIRS = {".git", "node_modules"}
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"
LENIENT_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(?:|(.*?)\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][\w.-]*)[ \t]*:(?:[ \t]+(.*))?$")
BLOCK_SCALAR = re.compile(r"^[|>][+-]?$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])")
BIN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
PACKAGE_PATH = re.compile(r"(?<![\w./-])(?:scripts|references|assets)/[A-Za-z0-9._/-]*[A-Za-z0-9_]")
# Install commands in your text: shown to the student in the install summary; Cubbie runs them after they agree.
INSTALL_LINE = re.compile(
    r"\b(?:pip3?|uv\s+pip|uv\s+tool|pipx|npm|pnpm|yarn|bun|brew|apt-get|apt|go|cargo|gem)\s+(?:install|add|i)\b"
    r"|\bnpx\s+(?:-y\s+)?@?[\w./-]+|\|\s*(?:ba)?sh\b", re.IGNORECASE)
# Keys: the variable names a student can save in Cubbie, and how your files read them.
KEY_NAME = re.compile(r"^(?:VAULT_[A-Z0-9_]+|[A-Z][A-Z0-9_]*_(?:API_KEY|TOKEN|SECRET|CLIENT_ID|USERNAME|PASSWORD|EMAIL|PHONE))$")
TEXT_NAME = re.compile(
    r"""\$\{?([A-Z][A-Z0-9_]*)"""
    r"""|environ(?:\.get)?\s*[\[(]\s*['"]([A-Z][A-Z0-9_]*)"""
    r"""|getenv\s*\(\s*['"]([A-Z][A-Z0-9_]*)"""
    r"""|process\.env(?:\.([A-Z][A-Z0-9_]*)|\[\s*['"]([A-Z][A-Z0-9_]*))""")


class SkillError(ValueError):
    """A reason Cubbie refuses to install the folder, worded like Cubbie's reply."""


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


def _regular(path: Path) -> bool:
    return stat.S_ISREG(os.lstat(path).st_mode) if os.path.lexists(path) else False


def repository(folder: Path) -> tuple[Path, str]:
    """The root a link's target must stay inside (the git repository, else the folder) and the folder's path in it."""
    top = _git(folder, "rev-parse", "--show-toplevel")
    root = Path(top.strip()).resolve() if top else folder
    inside = folder.relative_to(root).as_posix()
    return root, "" if inside == "." else inside


def lfs_files(folder: Path, paths: list[str]) -> set[str]:
    """Paths stored through Git LFS: Cubbie fetches without LFS, so it gets their pointer files."""
    try:
        listed = subprocess.run(["git", "-C", str(folder), "check-attr", "-z", "--stdin", "filter"], input="".join(path + "\0" for path in paths),
                                capture_output=True, check=True, text=True).stdout.split("\0")
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {path for path, _, value in zip(listed[0::3], listed[1::3], listed[2::3]) if value == "lfs"}


def read_files(folder: Path, paths: list[str]) -> tuple[dict[str, bytes], list[str]]:
    """Read the folder the way Cubbie's installer reads a fetched repository, and what it changes or leaves out.

    A symbolic link to a file elsewhere in the repository is installed as a copy of it; links that leave
    the repository, point at folders, links or nothing are left out, and so are git submodules. .git and
    node_modules are not copied. A folder over MAX_FILES files or MAX_TOTAL_BYTES is refused.
    """
    root, where = repository(folder)
    entries = []
    for path in paths:
        relative = posixpath.normpath(path)
        if relative.startswith("../") or relative == ".." or relative.startswith("/"):
            raise SkillError("The Skill contains a path outside its folder.")
        if os.path.islink(folder / path) or not os.path.isdir(folder / path):
            entries.append((relative, os.lstat(folder / path).st_size))
    # Fetching checks every file and link in the folder first, node_modules included.
    if len(entries) > MAX_FILES or sum(size for _, size in entries) > MAX_TOTAL_BYTES:
        raise SkillError(f"{where or 'The Skill'} has {len(entries)} files and {sum(size for _, size in entries) // 1048576} MiB; "
                         f"a Skill can have at most {MAX_FILES} files and {MAX_TOTAL_BYTES // 1048576} MiB.")
    files: dict[str, bytes] = {}
    notes: list[str] = []
    published = None
    stored_in_lfs = lfs_files(folder, [path for path, _ in entries])
    for inside, _ in entries:
        if _skipped(inside):
            continue
        source = folder / inside
        if os.path.islink(source):
            link = os.readlink(source)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(posixpath.join(where, inside)), link))
            if published is None:
                published = set(folder_files(root))
            if (link.startswith("/") or target == ".." or target.startswith("../") or target not in published
                    or _skipped(target) or not _regular(root / target)):
                notes.append(f"{inside} is a link to {link}, which is not a file in the repository; it was left out.")
                continue
            notes.append(f"{inside} is a link to {link}; it is installed as a copy.")
            data, stored = (root / target).read_bytes(), target in lfs_files(root, [target])
        elif stat.S_ISREG(os.lstat(source).st_mode):
            data, stored = source.read_bytes(), inside in stored_in_lfs
        else:
            continue
        if stored or data.startswith(LFS_POINTER):
            notes.append(f"{inside} is a Git LFS pointer; the large file itself is not included.")
        files[inside] = data
    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_TOTAL_BYTES:
        raise SkillError(f"A Skill can have at most {MAX_FILES} files and {MAX_TOTAL_BYTES // 1048576} MiB in total.")
    if "SKILL.md" not in files:
        raise SkillError("No SKILL.md was found at the linked folder.")
    for line in (_git(folder, "ls-files", "-s", "-z", "--", ".") or "").split("\0"):
        meta, _, path = line.partition("\t")
        if meta.startswith("160000 "):  # a submodule's files are never part of the repository's commit
            path = posixpath.join(where, path)
            notes.append(f"{path} is a git submodule; its files are not included.")
    return files, notes


# ---------------------------------------------------------------- SKILL.md


def skill_name(value: str) -> str:
    """A path-safe Skill name: lowercase ASCII letters, digits and single hyphens, at most 64 characters."""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return NOT_NAME.sub("-", text).strip("-")[:MAX_NAME_CHARS].rstrip("-")


def unique_name(name: str, taken) -> str:
    if name not in taken:
        return name
    for number in itertools.count(2):
        suffix = f"-{number}"
        candidate = name[:MAX_NAME_CHARS - len(suffix)].rstrip("-") + suffix
        if candidate not in taken:
            return candidate


def _text(value) -> str:
    return "" if value is None or isinstance(value, (dict, list)) else str(value).strip()


def _lenient(block: str) -> dict:
    """Top-level `key: value` lines of frontmatter YAML rejects; indented lines continue the value above."""
    data, key = {}, None
    for line in block.splitlines():
        match = TOP_LEVEL_KEY.match(line)
        if match:
            key, value = match.group(1), (match.group(2) or "").strip()
            if value and not BLOCK_SCALAR.match(value):
                data[key] = value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value
            elif value or key in ("name", "description"):
                data[key] = ""
            else:
                key = None
        elif key is not None and line[:1] in (" ", "\t"):
            data[key] = f"{data[key]} {line.strip()}".strip()
        elif line.strip():
            key = None
    return data


def read_skill_md(files: dict) -> tuple[str, dict, str, bool]:
    """(SKILL.md text, frontmatter, body, read line by line)."""
    try:
        text = files["SKILL.md"].decode("utf-8")
    except KeyError:
        raise SkillError("No SKILL.md was found at the linked folder.") from None
    except UnicodeDecodeError:
        raise SkillError("SKILL.md must be UTF-8 text.") from None
    content = text.removeprefix("\ufeff")
    match = LENIENT_FRONTMATTER.match(content)
    if not match:
        return text, {}, content, False
    block, body = match.group(1) or "", content[match.end():]
    try:
        data = yaml.safe_load(block) if block.strip() else {}
    except yaml.YAMLError:
        data = None
    if isinstance(data, dict):
        return text, data, body, False
    return text, _lenient(block), body, True


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


def required_commands(frontmatter: dict) -> list:
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        return []
    found = []
    for scope in (metadata, *(value for value in metadata.values() if isinstance(value, dict))):
        requires = scope.get("requires")
        bins = requires.get("bins") if isinstance(requires, dict) else None
        if isinstance(bins, list):
            found += [str(item).strip() for item in bins if BIN_NAME.match(str(item).strip())]
    return list(dict.fromkeys(found))[:10]


def texts(files: dict) -> list:
    found = []
    for data in files.values():
        try:
            found.append(data.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    return found


def install_lines(all_texts) -> list:
    lines = []
    for text in all_texts:
        for raw in text.splitlines():
            line = raw.strip().strip("`").removeprefix("$ ").strip()
            if line and INSTALL_LINE.search(line) and line not in lines:
                lines.append(line[:200])
    return lines[:12]


def key_names(all_texts) -> list:
    found = []
    for text in all_texts:
        for match in TEXT_NAME.finditer(text):
            name = next(group for group in match.groups() if group)
            if KEY_NAME.match(name) and name not in found:
                found.append(name)
    return found[:20]


def list_description(description: str) -> str:
    first = SENTENCE_END.split(description.strip(), maxsplit=1)[0].strip()
    return first if len(first) <= MAX_LIST_DESCRIPTION_CHARS else first[:MAX_LIST_DESCRIPTION_CHARS - 1].rstrip() + "…"


def name_skills(folders: dict, *, fallback_names=(), reserved_names=BUILTIN_SKILL_NAMES) -> dict:
    """The name Cubbie installs each folder of one link under (subpath -> name), and why it changed."""
    wanted, declared = {}, {}
    for path, files in folders.items():
        _, frontmatter, _, _ = read_skill_md(files)
        declared[path] = _text(frontmatter.get("name"))
        candidates = (declared[path], posixpath.basename(path), *fallback_names)
        wanted[path] = declared[path] if NAME_PATTERN.match(declared[path]) else next(filter(None, map(skill_name, candidates)), "skill")
    names = {}
    for path, name in wanted.items():
        if name not in reserved_names and name not in names.values():
            names[path] = name
    taken = set(reserved_names) | set(names.values())
    for path, name in wanted.items():
        if path not in names:
            names[path] = unique_name(name, taken)
            taken.add(names[path])
    fixes = {}
    for path, name in names.items():
        if name == declared[path]:
            fixes[path] = None
        elif not declared[path]:
            fixes[path] = f"SKILL.md gives no name, so it is named {name!r}."
        else:
            reason = ("Skill names use lowercase letters, digits and hyphens" if name == wanted[path] else
                      f"{wanted[path]!r} is a built-in Cubbie Skill" if wanted[path] in reserved_names else
                      f"another Skill from this link is named {wanted[path]!r}")
            fixes[path] = f"SKILL.md names it {declared[path]!r}; installed as {name!r} because {reason}."
    return {path: (names[path], fixes[path]) for path in folders}


def read_package(files: dict, name: str, name_fix=None) -> dict:
    text, frontmatter, body, lenient = read_skill_md(files)
    fixes = ["SKILL.md frontmatter is not valid YAML, so its fields were read line by line."] if lenient else []
    fixes += [name_fix] if name_fix else []
    description = _text(frontmatter.get("description"))
    if not description:
        description = first_paragraph(body)
        if not description:
            raise SkillError("SKILL.md has no description and no instructions to take one from.")
        fixes.append("SKILL.md gives no description, so its first paragraph is used.")
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
        fixes.append(f"The description was shortened to {MAX_DESCRIPTION_CHARS} characters.")
    hashes = {path: hashlib.sha256(raw).hexdigest() for path, raw in sorted(files.items())}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    markdown = texts({path: data for path, data in files.items() if path.endswith(".md")})
    return {"name": name, "description": description, "listed_as": list_description(description), "frontmatter": frontmatter,
            "skill_md": text, "fixes": fixes, "package_sha256": digest, "commands": required_commands(frontmatter),
            "install_lines": install_lines(markdown), "env": key_names(texts(files))}


# ---------------------------------------------------------------- report


def warnings_for(package: dict, files: dict, folder: Path, changes=()) -> list:
    notes = [f"Cubbie would fix this on install: {fix}" for fix in [*package["fixes"], *changes]]
    lines = len(package["skill_md"].splitlines())
    if lines > MAX_BODY_LINES:
        notes.append(f"SKILL.md has {lines} lines; the Agent Skills spec recommends under {MAX_BODY_LINES}. Move details into other files.")
    if "cubbie.yaml" in files:
        notes.append("cubbie.yaml is no longer read: write install commands, keys and logins in SKILL.md instead.")
    for path in sorted(set(PACKAGE_PATH.findall(package["skill_md"]))):
        if path not in files and not any(name.startswith(path + "/") for name in files):
            notes.append(f"SKILL.md refers to {path}, which is not in the folder.")
    if _git(folder, "status", "--porcelain", "--", "."):
        notes.append("There are uncommitted changes; Cubbie installs the pushed commit, not your working copy.")
    # Portability hints: Cubbie accepts these, other Agent Skills clients may not.
    name = package["name"]
    if name.endswith("-") or "--" in name:
        notes.append("The Agent Skills spec does not allow a trailing hyphen or '--' in name; other agents may reject it.")
    extra = sorted(str(key) for key in package["frontmatter"] if key not in SPEC_FIELDS)
    if extra:
        notes.append(f"Frontmatter field(s) {', '.join(extra)} are not in the Agent Skills spec; other agents may reject them.")
    return notes


def expand(folder: Path) -> tuple:
    """The Skill folders a link to `folder` installs: itself when it has SKILL.md, else every folder inside it
    that has one, however deep, the outermost where Skills nest; .git and node_modules are not searched. At most 40."""
    if not folder.is_dir() or _regular(folder / "SKILL.md"):
        return [folder], None
    root = folder.resolve()
    found = sorted({posixpath.dirname(path) for path in folder_files(root)
                    if posixpath.basename(path) == "SKILL.md" and not _skipped(path) and _regular(root / path)},
                   key=lambda path: (path.count("/"), path))
    outer = []
    for path in found:
        if not any(path.startswith(parent + "/") for parent in outer):
            outer.append(path)
    if len(outer) > MAX_BUNDLE_SKILLS:
        return [], (f"The link holds {len(outer)} Skills; at most {MAX_BUNDLE_SKILLS} can be installed from one link. "
                    "Send a link to a folder with fewer.")
    if not outer:
        return [], "No SKILL.md was found at the linked folder or in the folders inside it."
    return [folder / path for path in sorted(outer)], None


def check_all(folder: Path, reserved_names: frozenset = BUILTIN_SKILL_NAMES) -> list:
    """Check a Skill folder, or every Skill a link to a folder of Skills would install together."""
    skills, error = expand(folder)
    if error:
        return [{"folder": str(folder), "ok": False, "error": error}]
    results, readable, changes = {}, {}, {}
    for skill in skills:
        shown, resolved = str(skill), skill.resolve()
        if not resolved.is_dir():
            results[shown] = {"folder": shown, "ok": False, "error": "Not a folder."}
            continue
        try:
            files, changes[shown] = read_files(resolved, folder_files(resolved))
            readable[shown] = (resolved, files)
            read_skill_md(files)
        except SkillError as exc:
            results[shown] = {"folder": shown, "ok": False, "error": str(exc)}
            readable.pop(shown, None)
    named = name_skills({shown: files for shown, (_, files) in readable.items()},
                        fallback_names=(Path(folder).resolve().name,), reserved_names=reserved_names)
    for shown, (resolved, files) in readable.items():
        name, fix = named[shown]
        try:
            package = read_package(files, name, fix)
        except SkillError as exc:
            results[shown] = {"folder": shown, "ok": False, "error": str(exc)}
            continue
        results[shown] = {"folder": shown, "ok": True, "name": package["name"], "description": package["description"],
                          "listed_as": package["listed_as"], "files": len(files), "bytes": sum(len(data) for data in files.values()),
                          "package_sha256": package["package_sha256"], "commands": package["commands"],
                          "install_lines": package["install_lines"], "env": package["env"],
                          "warnings": warnings_for(package, files, resolved, changes[shown])}
    return [results[str(skill)] for skill in skills]


def render(result: dict) -> str:
    if not result["ok"]:
        return f"FAIL {result['folder']}\n  {result['error']}"
    rows = [
        ("description", result["description"]),
        ("in the list", result["listed_as"] if result["listed_as"] != result["description"] else ""),
        ("files", f"{result['files']} file{'s' * (result['files'] != 1)}, {result['bytes']:,} bytes"),
        ("commands", ", ".join(result["commands"])),
        ("install", " | ".join(result["install_lines"])),
        ("keys (env)", ", ".join(result["env"])),
    ]
    lines = [f"OK   {result['name']}  {result['folder']}"]
    lines += [f"  {label + ':':15}{value}" for label, value in rows if value]
    lines += [f"  warning: {note}" for note in result["warnings"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check Skill folders against Cubbie's install rules before pushing them.")
    parser.add_argument("folders", nargs="+", type=Path, help="Skill folders, or a folder of Skills")
    parser.add_argument("--json", action="store_true", help="print one JSON object per folder")
    args = parser.parse_args(argv)
    results = [result for folder in args.folders for result in check_all(folder)]
    for result in results:
        print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

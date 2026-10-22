#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Check Skill folders with the rules Cubbie applies when a student installs a Skill from GitHub.

    python3 scripts/validate_cubbie_skill.py <skill-folder>...    # needs PyYAML
    uv run scripts/validate_cubbie_skill.py <skill-folder>...     # installs PyYAML on the fly

The checks mirror Cubbie's installer (SKILL.md, folder name, built-in names, file limits,
symbolic links and every cubbie.yaml rule) and need nothing but PyYAML. Errors mean Cubbie
will refuse the install. Warnings are local hints: Cubbie does not reject a Skill for them,
but they usually point at something that breaks later or in other agents.
Nothing is installed or run, and no website is contacted.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by hand
    sys.exit("PyYAML is missing: run `pip install pyyaml`, or use `uv run scripts/validate_cubbie_skill.py`.")

# Names of Skills built into Cubbie; a user Skill cannot reuse them.
BUILTIN_SKILL_NAMES = frozenset({"email-to-professor", "study-plan-builder"})

MANIFEST = "cubbie.yaml"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MAX_DESCRIPTION = 320  # UTF-8 bytes
MAX_SKILL_BYTES = 8 * 1024
MAX_REFERENCE_BYTES = 16 * 1024
MAX_BODY_LINES = 500
MAX_FILES = 300
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024

PIP_SPEC = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9][A-Za-z0-9.+!_-]*$")
NPM_SPEC = re.compile(r"^(@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*@\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
BIN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
LOGIN_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
RESERVED_ENV = {"PATH", "HOME", "PWD", "SHELL", "USER", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP",
                "NODE_PATH", "NODE_OPTIONS", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "SSL_CERT_DIR",
                "REQUESTS_CA_BUNDLE", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "TMPDIR",
                "LANG", "LC_ALL", "TZ", "MPLBACKEND", "SAL_USE_VCLPLUGIN"}
RESERVED_ENV_PREFIXES = ("LD_", "DYLD_", "CUBBIE_", "SKILL_", "MODAL_", "BASH_", "NPM_CONFIG_", "PIP_")
# Wildcards on these would cover anyone's subdomain; plain TLDs are rejected separately.
SHARED_SUFFIXES = {"github.io", "githubusercontent.com", "vercel.app", "netlify.app", "pages.dev", "workers.dev",
                   "herokuapp.com", "appspot.com", "web.app", "firebaseapp.com", "run.app", "cloudfunctions.net",
                   "azurewebsites.net", "amazonaws.com", "cloudfront.net", "onrender.com", "fly.dev", "ngrok.io",
                   "ngrok-free.app", "trycloudflare.com", "co.uk", "com.au", "com.cn", "co.jp", "com.br", "co.in"}
MAX_DOMAINS = 10
MAX_SECRETS = 5
MAX_DEPENDENCIES = 20

# Frontmatter fields defined by the Agent Skills specification (agentskills.io/specification).
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
INSTALL_COMMAND = re.compile(r"\b(?:pip3?|npm|pnpm|yarn|uv|apt-get|apt|brew)\s+(?:install|add|i)\b|\|\s*(?:ba)?sh\b")
PACKAGE_PATH = re.compile(r"(?<![\w./-])(?:scripts|references|assets)/[A-Za-z0-9._/-]*[A-Za-z0-9_]")
TRUE_WORDS = {"1", "on", "t", "true", "y", "yes"}
FALSE_WORDS = {"0", "off", "f", "false", "n", "no"}


class SkillError(ValueError):
    """A reason Cubbie refuses to install the folder, worded like Cubbie's reply."""


class _Invalid(Exception):
    def __init__(self, loc: tuple, message: str):
        super().__init__(message)
        self.loc, self.message = loc, message


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


def read_files(folder: Path, paths: list[str]) -> dict[str, bytes]:
    """Read the folder the way Cubbie unpacks a GitHub archive: regular files only, within the size limits."""
    files: dict[str, bytes] = {}
    total = 0
    for path in paths:
        relative = posixpath.normpath(path)
        if relative.startswith("../") or relative == ".." or relative.startswith("/"):
            raise SkillError("The Skill contains a path outside its folder.")
        info = os.lstat(folder / path)
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise SkillError(f"{relative}: links and special files are not allowed in a Skill.")
        if info.st_size > MAX_FILE_BYTES:
            raise SkillError(f"{relative}: files must be at most 1 MiB.")
        total += info.st_size
        if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
            raise SkillError("A Skill can have at most 300 files and 5 MiB in total.")
        files[relative] = (folder / path).read_bytes()
    if "SKILL.md" not in files:
        raise SkillError("No SKILL.md was found at the linked folder.")
    return files


# ---------------------------------------------------------------- cubbie.yaml


def _string(value, loc, *, min_length=0, max_length=None) -> str:
    if not isinstance(value, str):
        raise _Invalid(loc, "Input should be a valid string")
    if len(value) < min_length:
        raise _Invalid(loc, f"String should have at least {min_length} character{'s' * (min_length != 1)}")
    if max_length is not None and len(value) > max_length:
        raise _Invalid(loc, f"String should have at most {max_length} characters")
    return value


def _integer(value, loc) -> int:
    """Integers the way Cubbie's installer reads them: 1, 1.0, true, "1" and " 01 " all count as 1."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                number = None
            if number is not None and number.is_integer():
                return int(number)
    raise _Invalid(loc, "Input should be a valid integer")


def _boolean(value, loc) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in TRUE_WORDS | FALSE_WORDS:
        return value.lower() in TRUE_WORDS
    raise _Invalid(loc, "Input should be a valid boolean")


class _Problems(Exception):
    """Several problems found at once, so the report lists them together like Cubbie's does."""

    def __init__(self, errors: list):
        super().__init__(f"{len(errors)} problems")
        self.errors = errors


def _collect(loc, parse, value):
    """Run a parser and return (result, errors) instead of stopping at the first problem."""
    try:
        return parse(value, loc), []
    except _Invalid as exc:
        return None, [exc]
    except _Problems as group:
        return None, group.errors


def _model(value, loc, fields: dict, required: tuple = ()) -> dict:
    """Check a mapping field by field; unknown keys are rejected so a typo never silently does nothing."""
    if not isinstance(value, dict):
        raise _Invalid(loc, "Input should be a valid dictionary")
    errors = []
    for key in value:
        if not isinstance(key, str):
            errors.append(_Invalid((*loc, key), "Keys should be strings"))
        elif key not in fields:
            errors.append(_Invalid((*loc, key), "Extra inputs are not permitted"))
    parsed = {}
    for key, (default, parse) in fields.items():
        if key in value:
            result, problems = _collect((*loc, key), parse, value[key])
            errors.extend(problems)
            parsed[key] = result
        elif key in required:
            errors.append(_Invalid((*loc, key), "Field required"))
        else:
            parsed[key] = default() if callable(default) else default
    if errors:
        raise _Problems(errors)
    return parsed


def _list(max_items, parse_item):
    def parse(value, loc):
        if not isinstance(value, list):
            raise _Invalid(loc, "Input should be a valid list")
        items, errors = [], []
        for index, item in enumerate(value):
            result, problems = _collect((*loc, index), parse_item, item)
            items.append(result)
            errors.extend(problems)
        if errors:
            raise _Problems(errors)
        if len(items) > max_items:
            raise _Invalid(loc, f"List should have at most {max_items} items after validation, not {len(items)}")
        return items
    return parse


def _str_item(value, loc):
    return _string(value, loc)


def _checked(parse, check):
    def run(value, loc):
        return check(parse(value, loc), loc)
    return run


def _pinned(pattern, message):
    def check(values, loc):
        for value in values:
            if not pattern.match(value):
                raise _Invalid(loc, "Value error, " + message.format(value=value))
        return values
    return check


def validate_domain(value: str) -> str:
    host = str(value or "").strip().lower().rstrip(".")
    wildcard = host.startswith("*.")
    base = host[2:] if wildcard else host
    if not base or len(base) > 253 or "/" in host or ":" in host:
        raise ValueError(f"{value!r}: use a host name only, without scheme, port or path")
    try:
        ipaddress.ip_address(base)
    except ValueError:
        pass
    else:
        raise ValueError(f"{value!r}: IP addresses are not allowed")
    labels = base.split(".")
    if len(labels) < 2 or not all(LABEL.match(label) for label in labels) or labels[-1].isdigit():
        raise ValueError(f"{value!r}: not a valid public host name")
    if wildcard and base in SHARED_SUFFIXES:
        raise ValueError(f"{value!r}: wildcards must stay inside one registered domain")
    return host


def _hosts(values, loc):
    try:
        return [validate_domain(value) for value in values]
    except ValueError as exc:
        raise _Invalid(loc, f"Value error, {exc}") from None


def _download(value, loc):
    def url(text, where):
        text = _string(text, where, max_length=2048)
        if not text.startswith("https://") or any(c.isspace() for c in text):
            raise _Invalid(where, "Value error, download urls must be https:// links")
        return text

    def sha256(text, where):
        text = _string(text, where)
        if not SHA256.match(text.lower()):
            raise _Invalid(where, "Value error, sha256 must be 64 hex characters")
        return text.lower()

    def binary(text, where):
        text = _string(text, where)
        if not BIN_NAME.match(text):
            raise _Invalid(where, "Value error, bin must be a plain executable name")
        return text

    return _model(value, loc, {"url": (None, url), "sha256": (None, sha256), "bin": (None, binary)},
                  required=("url", "sha256", "bin"))


def _secret(value, loc):
    def env(text, where):
        text = _string(text, where)
        if not ENV_NAME.match(text) or text in RESERVED_ENV or text.startswith(RESERVED_ENV_PREFIXES):
            raise _Invalid(where, f"Value error, environment variable {text!r} is invalid or reserved")
        return text

    def help_url(text, where):
        if text is None:
            return None
        text = _string(text, where, max_length=2048)
        if not text.startswith("https://"):
            raise _Invalid(where, "Value error, help_url must be an https:// link")
        return text

    return _model(value, loc, {
        "env": (None, env),
        "label": (None, lambda text, where: _string(text, where, min_length=1, max_length=120)),
        "help_url": (None, help_url),
        "required": (True, _boolean),
    }, required=("env", "label"))


def _login(value, loc):
    def login_id(text, where):
        text = _string(text, where)
        if not LOGIN_ID.fullmatch(text):
            raise _Invalid(where, "String should match pattern '^[a-z0-9][a-z0-9-]{0,31}$'")
        return text

    def status(text, where):
        return None if text is None else _string(text, where, max_length=500)

    return _model(value, loc, {
        "id": (None, login_id),
        "command": (None, lambda text, where: _string(text, where, min_length=1, max_length=500)),
        "status": (None, status),
    }, required=("id", "command"))


def _unique_env(secrets, loc):
    names = [secret["env"] for secret in secrets]
    if len(names) != len(set(names)):
        raise _Invalid(loc, "Value error, secret env names must be unique")
    return secrets


def _version(value, loc):
    if _integer(value, loc) != 1:
        raise _Invalid(loc, "Value error, cubbie must be 1")
    return 1


DEPENDENCIES = {
    "pip": (list, _checked(_list(MAX_DEPENDENCIES, _str_item),
                           _pinned(PIP_SPEC, "pip package {value!r} must be pinned as name==version"))),
    "npm": (list, _checked(_list(MAX_DEPENDENCIES, _str_item),
                           _pinned(NPM_SPEC, "npm package {value!r} must be pinned as name@x.y.z"))),
    "download": (list, _list(5, _download)),
}
NETWORK = {
    "install": (list, _checked(_list(MAX_DOMAINS, _str_item), _hosts)),
    "runtime": (list, _checked(_list(MAX_DOMAINS, _str_item), _hosts)),
}
MANIFEST_FIELDS = {
    "cubbie": (None, _version),
    "dependencies": (lambda: _model({}, (), DEPENDENCIES), lambda value, loc: _model(value, loc, DEPENDENCIES)),
    "network": (lambda: _model({}, (), NETWORK), lambda value, loc: _model(value, loc, NETWORK)),
    "secrets": (list, _checked(_list(MAX_SECRETS, _secret), _unique_env)),
    "login": (list, _list(3, _login)),
}


def empty_manifest() -> dict:
    return _model({"cubbie": 1}, (), MANIFEST_FIELDS)


def parse_manifest(raw: bytes | None) -> dict | None:
    """Return cubbie.yaml as plain data with defaults filled in, or None when the file is absent."""
    if raw is None:
        return None
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError):
        raise SkillError(f"{MANIFEST} is not valid UTF-8 YAML.") from None
    if not isinstance(data, dict):
        raise SkillError(f"{MANIFEST} must be a mapping.")
    try:
        return _model(data, (), MANIFEST_FIELDS, required=("cubbie",))
    except (_Invalid, _Problems) as exc:
        errors = exc.errors if isinstance(exc, _Problems) else [exc]
        problems = "; ".join(f"{'.'.join(str(p) for p in error.loc) or MANIFEST}: {error.message}" for error in errors[:5])
        raise SkillError(f"{MANIFEST} is invalid: {problems}") from None


# ---------------------------------------------------------------- SKILL.md


def validate_package(files: dict[str, bytes], *, directory_name: str,
                     reserved_names: frozenset[str] = BUILTIN_SKILL_NAMES) -> dict:
    try:
        content = files["SKILL.md"].decode("utf-8")
    except KeyError:
        raise SkillError("No SKILL.md was found at the linked folder.") from None
    except UnicodeDecodeError:
        raise SkillError("SKILL.md must be UTF-8 text.") from None
    match = FRONTMATTER.match(content)
    if not match:
        raise SkillError("SKILL.md must start with YAML frontmatter between --- lines.")
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        raise SkillError("SKILL.md frontmatter is not valid YAML.") from None
    if not isinstance(data, dict):
        raise SkillError("SKILL.md frontmatter must be a mapping.")
    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip()
    if not NAME_PATTERN.match(name):
        raise SkillError("name must use lowercase letters, digits and hyphens (at most 64 characters).")
    if name != directory_name:
        raise SkillError(f"name {name!r} must equal the folder name {directory_name!r}.")
    if name in reserved_names:
        raise SkillError(f"{name!r} is the name of a built-in Cubbie Skill; choose another name.")
    if not description or len(description.encode("utf-8")) > MAX_DESCRIPTION:
        raise SkillError(f"description is required and must be at most {MAX_DESCRIPTION} bytes.")
    if len(content.encode("utf-8")) > MAX_SKILL_BYTES or len(content.splitlines()) > MAX_BODY_LINES:
        raise SkillError("SKILL.md must be at most 8 KiB and 500 lines; move details into references/.")
    for path, raw in files.items():
        if not path.startswith("references/"):
            continue
        if not path.endswith(".md"):
            raise SkillError(f"{path}: references must be Markdown files.")
        if len(raw) > MAX_REFERENCE_BYTES:
            raise SkillError(f"{path}: references must be at most 16 KiB.")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            raise SkillError(f"{path}: references must be UTF-8 text.") from None
    manifest = parse_manifest(files.get(MANIFEST))
    hashes = {path: hashlib.sha256(raw).hexdigest() for path, raw in sorted(files.items())}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"name": name, "description": description, "frontmatter": data, "skill_md": content,
            "manifest": manifest or empty_manifest(), "package_sha256": digest}


# ---------------------------------------------------------------- report


def warnings_for(package: dict, files: dict[str, bytes], folder: Path) -> list[str]:
    notes = []
    if INSTALL_COMMAND.search(package["skill_md"]):
        notes.append("SKILL.md mentions an install command; Cubbie never runs it. Declare packages in cubbie.yaml.")
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
        notes.append(f"Frontmatter field(s) {', '.join(extra)} are not in the Agent Skills spec; other agents may reject them. "
                     "Put Cubbie settings in cubbie.yaml.")
    return notes


def check(folder: Path, reserved_names: frozenset[str] = BUILTIN_SKILL_NAMES, directory_name: str | None = None) -> dict:
    """directory_name overrides the folder name, e.g. with the repository name for a Skill at a repository root."""
    shown, folder = str(folder), folder.resolve()
    if not folder.is_dir():
        return {"folder": shown, "ok": False, "error": "Not a folder."}
    try:
        files = read_files(folder, folder_files(folder))
        package = validate_package(files, directory_name=directory_name or folder.name, reserved_names=reserved_names)
    except SkillError as exc:
        return {"folder": shown, "ok": False, "error": str(exc)}
    return {"folder": shown, "ok": True, "name": package["name"], "description": package["description"],
            "files": len(files), "bytes": sum(len(data) for data in files.values()),
            "package_sha256": package["package_sha256"], "manifest": package["manifest"],
            "warnings": warnings_for(package, files, folder)}


def render(result: dict) -> str:
    if not result["ok"]:
        return f"FAIL {result['folder']}\n  {result['error']}"
    manifest = result["manifest"]
    deps, network = manifest["dependencies"], manifest["network"]
    rows = [
        ("description", result["description"]),
        ("files", f"{result['files']} file{'s' * (result['files'] != 1)}, {result['bytes']:,} bytes"),
        ("pip", ", ".join(deps["pip"])),
        ("npm", ", ".join(deps["npm"])),
        ("downloads", ", ".join(item["url"] for item in deps["download"])),
        ("install hosts", ", ".join(network["install"])),
        ("runtime hosts", ", ".join(network["runtime"])),
        ("keys", ", ".join(f"{item['env']} ({item['label']})" for item in manifest["secrets"])),
        ("logins", ", ".join(f"{item['id']}: {item['command']}" for item in manifest["login"])),
    ]
    lines = [f"OK   {result['name']}  {result['folder']}"]
    lines += [f"  {label + ':':15}{value}" for label, value in rows if value]
    lines += [f"  warning: {note}" for note in result["warnings"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Skill folders against Cubbie's install rules before pushing them to GitHub.")
    parser.add_argument("folders", nargs="+", type=Path, help="Skill folders; each folder name must equal the Skill name")
    parser.add_argument("--json", action="store_true", help="print one JSON object per folder")
    args = parser.parse_args(argv)
    results = [check(folder) for folder in args.folders]
    for result in results:
        print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

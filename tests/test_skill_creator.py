"""Offline tests for the cubbie-skill-creator scripts (no network; needs git and PyYAML).

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "cubbie-skill-creator" / "scripts"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    import yaml  # noqa: F401
    validator, links = load("validate_cubbie_skill"), load("github_link")
except ImportError:
    validator = links = None


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=GIT_ENV)


def skill(root: Path, path: str, name: str, body: str = "") -> None:
    (root / path).mkdir(parents=True, exist_ok=True)
    (root / path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Does {name}.\n---\n{body}")


@unittest.skipIf(validator is None, "PyYAML is not installed")
class InstallRulesTest(unittest.TestCase):
    """The rules of Cubbie's installer (app/skills/source.py) as of 2026-10-24."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        git(self.root, "init", "-q", "-b", "main")

    def test_a_folder_of_skills_finds_them_at_any_depth_outermost_first(self):
        skill(self.root, ".claude/skills/a", "a")
        skill(self.root, ".agents/skills/c", "c")
        skill(self.root, "plugins/p/skills/d", "d")
        skill(self.root, "plugins/p/skills/d/inner", "inner")
        skill(self.root, "skills/b/node_modules/x", "hidden")
        skill(self.root, "skills/b", "b")
        found, error = validator.expand(self.root)
        self.assertIsNone(error)
        self.assertEqual([p.relative_to(self.root).as_posix() for p in found],
                         [".agents/skills/c", ".claude/skills/a", "plugins/p/skills/d", "skills/b"])
        empty = self.root / "empty"
        empty.mkdir()
        (empty / "notes.txt").write_text("x")
        self.assertEqual(validator.expand(empty)[1], "No SKILL.md was found at the linked folder or in the folders inside it.")
        for i in range(41):
            skill(self.root, f"many/s{i}", f"s{i}")
        self.assertIn("The link holds 41 Skills; at most 40", validator.expand(self.root / "many")[1])

    def test_links_inside_the_repository_are_copied_and_others_left_out(self):
        skill(self.root, "skills/b", "b", "Read references/shared.md\n")
        (self.root / "shared").mkdir()
        (self.root / "shared/cities.md").write_text("# Shared cities\n")
        (self.root / "skills/b/references").mkdir()
        os.symlink("../../../shared/cities.md", self.root / "skills/b/references/shared.md")
        os.symlink("/etc/hosts", self.root / "skills/b/outside")
        os.symlink("../../shared", self.root / "skills/b/folder")
        (self.root / "skills/b/big.bin").write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:0\nsize 9\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "skills")
        [result] = validator.check_all(self.root / "skills/b")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["files"], 3)
        fixes = [note.removeprefix("Cubbie would fix this on install: ") for note in result["warnings"]]
        self.assertIn("references/shared.md is a link to ../../../shared/cities.md; it is installed as a copy.", fixes)
        self.assertIn("outside is a link to /etc/hosts, which is not a file in the repository; it was left out.", fixes)
        self.assertIn("folder is a link to ../../shared, which is not a file in the repository; it was left out.", fixes)
        self.assertIn("big.bin is a Git LFS pointer; the large file itself is not included.", fixes)
        self.assertNotIn("SKILL.md refers to references/shared.md, which is not in the folder.", result["warnings"])

    def test_the_limits_are_1000_files_and_50_mib(self):
        skill(self.root, "big", "big")
        for i in range(1000):
            (self.root / f"big/{i}.txt").write_text("")
        [result] = validator.check_all(self.root / "big")
        self.assertEqual(result["error"], "big has 1001 files and 0 MiB; a Skill can have at most 1000 files and 50 MiB.")
        skill(self.root, "fits", "fits")
        (self.root / "fits/data.bin").write_bytes(b"\0" * (2 * 1024 * 1024))
        self.assertTrue(validator.check_all(self.root / "fits")[0]["ok"])


@unittest.skipIf(links is None, "PyYAML is not installed")
class InstallLinkTest(unittest.TestCase):
    def test_links_follow_each_hosts_form(self):
        commit = "a" * 40
        self.assertEqual(links.web_link("github.com", "o/r", "feature/x", "skills/my skill"),
                         "https://github.com/o/r/tree/feature/x/skills/my%20skill")
        self.assertEqual(links.web_link("gitlab.com", "g/sub/r", commit, "skills/b"),
                         f"https://gitlab.com/g/sub/r/-/tree/{commit}/skills/b")
        self.assertIsNone(links.web_link("codeberg.org", "o/r", commit, "skills/b"))
        for remote, host, path in [("git@github.com:o/r.git", "github.com", "o/r"),
                                   ("https://gitlab.com/g/sub/r.git", "gitlab.com", "g/sub/r"),
                                   ("ssh://git@gitee.com:22/o/r", "gitee.com", "o/r")]:
            match = links.REMOTE.match(remote)
            self.assertEqual(((match["host"] or match["scp"]), match["path"]), (host, path))


if __name__ == "__main__":
    unittest.main()

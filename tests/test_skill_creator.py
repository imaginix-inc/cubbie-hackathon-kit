"""Offline tests for the cubbie-skill-creator scripts (no network; needs git and PyYAML).

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

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
class SkillChecksTest(unittest.TestCase):
    """The checks follow the Agent Skills format; only a missing SKILL.md fails, since Cubbie copes with the rest."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")

    def check(self, path):
        [result] = validator.check_all(self.root / path)
        return result

    def test_a_folder_of_skills_finds_them_at_any_depth_outermost_first_with_no_count_limit(self):
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
        for i in range(41):
            skill(self.root, f"many/s{i}", f"s{i}")
        results = validator.check_all(self.root / "many")
        self.assertEqual(len(results), 41)
        self.assertTrue(all(result["ok"] for result in results))

    def test_only_a_folder_without_skill_md_fails(self):
        empty = self.root / "empty"
        empty.mkdir()
        (empty / "notes.txt").write_text("x")
        self.assertEqual(validator.check_all(empty),
                         [{"folder": str(empty), "ok": False, "error": "No SKILL.md in this folder or the folders inside it."}])
        (self.root / "latin1").mkdir()
        (self.root / "latin1/SKILL.md").write_bytes("---\nname: caf\xe9\n---\n".encode("latin-1"))
        self.assertEqual(self.check("latin1")["error"], "SKILL.md is not UTF-8 text.")

    def test_missing_name_and_description_warn_and_fall_back_to_folder_and_first_paragraph(self):
        (self.root / "plain").mkdir()
        (self.root / "plain/SKILL.md").write_text("# Plain\n\nChecks the dining hall menu.\n")
        result = self.check("plain")
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["name"], result["description"]), ("plain", "Checks the dining hall menu."))
        self.assertIn("SKILL.md has no frontmatter", result["warnings"][0])
        (self.root / "empty-fields").mkdir()
        (self.root / "empty-fields/SKILL.md").write_text("---\nlicense: MIT\n---\nDoes things.\n")
        warnings = self.check("empty-fields")["warnings"]
        self.assertIn("SKILL.md gives no name; Cubbie lists the Skill as 'empty-fields', its folder name.", warnings)
        self.assertTrue(any(w.startswith("SKILL.md gives no description; Cubbie uses its first paragraph") for w in warnings))
        (self.root / "bad-yaml").mkdir()
        (self.root / "bad-yaml/SKILL.md").write_text("---\nname: bad-yaml\ndescription: Use when: it rains: often\n---\nx\n")
        result = self.check("bad-yaml")
        self.assertTrue(result["ok"])
        self.assertIn("can't be read as YAML", result["warnings"][0])

    def test_description_length_and_name_format_are_warnings(self):
        skill(self.root, "short", "short")
        self.assertEqual(self.check("short")["warnings"], ["There are uncommitted changes; Cubbie fetches the pushed commit, "
                                                           "not your working copy."])
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "short")
        self.assertEqual(self.check("short")["warnings"], [])
        for chars, expected in ((201, "Cubbie's Skill list shows only the first sentence"), (1025, "the Agent Skills format allows 1024")):
            (self.root / f"long{chars}").mkdir()
            (self.root / f"long{chars}/SKILL.md").write_text(f"---\nname: long\ndescription: {'x' * chars}\n---\n")
            result = self.check(f"long{chars}")
            self.assertTrue(result["ok"])
            self.assertIn(expected, " ".join(result["warnings"]))
        # Only the first sentence is listed, so a long description with a short first sentence is fine.
        (self.root / "sentences").mkdir()
        (self.root / "sentences/SKILL.md").write_text(f"---\nname: sentences\ndescription: Does a thing. {'y' * 300}\n---\n")
        self.assertFalse([note for note in self.check("sentences")["warnings"] if "first sentence" in note])
        skill(self.root, "Weather Buddy", "Weather Buddy")
        result = self.check("Weather Buddy")
        self.assertEqual(result["name"], "Weather Buddy")
        self.assertIn("isn't lowercase letters, digits and single hyphens", " ".join(result["warnings"]))

    def test_cubbie_yaml_missing_files_and_outside_links_warn(self):
        skill(self.root, "skills/b", "b", "Run `python3 scripts/run.py`. Read references/shared.md and references/inside.md.\n")
        (self.root / "skills/b/cubbie.yaml").write_text("name: b\n")
        (self.root / "shared").mkdir()
        (self.root / "shared/cities.md").write_text("# Shared cities\n")
        (self.root / "skills/b/references").mkdir()
        (self.root / "skills/b/references/real.md").write_text("# Real\n")
        os.symlink("../../../shared/cities.md", self.root / "skills/b/references/shared.md")
        os.symlink("real.md", self.root / "skills/b/references/inside.md")
        os.symlink("/etc/hosts", self.root / "skills/b/outside")
        result = self.check("skills/b")
        self.assertTrue(result["ok"], result)
        warnings = " | ".join(result["warnings"])
        self.assertIn("cubbie.yaml is not needed and Cubbie ignores it", warnings)
        self.assertIn("SKILL.md refers to scripts/run.py, which is not in the folder.", warnings)
        self.assertIn("references/shared.md is a link to ../../../shared/cities.md, outside the Skill folder", warnings)
        self.assertIn("outside is a link to /etc/hosts, outside the Skill folder", warnings)
        self.assertNotIn("references/inside.md is a link", warnings)

    def test_large_files_and_repositories_warn_without_failing(self):
        skill(self.root, "big", "big")
        for i in range(1001):
            (self.root / f"big/{i}.txt").write_text("")
        (self.root / "big/data.bin").write_bytes(b"\0" * 2048)
        self.assertTrue(self.check("big")["ok"])
        with mock.patch.object(validator, "LARGE_FILE_BYTES", 1024), \
                mock.patch.object(validator, "LARGE_REPOSITORY_FILES", 1000):
            validator.repository_size.cache_clear()
            result = self.check("big")
        validator.repository_size.cache_clear()
        self.assertTrue(result["ok"])
        warnings = " | ".join(result["warnings"])
        self.assertIn("data.bin is 0 MiB; large files make the Skill slow to fetch.", warnings)
        self.assertIn("The repository has 1,003 files", warnings)

    def test_the_kits_examples_pass_without_warnings(self):
        results = validator.check_all(Path(__file__).resolve().parents[1] / "examples")
        self.assertEqual(sorted(result["name"] for result in results),
                         ["canvas-deadline-nudge", "netlify-publish", "weather-before-class"])
        for result in results:
            self.assertTrue(result["ok"], result)
            self.assertEqual([w for w in result["warnings"] if not w.startswith("There are uncommitted changes")], [])

    def test_the_command_line_prints_ok_fail_and_warning_lines(self):
        skill(self.root, "good", "good")
        (self.root / "none").mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = validator.main([str(self.root / "good"), str(self.root / "none")])
        self.assertEqual(code, 1)
        lines = out.getvalue().splitlines()
        self.assertTrue(lines[0].startswith("OK   good  "))
        self.assertIn("  warning: There are uncommitted changes; Cubbie fetches the pushed commit, not your working copy.", lines)
        self.assertIn(f"FAIL {self.root / 'none'}", lines)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(validator.main([str(self.root / "good")]), 0)


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

    def test_a_pushed_skill_gets_branch_and_pinned_links(self):
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        bare, repo = root / "remote.git", root / "repo"
        git(root, "init", "-q", "--bare", str(bare))
        git(root, "init", "-q", "-b", "main", str(repo))
        git(repo, "remote", "add", "origin", "https://github.com/night-owls/dorm_chef.v2.git")
        git(repo, "remote", "set-url", "--push", "origin", str(bare))
        skill(repo, "skills/dorm-chef", "dorm-chef")
        (repo / "skills/notes").mkdir()
        (repo / "skills/notes/README.md").write_text("Not a Skill.\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "skill")
        git(repo, "push", "-q", "origin", "main")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
        result = links.link_for(repo / "skills/dorm-chef", offline=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["pinned"], f"https://github.com/night-owls/dorm_chef.v2/tree/{commit}/skills/dorm-chef")
        self.assertEqual(result["latest"], "https://github.com/night-owls/dorm_chef.v2/tree/main/skills/dorm-chef")
        result = links.link_for(repo / "skills/notes", offline=True)
        self.assertFalse(result["ok"])
        self.assertIn("No SKILL.md in this folder or the folders inside it.", " ".join(result["problems"]))


if __name__ == "__main__":
    unittest.main()

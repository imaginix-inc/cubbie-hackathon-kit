"""Offline tests for skills/cubbie-hackathon/scripts/hackathon.py (no network).

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import stat
import tempfile
import time
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "cubbie-hackathon" / "scripts" / "hackathon.py"
spec = importlib.util.spec_from_file_location("hackathon", SCRIPT)
hk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hk)

ME = "11111111-1111-1111-1111-111111111111"
MATE = "22222222-2222-2222-2222-222222222222"


def fake_jwt(email="ana@school.edu", sub=ME, exp_in=3600) -> str:
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'HS256'})}.{enc({'email': email, 'sub': sub, 'exp': int(time.time()) + exp_in})}.sig"


def iso(delta_hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_hours)).isoformat()


OPEN = {"skills_open_at": iso(-1), "skills_close_at": None, "general_open_at": iso(-1), "general_close_at": iso(5),
        "voting_open_at": iso(-1), "voting_close_at": None, "votes_per_voter": 5, "show_vote_counts": True}

TRACK1 = {"team": "Night Owls", "name": "Dorm Chef", "pitch": "It's 1 AM and nothing is open.",
          "members": [{"name": "Ana", "email": "ana@school.edu"}],
          "repo": "https://github.com/owls/dorm-chef", "platform": "tiktok",
          "post": "https://www.tiktok.com/@owls/video/1", "website": "", "video": ""}


def saved_row(track="skills", owner=ME, **over):
    row = {"id": f"id-{track}", "track": track, "owner_id": owner, "team_name": "Night Owls", "name": "Dorm Chef",
           "pitch": "It's 1 AM and nothing is open.", "platform": "tiktok" if track == "skills" else "",
           "link": "https://github.com/owls/dorm-chef" if track == "skills" else "",
           "video_url": "https://www.tiktok.com/@owls/video/1" if track == "skills" else "",
           "repo_url": "" if track == "skills" else "https://github.com/owls/study",
           "members": [{"name": "Ana", "email": "ana@school.edu"}], "status": "published", "social_urls": [],
           "review_note": ""}
    row.update(over)
    return row


class FakeBackend:
    """Stands in for hackathon.request: records calls, answers like Supabase."""

    def __init__(self, settings=None, mine=None, gallery=None):
        self.settings = settings or OPEN
        self.mine = mine or []
        self.gallery = gallery
        self.calls = []

    def __call__(self, method, path, body=None, token=None):
        self.calls.append((method, path, body, token))
        if path.startswith("/rest/v1/settings"):
            return [self.settings]
        if path == "/rest/v1/rpc/my_submissions":
            return self.mine
        if path == "/rest/v1/rpc/submit_entry":
            row = {"id": f"id-{body['p_track']}", "track": body["p_track"], "team_name": body["p_team_name"],
                   "name": body["p_name"] or body["p_team_name"], "status": "published"}
            return row
        if path in ("/rest/v1/rpc/get_leaderboard", "/rest/v1/rpc/get_gallery"):
            return self.gallery if self.gallery is not None else [{"id": "id-skills"}, {"id": "id-agents"}]
        if path == "/rest/v1/rpc/update_launch_links":
            return {"video_url": "https://www.tiktok.com/@owls/video/1", "social_urls": body["p_social_urls"]}
        if path == "/rest/v1/rpc/is_school_email":
            return True
        if path == "/auth/v1/otp":
            return {}
        if path == "/auth/v1/verify":
            return {"access_token": fake_jwt(), "refresh_token": "never-saved", "user": {"email": "ana@school.edu"}}
        if path == "/auth/v1/logout":
            return None
        raise AssertionError(f"unexpected call {method} {path}")

    def sent(self, path):
        return [c for c in self.calls if c[1] == path]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = unittest.mock.patch.dict(os.environ, {"CUBBIE_HACKATHON_HOME": self.tmp.name})
        self.env.start()
        self.backend = FakeBackend()
        self.patch = unittest.mock.patch.object(hk, "request", self.backend)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def sign_in(self, **kw):
        hk.save_token(fake_jwt(**kw))

    def run_cli(self, *argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = hk.main(list(argv))
        return code, stdout.getvalue(), stderr.getvalue()



class TimeAndWindows(unittest.TestCase):
    def test_parses_postgres_timestamps(self):
        for text in ("2026-10-22T10:55:43.092828+00:00", "2026-10-22T10:55:43.09+00:00", "2026-10-22 10:55:43+00",
                     "2026-10-22T10:55:43Z"):
            self.assertEqual(hk.parse_time(text).astimezone(timezone.utc).replace(microsecond=0),
                             datetime(2026, 10, 22, 10, 55, 43, tzinfo=timezone.utc), text)
        self.assertIsNone(hk.parse_time(None))

    def test_window_states_match_track_open(self):
        now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
        self.assertEqual(hk.window(None, None, now)["state"], "not open yet")
        self.assertEqual(hk.window("2026-10-22T13:00:00+00:00", None, now)["state"], "not open yet")
        self.assertTrue(hk.window("2026-10-22T11:00:00+00:00", None, now)["open"])
        self.assertTrue(hk.window("2026-10-22T11:00:00+00:00", "2026-10-22T12:00:01+00:00", now)["open"])
        self.assertEqual(hk.window("2026-10-22T11:00:00+00:00", "2026-10-22T12:00:00+00:00", now)["state"], "closed")


class Checks(unittest.TestCase):
    def test_valid_track1_entry_passes(self):
        self.assertEqual(hk.check_entry("skills", dict(TRACK1)), [])

    def test_track1_rules(self):
        cases = {
            "repo": ("https://gitlab.com/owls/x", "GitHub repo"),
            "platform": ("youtube", "--platform tiktok"),
            "post": ("https://www.instagram.com/reel/1", "TikTok link"),
            "pitch": ("x" * 141, "140 characters"),
            "team": ("", "team name"),
        }
        for key, (value, expected) in cases.items():
            e = dict(TRACK1, **{key: value})
            self.assertTrue(any(expected in p for p in hk.check_entry("skills", e)), (key, hk.check_entry("skills", e)))

    def test_members(self):
        five = [{"name": f"P{i}", "email": f"p{i}@school.edu"} for i in range(5)]
        self.assertIn("List 1 to 4", " ".join(hk.check_entry("skills", dict(TRACK1, members=five))))
        self.assertIn("List 1 to 4", " ".join(hk.check_entry("skills", dict(TRACK1, members=[]))))
        dup = [{"name": "A", "email": "a@school.edu"}, {"name": "B", "email": "A@School.edu"}]
        self.assertIn("their own email", " ".join(hk.check_entry("skills", dict(TRACK1, members=dup))))
        bad = [{"name": "A", "email": "not-an-email"}]
        self.assertIn("name and an email", " ".join(hk.check_entry("skills", dict(TRACK1, members=bad))))
        self.assertEqual(hk.parse_member(" Ana Ruiz <Ana@School.edu> "), {"name": "Ana Ruiz", "email": "Ana@School.edu"})
        with self.assertRaises(hk.Problem):
            hk.parse_member("ana@school.edu")

    def test_tracks_2_and_3(self):
        e = dict(TRACK1, platform="", post="", repo="https://github.com/owls/study", website="https://study.example.com")
        self.assertEqual(hk.check_entry("agents", e), [])
        self.assertIn("need the project's GitHub repo", " ".join(hk.check_entry("groupchat", dict(e, repo=""))))
        self.assertIn("no social post field", " ".join(hk.check_entry("agents", dict(e, post="https://tiktok.com/x"))))
        self.assertIn("https://", " ".join(hk.check_entry("agents", dict(e, website="http://study.example.com"))))

    def test_rpc_args_map_fields_like_the_site(self):
        a = hk.rpc_args("skills", dict(TRACK1, members=[{"name": " Ana ", "email": " ANA@school.edu "}]))
        self.assertEqual(a["p_link"], TRACK1["repo"])
        self.assertEqual(a["p_video_url"], TRACK1["post"])
        self.assertEqual(a["p_repo_url"], "")
        self.assertEqual(a["p_members"], [{"name": "Ana", "email": "ana@school.edu"}])
        e = dict(TRACK1, platform="", post="", repo="https://github.com/owls/study", website="https://s.example.com",
                 video="https://youtu.be/x")
        b = hk.rpc_args("agents", e)
        self.assertEqual((b["p_link"], b["p_video_url"], b["p_repo_url"], b["p_platform"]),
                         ("https://s.example.com", "https://youtu.be/x", "https://github.com/owls/study", ""))

    def test_saved_rows_round_trip(self):
        self.assertEqual(hk.entry_from_row(saved_row())["repo"], "https://github.com/owls/dorm-chef")
        self.assertEqual(hk.entry_from_row(saved_row("agents"))["repo"], "https://github.com/owls/study")

    def test_track_aliases(self):
        self.assertEqual([hk.track_id(t) for t in ("1", "Track 2", "groupchat")], ["skills", "agents", "groupchat"])
        with self.assertRaises(hk.Problem):
            hk.track_id("4")


class Session(Base):
    def test_verify_saves_only_the_access_token(self):
        code, out, _ = self.run_cli("verify", "--email", "Ana@School.edu", "--code", "123456")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.backend.sent("/auth/v1/verify")[0][2], {"type": "email", "email": "ana@school.edu", "token": "123456"})
        path = hk.session_path()
        self.assertEqual(set(json.loads(path.read_text())), {"access_token"})
        self.assertNotIn("never-saved", path.read_text())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_bad_code_shape_is_refused_locally(self):
        code, _, err = self.run_cli("verify", "--email", "a@school.edu", "--code", "12345")
        self.assertEqual(code, 1)
        self.assertIn("6 digits", err)
        self.assertEqual(self.backend.sent("/auth/v1/verify"), [])

    def test_login_requests_a_code_and_says_what_next(self):
        code, out, _ = self.run_cli("login", "--email", "ana@school.edu")
        self.assertEqual(code, 0)
        self.assertEqual(self.backend.sent("/auth/v1/otp")[0][2], {"email": "ana@school.edu", "create_user": True})
        self.assertIn("verify --email ana@school.edu", out)

    def test_expired_token_counts_as_signed_out(self):
        self.sign_in(exp_in=-10)
        code, _, err = self.run_cli("mine")
        self.assertEqual(code, 1)
        self.assertIn("expired", err)

    def test_logout_removes_the_file(self):
        self.sign_in()
        self.assertEqual(self.run_cli("logout")[0], 0)
        self.assertFalse(hk.session_path().exists())


class Submit(Base):
    ARGS = ["submit", "--track", "skills", "--team", "Night Owls", "--name", "Dorm Chef", "--pitch",
            "It's 1 AM and nothing is open.", "--member", "Ana <ana@school.edu>", "--repo",
            "https://www.github.com/owls/dorm-chef", "--platform", "TikTok", "--post", "https://www.tiktok.com/@owls/video/1"]

    def test_preview_sends_nothing(self):
        self.sign_in()
        code, out, _ = self.run_cli(*self.ARGS)
        self.assertEqual(code, 0, out)
        self.assertIn("Nothing sent", out)
        self.assertEqual(self.backend.sent("/rest/v1/rpc/submit_entry"), [])

    def test_yes_sends_and_checks_the_gallery(self):
        self.sign_in()
        code, out, err = self.run_cli(*self.ARGS, "--yes")
        self.assertEqual(code, 0, err)
        (_, _, body, token), = self.backend.sent("/rest/v1/rpc/submit_entry")
        self.assertEqual(body["p_link"], "https://github.com/owls/dorm-chef")  # www. dropped like the database does
        self.assertEqual(body["p_platform"], "tiktok")
        self.assertTrue(token)
        self.assertIn("in the public gallery now", out)
        self.assertIn(hk.GALLERY_URL, out)

    def test_update_keeps_fields_not_given(self):
        self.sign_in()
        self.backend.mine = [saved_row()]
        code, out, err = self.run_cli("submit", "--track", "1", "--pitch", "New one-liner.", "--yes")
        self.assertEqual(code, 0, err)
        body = self.backend.sent("/rest/v1/rpc/submit_entry")[0][2]
        self.assertEqual(body["p_pitch"], "New one-liner.")
        self.assertEqual(body["p_link"], "https://github.com/owls/dorm-chef")
        self.assertEqual(body["p_members"], [{"name": "Ana", "email": "ana@school.edu"}])
        self.assertIn("Updated", out)

    def test_teammate_cannot_edit(self):
        self.sign_in(email="ben@school.edu", sub=MATE)
        self.backend.mine = [saved_row(owner=ME)]
        code, _, err = self.run_cli("submit", "--track", "skills", "--pitch", "x", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("whoever submitted it can update it", err)
        self.assertEqual(self.backend.sent("/rest/v1/rpc/submit_entry"), [])

    def test_closed_window_stops_before_sending(self):
        self.sign_in()
        self.backend.settings = dict(OPEN, skills_close_at=iso(-0.5))
        code, _, err = self.run_cli(*self.ARGS, "--yes")
        self.assertEqual(code, 1)
        self.assertIn("not open", err)
        self.assertEqual(self.backend.sent("/rest/v1/rpc/submit_entry"), [])

    def test_sent_back_entry_can_be_edited_after_the_window(self):
        self.sign_in()
        self.backend.settings = dict(OPEN, skills_close_at=iso(-0.5))
        self.backend.mine = [saved_row(status="changes_requested", review_note="Say which dining halls.")]
        code, _, err = self.run_cli("submit", "--track", "skills", "--pitch", "Covers every dining hall.", "--yes")
        self.assertEqual(code, 0, err)

    def test_track2_needs_track1_first(self):
        self.sign_in()
        code, _, err = self.run_cli("submit", "--track", "agents", "--team", "Owls", "--pitch", "p",
                                    "--member", "Ana <ana@school.edu>", "--repo", "https://github.com/owls/study", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("submitted Track 1", err)

    def test_invalid_fields_are_listed_not_sent(self):
        self.sign_in()
        code, _, err = self.run_cli("submit", "--track", "skills", "--team", "Owls", "--pitch", "p", "--member",
                                    "Ana <ana@school.edu>", "--repo", "https://github.com/owls", "--platform", "tiktok",
                                    "--post", "https://www.instagram.com/reel/1", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("GitHub repo", err)
        self.assertIn("TikTok link", err)
        self.assertEqual(self.backend.sent("/rest/v1/rpc/submit_entry"), [])

    def test_entry_file(self):
        self.sign_in()
        path = Path(self.tmp.name) / "entry.json"
        path.write_text(json.dumps(dict(TRACK1, members=["Ana <ana@school.edu>", {"name": "Ben", "email": "ben@school.edu"}])))
        code, _, err = self.run_cli("submit", "--track", "skills", "--file", str(path), "--yes")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.backend.sent("/rest/v1/rpc/submit_entry")[0][2]["p_members"]), 2)


class Posts(Base):
    def test_add_keeps_existing_and_caps_at_five(self):
        self.sign_in()
        self.backend.mine = [saved_row(social_urls=["https://www.instagram.com/reel/a"])]
        code, _, err = self.run_cli("posts", "--add", "https://www.instagram.com/reel/b", "--yes")
        self.assertEqual(code, 0, err)
        body = self.backend.sent("/rest/v1/rpc/update_launch_links")[0][2]
        self.assertEqual(body["p_social_urls"], ["https://www.instagram.com/reel/a", "https://www.instagram.com/reel/b"])
        self.assertIsNone(body["p_video_url"])  # the main post stays as it is
        self.backend.mine = [saved_row(social_urls=[f"https://www.instagram.com/reel/{i}" for i in range(5)])]
        code, _, err = self.run_cli("posts", "--add", "https://www.instagram.com/reel/z", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("Up to 5", err)


class Errors(unittest.TestCase):
    def test_database_messages_pass_through(self):
        raw = json.dumps({"code": "P0001", "message": "Tracks 2 and 3 open once your team has submitted Track 1."}).encode()
        self.assertEqual(hk.explain_error(400, raw), "Tracks 2 and 3 open once your team has submitted Track 1.")

    def test_auth_errors(self):
        self.assertIn("didn't work", hk.explain_error(403, json.dumps({"code": 403, "error_code": "otp_expired",
                                                                         "msg": "Token has expired or is invalid"}).encode()))
        self.assertIn("Wait a minute", hk.explain_error(429, json.dumps({"error_code": "over_email_send_rate_limit"}).encode()))
        self.assertIn("expired", hk.explain_error(401, json.dumps({"code": "PGRST301", "message": "JWT expired"}).encode()))
        self.assertIn("git pull", hk.explain_error(404, json.dumps({"code": "PGRST202", "message": "no function"}).encode()))


if __name__ == "__main__":
    unittest.main()

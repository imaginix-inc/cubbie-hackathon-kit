#!/usr/bin/env python3
"""Maintainers only: run scripts/hackathon.py against the hosted hackathon project, then delete what it made.

    python3 tests/live_test.py

Needs the Supabase CLI logged in with access to the project (`supabase login`); the service-role key is
fetched at run time with `supabase projects api-keys` and never written anywhere. Two test users
(@cubbie.test) are created through the admin API and signed in with the script's own `verify` command,
using a code from the admin API's generate_link, so no email is sent. Their entries are live in the public
gallery for well under a minute. At the end every submission, audit_log row and auth user it created is
deleted, and the deletion is checked.

It does not change settings: the Track 1 and Tracks 2/3 windows must already be open.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REF = os.environ.get("SUPABASE_PROJECT_REF", "mputiuoljihmxpqhmpeb")
URL = f"https://{REF}.supabase.co"
SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "cubbie-hackathon" / "scripts" / "hackathon.py"

spec = importlib.util.spec_from_file_location("hackathon", SCRIPT)
hk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hk)

results: list = []


def check(ok: bool, what: str) -> None:
    results.append((ok, what))
    print("• PASS" if ok else "• FAIL", what, flush=True)


def service_key() -> str:
    raw = subprocess.run(["supabase", "projects", "api-keys", "--project-ref", REF, "-o", "json"],
                         check=True, capture_output=True, text=True).stdout
    return next(k["api_key"] for k in json.loads(raw) if k.get("name") == "service_role")


SERVICE = service_key()


def admin(method: str, path: str, body=None, prefer: str = "return=representation"):
    headers = {"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}", "Content-Type": "application/json",
               "Prefer": prefer, "User-Agent": "cubbie-hackathon-kit-live-test"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{URL}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def cli(home: str, *argv: str) -> tuple:
    env = dict(os.environ, CUBBIE_HACKATHON_HOME=home)
    p = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


def cli_json(home: str, *argv: str):
    code, out, err = cli(home, "--json", *argv)
    return code, json.loads(out) if out.strip() else None, err


def create_user(email: str) -> tuple:
    status, user = admin("POST", "/auth/v1/admin/users", {"email": email, "email_confirm": True})
    assert status == 200, (status, user)
    status, link = admin("POST", "/auth/v1/admin/generate_link", {"type": "magiclink", "email": email})
    assert status == 200 and link.get("email_otp"), (status, link)
    return user["id"], link["email_otp"]


def main() -> int:
    now = datetime.now(timezone.utc)
    if now.hour % 3 == 0 and 10 <= now.minute <= 25:
        print("The social tracker runs at minute 17 every 3 hours (UTC) and would read the test posts; try in 15 minutes.")
        return 2
    st = hk.live_status()
    if not (st["tracks"]["skills"]["open"] and st["tracks"]["agents"]["open"]):
        print("The Track 1 and Tracks 2/3 windows must be open; this test doesn't change settings.")
        return 2

    stamp = format(int(time.time()), "x")
    captain, mate = f"kit-captain-{stamp}@cubbie.test", f"kit-mate-{stamp}@cubbie.test"
    team = f"Kit test {stamp} (deleting)"
    users: list = []
    homes = {who: tempfile.mkdtemp(prefix=f"cubbie-kit-{who}-") for who in ("captain", "mate")}
    try:
        cap_id, cap_code = create_user(captain)
        users.append(cap_id)
        mate_id, mate_code = create_user(mate)
        users.append(mate_id)

        # sign in through the script's own verify
        code, out, err = cli(homes["captain"], "verify", "--email", captain, "--code", cap_code)
        check(code == 0 and captain in out, f"verify signs in with the emailed code ({err.strip() or 'ok'})")
        session = Path(homes["captain"]) / "session.json"
        check(set(json.loads(session.read_text())) == {"access_token"}, "only the access token is saved")
        check(stat.S_IMODE(session.stat().st_mode) == 0o600, "the session file is private (600)")
        code, who, _ = cli_json(homes["captain"], "whoami")
        check(code == 0 and who["email"] == captain and who["user_id"] == cap_id, "whoami reports the signed-in user")

        # the database's own rule, passed through as written
        token = json.loads(session.read_text())["access_token"]
        try:
            hk.rpc("submit_entry", {"p_track": "agents", "p_team_name": team, "p_name": "", "p_pitch": "p", "p_platform": "",
                                    "p_link": "", "p_video_url": "", "p_members": [{"name": "C", "email": captain}],
                                    "p_repo_url": "https://github.com/cubbie-kit-test/agents"}, token)
            check(False, "the database refuses Track 2 before Track 1")
        except hk.Problem as exc:
            check(str(exc) == "Tracks 2 and 3 open once your team has submitted Track 1.", f"database message passes through: {exc}")

        track1 = ["submit", "--track", "skills", "--team", team, "--name", "Kit Skill", "--pitch", "Live test of the kit.",
                  "--member", f"Captain <{captain}>", "--member", f"Mate <{mate}>",
                  "--repo", "https://github.com/cubbie-kit-test/kit-skill", "--platform", "tiktok",
                  "--post", "https://www.tiktok.com/@cubbie-kit-test/video/0"]
        code, out, err = cli(homes["captain"], *track1)
        _, rows = admin("GET", f"/rest/v1/submissions?owner_id=eq.{cap_id}&select=id")
        check(code == 0 and "Nothing sent" in out and rows == [], "submit without --yes only previews")

        code, out, err = cli(homes["captain"], *track1, "--yes")
        check(code == 0 and "in the public gallery now" in out and hk.GALLERY_URL in out,
              f"Track 1 submits and the script finds it in the gallery ({err.strip() or 'ok'})")
        _, rows = admin("GET", f"/rest/v1/submissions?owner_id=eq.{cap_id}&track=eq.skills&select=*")
        t1 = rows[0] if rows else {}
        check(t1.get("status") == "published" and t1.get("link") == "https://github.com/cubbie-kit-test/kit-skill"
              and [m["email"] for m in t1.get("members", [])] == [captain, mate], "the saved Track 1 row matches")
        _, board, _ = cli_json(homes["captain"], "gallery", "--track", "skills")
        check(any(r["id"] == t1.get("id") for r in board or []), "get_leaderboard (public) lists the entry")

        code, out, err = cli(homes["captain"], "submit", "--track", "skills", "--pitch", "Edited by the live test.", "--yes")
        _, rows = admin("GET", f"/rest/v1/submissions?id=eq.{t1.get('id')}&select=pitch,link,members,status")
        check(code == 0 and rows and rows[0]["pitch"] == "Edited by the live test." and rows[0]["link"] == t1.get("link")
              and len(rows[0]["members"]) == 2 and rows[0]["status"] == "published",
              f"an edit changes only the given field and stays live ({err.strip() or 'ok'})")

        code, out, err = cli(homes["captain"], "submit", "--track", "agents", "--team", team, "--name", "Kit Agents",
                             "--pitch", "Track 2 from the kit.", "--member", f"Captain <{captain}>",
                             "--repo", "https://github.com/cubbie-kit-test/kit-agents", "--website", "https://example.com/kit", "--yes")
        check(code == 0 and "in the public gallery now" in out, f"Track 2 submits once Track 1 is in ({err.strip() or 'ok'})")
        _, gallery, _ = cli_json(homes["captain"], "gallery", "--track", "agents")
        t2 = next((r for r in gallery or [] if r["team_name"] == team), {})
        check(t2.get("repo_url") == "https://github.com/cubbie-kit-test/kit-agents" and t2.get("link") == "https://example.com/kit",
              "get_gallery('agents') (public) lists it with repo and website")

        code, out, err = cli(homes["captain"], "posts", "--add", "https://www.instagram.com/reel/cubbie-kit-test/", "--yes")
        _, rows = admin("GET", f"/rest/v1/submissions?id=eq.{t1.get('id')}&select=social_urls")
        check(code == 0 and rows and rows[0]["social_urls"] == ["https://www.instagram.com/reel/cubbie-kit-test/"],
              f"posts adds an extra social post ({err.strip() or 'ok'})")

        code, out, err = cli(homes["mate"], "verify", "--email", mate, "--code", mate_code)
        check(code == 0, "the teammate signs in")
        code, mine, _ = cli_json(homes["mate"], "mine")
        check(code == 0 and any(r["id"] == t1.get("id") for r in mine or []), "the teammate sees the team's Track 1 entry")
        code, out, err = cli(homes["mate"], "submit", "--track", "skills", "--pitch", "Mate edit", "--yes")
        check(code == 1 and "whoever submitted it can update it" in err, "a teammate can't edit the captain's entry")

        code, out, err = cli(homes["captain"], "logout")
        code2, _, err2 = cli(homes["captain"], "mine")
        check(code == 0 and not session.exists() and code2 == 1 and "not signed in" in err2, "logout deletes the token")
    finally:
        cleanup(users)
    failed = [w for ok, w in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


def cleanup(users: list) -> None:
    if not users:
        return
    owners = ",".join(users)
    _, rows = admin("GET", f"/rest/v1/submissions?owner_id=in.({owners})&select=id")
    ids = [r["id"] for r in rows or []]
    if ids:
        admin("DELETE", f"/rest/v1/audit_log?entity_id=in.({','.join(ids)})")
        admin("DELETE", f"/rest/v1/submissions?id=in.({','.join(ids)})")
    admin("DELETE", f"/rest/v1/audit_log?actor_id=in.({owners})")
    for uid in users:
        admin("DELETE", f"/auth/v1/admin/users/{uid}")
    _, left_subs = admin("GET", f"/rest/v1/submissions?owner_id=in.({owners})&select=id")
    left_audit = []
    if ids:
        _, left_audit = admin("GET", f"/rest/v1/audit_log?entity_id=in.({','.join(ids)})&select=id")
    _, left_actor = admin("GET", f"/rest/v1/audit_log?actor_id=in.({owners})&select=id")
    left_users = [uid for uid in users if admin("GET", f"/auth/v1/admin/users/{uid}")[0] != 404]
    check(not left_subs and not left_audit and not left_actor and not left_users,
          f"cleanup: deleted {len(ids)} submissions, their audit rows and {len(users)} users "
          f"(left: {len(left_subs or [])} submissions, {len(left_audit or []) + len(left_actor or [])} audit rows, {len(left_users)} users)")


if __name__ == "__main__":
    sys.exit(main())

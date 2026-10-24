#!/usr/bin/env python3
"""The Cubbie Hackathon from the command line: live windows, sign-in, your team's entries, submitting.

    python3 scripts/hackathon.py status                          # what is open right now (live)
    python3 scripts/hackathon.py login --google                  # signs in with Google in your browser
    python3 scripts/hackathon.py login --email you@school.edu    # or: emails you a 6-digit code
    python3 scripts/hackathon.py verify --email you@school.edu --code 123456
    python3 scripts/hackathon.py whoami
    python3 scripts/hackathon.py mine                            # your team's entries
    python3 scripts/hackathon.py submit --track skills ...       # preview; add --yes to send
    python3 scripts/hackathon.py posts --track skills --add URL  # more social posts (preview; --yes)
    python3 scripts/hackathon.py gallery --track skills
    python3 scripts/hackathon.py logout

Standard library only (Python 3.9+). It talks to the hackathon's Supabase project with the
site's publishable key, which is public by design: every rule (windows, team size, required
links, who may edit) is enforced by the database, and its error messages are passed through
as they are. The only thing saved on disk is the sign-in's access token (about an hour), in
~/.config/cubbie-hackathon/session.json with mode 600; `logout` deletes it. Add --json to any
command for machine-readable output.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

SUPABASE_URL = os.environ.get("CUBBIE_HACKATHON_SUPABASE_URL", "https://mputiuoljihmxpqhmpeb.supabase.co").rstrip("/")
# The site's publishable key: meant for browsers and scripts, safe to share.
PUBLISHABLE_KEY = os.environ.get("CUBBIE_HACKATHON_PUBLISHABLE_KEY", "sb_publishable_CeGx6OG3XRoL-H5GqUC-Yg_Olf-HdBu")
SITE_URL = "https://hackathon.cubbie.ai"
GALLERY_URL = f"{SITE_URL}/#gallery"
USER_AGENT = "cubbie-hackathon-kit/0.1"

TRACKS = {
    "skills": "Track 1 · Cubbie Skills",
    "agents": "Track 2 · Agent-to-Agent Coordination",
    "groupchat": "Track 3 · Group Chat Assistant",
}
TRACK_ALIASES = {"1": "skills", "2": "agents", "3": "groupchat", "track1": "skills", "track2": "agents", "track3": "groupchat"}
# Track 1's demo goes on TikTok or Instagram (the site's form offers only these two).
PLATFORMS = {"tiktok": ("TikTok", ("tiktok.com",)), "instagram": ("Instagram", ("instagram.com",))}
MAX_MEMBERS = 4
MAX_EXTRA_POSTS = 5

GITHUB_REPO = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[^\s]*)?$")
HTTPS_LINK = re.compile(r"^https://[^\s]+$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MEMBER = re.compile(r"^\s*(?P<name>.*?)\s*<\s*(?P<email>[^<>\s]+)\s*>\s*$")


class Problem(Exception):
    """Something to tell the student; printed without a traceback."""


# ---------- session (only the access token is stored) ----------

def session_path() -> Path:
    home = os.environ.get("CUBBIE_HACKATHON_HOME")
    if home:
        return Path(home) / "session.json"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "cubbie-hackathon" / "session.json"


def jwt_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return {}


def save_token(token: str) -> Path:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"access_token": token}, f)
    os.chmod(path, 0o600)
    return path


def load_token(required: bool = True) -> Optional[str]:
    path = session_path()
    try:
        token = json.loads(path.read_text()).get("access_token")
    except (OSError, ValueError):
        token = None
    if token and jwt_claims(token).get("exp", 0) > time.time() + 30:
        return token
    if required:
        why = "Your sign-in expired" if token else "You're not signed in"
        raise Problem(f"{why}. Run: login --google, or login --email <your email> and verify with the code.")
    return None


# ---------- HTTP ----------

def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def request(method: str, path: str, body: Any = None, token: Optional[str] = None) -> Any:
    headers = {"apikey": PUBLISHABLE_KEY, "User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{SUPABASE_URL}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise Problem(explain_error(exc.code, exc.read())) from None
    except urllib.error.URLError as exc:
        hint = ""
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            hint = " (macOS python.org Python: run 'Install Certificates.command' from its Applications folder)"
        raise Problem(f"Can't reach the hackathon backend: {exc.reason}{hint}") from None
    return json.loads(raw) if raw.strip() else None


def explain_error(status: int, raw: bytes) -> str:
    try:
        err = json.loads(raw)
    except ValueError:
        err = {}
    if not isinstance(err, dict):
        err = {}
    code = str(err.get("code") or "")
    error_code = str(err.get("error_code") or "")
    message = err.get("message") or err.get("msg") or err.get("error_description") or err.get("error") or raw.decode(errors="replace")[:300]
    if code == "P0001":  # the database's own messages, written for students
        return message
    if error_code == "otp_expired":
        return "That code didn't work. Check it, or ask for a new one with login."
    if error_code in ("flow_state_not_found", "flow_state_expired", "bad_code_verifier"):
        return "The Google sign-in expired or didn't match. Run login --google again."
    if status == 429 or "rate" in error_code:
        return "Too many requests. Wait a minute (one code per email per 60 seconds) and try again."
    if status == 401 or code == "PGRST301" or "JWT" in str(message):
        return "Your sign-in expired. Run login again."
    if code == "PGRST202":
        return "The hackathon backend changed. Update this kit (git pull) and try again."
    return f"{message} (HTTP {status}{', ' + code if code else ''})"


def rpc(name: str, args: Optional[dict] = None, token: Optional[str] = None) -> Any:
    return request("POST", f"/rest/v1/rpc/{name}", args or {}, token)


# ---------- time and windows ----------

def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip().replace(" ", "T").replace("Z", "+00:00")
    text = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], text)
    text = re.sub(r"([+-]\d\d)$", r"\1:00", text)
    return datetime.fromisoformat(text)


def window(open_at: Optional[str], close_at: Optional[str], now: datetime) -> dict:
    opens, closes = parse_time(open_at), parse_time(close_at)
    is_open = bool(opens and opens <= now and (closes is None or now < closes))
    if is_open:
        state = "open"
    elif opens is None or opens > now:
        state = "not open yet"
    else:
        state = "closed"
    return {"open": is_open, "state": state, "opens_at": open_at, "closes_at": close_at}


def read_settings() -> dict:
    rows = request("GET", "/rest/v1/settings?select=skills_open_at,skills_close_at,general_open_at,general_close_at,"
                          "voting_open_at,voting_close_at,votes_per_voter,show_vote_counts")
    if not rows:
        raise Problem("The hackathon settings are empty; ask the organizers.")
    return rows[0]


def live_status(now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    s = read_settings()
    general = window(s["general_open_at"], s["general_close_at"], now)
    return {
        "now": now.isoformat(),
        "tracks": {
            "skills": window(s["skills_open_at"], s["skills_close_at"], now),
            "agents": general,
            "groupchat": general,
        },
        "voting": window(s["voting_open_at"], s["voting_close_at"], now),
        "votes_per_voter": s.get("votes_per_voter"),
        "gallery": GALLERY_URL,
    }


def when(value: Optional[str]) -> str:
    dt = parse_time(value)
    if not dt:
        return "not set"
    local = dt.astimezone()
    return f"{local:%a %b %d, %H:%M} {local.tzname() or ''} ({dt.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC)".replace(" ,", ",")


def describe_window(w: dict) -> str:
    if w["state"] == "open":
        end = f"closes {when(w['closes_at'])}" if w["closes_at"] else "no closing time set yet"
        return f"OPEN since {when(w['opens_at'])}; {end}"
    if w["state"] == "not open yet":
        return f"not open yet; opens {when(w['opens_at'])}" if w["opens_at"] else "not open yet (no opening time set)"
    return f"CLOSED since {when(w['closes_at'])}"


# ---------- entries ----------

def track_id(value: str) -> str:
    key = value.strip().lower().replace(" ", "")
    key = TRACK_ALIASES.get(key, key)
    if key not in TRACKS:
        raise Problem(f"Unknown track {value!r}: use skills (1), agents (2) or groupchat (3).")
    return key


def parse_member(text: str) -> dict:
    m = MEMBER.match(text)
    if not m:
        raise Problem(f"Write each member as \"Name <email>\", not {text!r}.")
    return {"name": m.group("name"), "email": m.group("email")}


def normalize_github(url: str) -> str:
    return re.sub(r"^https://www\.github\.com/", "https://github.com/", url.strip())


def host_matches(url: str, hosts: tuple) -> bool:
    m = re.match(r"^https?://([^/?#:]+)", url.strip(), re.I)
    host = m.group(1).lower() if m else ""
    return any(host == h or host.endswith("." + h) for h in hosts)


def entry_from_row(row: dict) -> dict:
    """A saved submission row in this script's field names."""
    skills = row.get("track") == "skills"
    return {
        "team": row.get("team_name") or "",
        "name": row.get("name") or "",
        "pitch": row.get("pitch") or "",
        "members": [{"name": m.get("name", ""), "email": m.get("email", "")} for m in row.get("members") or []],
        "repo": (row.get("link") if skills else row.get("repo_url")) or "",
        "platform": row.get("platform") or "",
        "post": (row.get("video_url") if skills else "") or "",
        "website": ("" if skills else row.get("link")) or "",
        "video": ("" if skills else row.get("video_url")) or "",
    }


def check_entry(track: str, e: dict) -> list:
    """The database's rules (and the site form's platform check), so problems show before sending."""
    problems = []
    if not e["team"].strip():
        problems.append("Add the team name.")
    elif len(e["team"].strip()) > 60:
        problems.append("Keep the team name within 60 characters.")
    if len((e.get("name") or "").strip()) > 60:
        problems.append("Keep the project name within 60 characters.")
    if not e["pitch"].strip():
        problems.append("Add the one-liner.")
    elif len(e["pitch"].strip()) > 140:
        problems.append(f"Keep the one-liner within 140 characters (now {len(e['pitch'].strip())}).")
    members = e["members"]
    if not 1 <= len(members) <= MAX_MEMBERS:
        problems.append(f"List 1 to {MAX_MEMBERS} team members (now {len(members)}).")
    for m in members:
        if not 1 <= len(m["name"].strip()) <= 60 or not EMAIL.match(m["email"].strip()):
            problems.append(f"Each team member needs a name and an email: {m['name']!r} <{m['email']}>.")
    emails = [m["email"].strip().lower() for m in members]
    if len(set(emails)) < len(emails):
        problems.append("Each team member needs their own email.")
    links = [("repo", e["repo"]), ("post", e["post"]), ("website", e["website"]), ("video", e["video"])]
    for label, url in links:
        if url and not url.startswith("https://"):
            problems.append(f"Links must start with https:// ({label}: {url}).")
    if track == "skills":
        if not e["repo"]:
            problems.append("Track 1 needs the Skill's GitHub repo (--repo).")
        elif not GITHUB_REPO.match(e["repo"]):
            problems.append("The Skill link needs to be a GitHub repo, like https://github.com/your-team/your-skill")
        if e["platform"] or e["post"]:  # the social post is optional, but a post needs its platform
            if e["platform"] not in PLATFORMS:
                problems.append("A social post needs its platform: --platform tiktok or --platform instagram.")
            elif not e["post"]:
                problems.append("Add the post link (--post), or leave out --platform: the post is optional.")
            elif not host_matches(e["post"], PLATFORMS[e["platform"]][1]):
                problems.append(f"That doesn't look like a {PLATFORMS[e['platform']][0]} link: {e['post']}")
        if e["website"] or e["video"]:
            problems.append("Track 1 has no website or video field: the demo goes in --post, the Skill in --repo.")
    else:
        if not e["repo"]:
            problems.append("Tracks 2 and 3 need the project's GitHub repo (--repo).")
        elif not GITHUB_REPO.match(e["repo"]):
            problems.append("The GitHub link needs to be a repo, like https://github.com/your-team/your-project")
        if e["website"] and not HTTPS_LINK.match(e["website"]):
            problems.append("The project website needs to be one link, like https://your-project.com")
        if e["platform"] or e["post"]:
            problems.append("Tracks 2 and 3 have no social post field: use --video for an optional demo video.")
    return problems


def rpc_args(track: str, e: dict) -> dict:
    skills = track == "skills"
    return {
        "p_track": track,
        "p_team_name": e["team"].strip(),
        "p_name": (e.get("name") or "").strip(),
        "p_pitch": e["pitch"].strip(),
        "p_platform": e["platform"] if skills else "",
        "p_link": e["repo"] if skills else e["website"],
        "p_video_url": e["post"] if skills else e["video"],
        "p_members": [{"name": m["name"].strip(), "email": m["email"].strip().lower()} for m in e["members"]],
        "p_repo_url": "" if skills else e["repo"],
    }


def find_in_gallery(track: str, entry_id: str) -> Optional[dict]:
    rows = rpc("get_leaderboard") if track == "skills" else rpc("get_gallery", {"p_track": track})
    return next((r for r in rows or [] if r.get("id") == entry_id), None)


# ---------- output ----------

def out(args, data: Any, text: str) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else text)


def entry_text(track: str, e: dict) -> str:
    lines = [f"  {TRACKS[track]}",
             f"  Team:      {e['team']}",
             f"  Project:   {e.get('name') or e['team'] + ' (the team name)'}",
             f"  One-liner: {e['pitch']}"]
    lines += [f"  Member:    {m['name']} <{m['email'].lower()}>" for m in e["members"]]
    if track == "skills":
        post = (f"{e['post']} ({PLATFORMS.get(e['platform'], (e['platform'] or '?',))[0]})" if e["post"] else "(none)")
        lines += [f"  Skill repo: {e['repo']}",
                  f"  Social post: {post}"]
    else:
        lines += [f"  GitHub repo: {e['repo']}",
                  f"  Website:     {e['website'] or '(none)'}",
                  f"  Demo video:  {e['video'] or '(none)'}"]
    return "\n".join(lines)


# ---------- commands ----------

def cmd_status(args) -> None:
    st = live_status()
    t = st["tracks"]
    cap = st["votes_per_voter"]
    text = "\n".join([
        "Cubbie Hackathon, live from the organizers' settings:",
        f"  Track 1 (Cubbie Skills):  {describe_window(t['skills'])}",
        f"  Tracks 2 and 3:           {describe_window(t['agents'])}",
        f"  Voting on Track 1:        {describe_window(st['voting'])}"
        + (f"; up to {cap} votes per person" if cap else "; one vote per project, no overall cap"),
        "  Entries can be edited freely while their track is open; closing the window locks them.",
        f"  Gallery: {GALLERY_URL}",
    ])
    out(args, st, text)


def cmd_login(args) -> None:
    if args.google:
        return login_google(args)
    email = args.email.strip().lower()
    if not EMAIL.match(email):
        raise Problem(f"{args.email!r} doesn't look like an email address.")
    request("POST", "/auth/v1/otp", {"email": email, "create_user": True})
    text = (f"Sent a 6-digit code to {email} (from hello@hackathon.cubbie.ai; check spam). It works for 10 minutes.\n"
            f"Next: verify --email {email} --code <the code>")
    if sys.stdin.isatty() and not args.json:  # someone at a terminal: ask right away
        print(text.splitlines()[0])
        return finish_verify(args, email, input("Code: ").strip())
    out(args, {"sent": True, "email": email}, text)


def finish_verify(args, email: str, code: str) -> None:
    if not re.fullmatch(r"\d{6}", code):
        raise Problem("The code is the 6 digits from the email.")
    try:
        session = request("POST", "/auth/v1/verify", {"type": "email", "email": email, "token": code})
    except Problem as exc:
        if "expired" in str(exc).lower() or "invalid" in str(exc).lower():
            raise Problem("That code didn't work. Check it, or ask for a new one with login.") from None
        raise
    finish_session(args, session)


def finish_session(args, session: Optional[dict]) -> None:
    """Keep only the access token of a new Supabase session and say who is signed in."""
    token = (session or {}).get("access_token")
    if not token:
        raise Problem("Sign-in didn't return a session; run login again.")
    path = save_token(token)
    claims = jwt_claims(token)
    methods = sign_in_methods(token)
    out(args, {"signed_in": True, "email": claims.get("email"), "user_id": claims.get("sub"), "sign_in_methods": methods,
               "expires_at": claims.get("exp"), "saved_to": str(path)},
        f"Signed in as {claims.get('email')} (account {str(claims.get('sub'))[:8]}; signs in with {', '.join(methods) or 'unknown'}).\n"
        f"The sign-in lasts about an hour; only its token is saved ({path}).")


def sign_in_methods(token: str) -> list:
    """How this account can sign in: its linked providers (Google) from Supabase's current view of the user, plus
    an email code, which always reaches the account that owns the address."""
    try:
        user = request("GET", "/auth/v1/user", token=token) or {}
    except Problem:
        user = {}
    providers = (user.get("app_metadata") or jwt_claims(token).get("app_metadata") or {}).get("providers") or []
    methods = [p.capitalize() for p in providers if p != "email"]
    return methods + ["email code"] if (user.get("email") or jwt_claims(token).get("email")) else methods


def pkce_pair() -> tuple:
    """A PKCE verifier and its S256 challenge (RFC 7636)."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


CALLBACK_PAGE = """<!doctype html><meta charset="utf-8"><title>Cubbie Hackathon</title>
<body style="font-family:system-ui,sans-serif;max-width:32rem;margin:4rem auto;padding:0 1rem;text-align:center">
<h1>{title}</h1><p>{body}</p></body>"""


def wait_for_callback(server: HTTPServer, deadline: float) -> dict:
    """Serve the loopback page Supabase sends the browser back to, until it brings a code or an error."""
    result: dict = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server's naming)
            url = urllib.parse.urlparse(self.path)
            if url.path != "/callback":
                self.send_error(404)
                return
            result.update({k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()})
            ok = "code" in result
            body = "You can close this tab and go back to your terminal or agent." if ok else \
                html.escape(result.get("error_description") or result.get("error") or "No sign-in came back.")
            page = CALLBACK_PAGE.format(title="You're signed in" if ok else "Sign-in didn't finish", body=body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, *args):  # keep the terminal quiet
            pass

    server.RequestHandlerClass = Callback
    while not result and time.time() < deadline:
        server.timeout = max(0.1, min(1.0, deadline - time.time()))
        server.handle_request()
    return result


def login_google(args) -> None:
    """Google through Supabase with PKCE; the browser comes back to a one-off page on 127.0.0.1.

    Supabase accepts loopback redirects on any port (RFC 8252), so nothing has to be registered.
    The code is useless without the verifier, which never leaves this process.
    """
    verifier, challenge = pkce_pair()
    server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    try:
        redirect = f"http://127.0.0.1:{server.server_address[1]}/callback"
        url = f"{SUPABASE_URL}/auth/v1/authorize?" + urllib.parse.urlencode({
            "provider": "google", "redirect_to": redirect, "code_challenge": challenge,
            "code_challenge_method": "s256", "prompt": "select_account"})
        print(f"Opening Google sign-in in your browser (waiting up to {args.timeout // 60} minutes).\n"
              f"If it doesn't open, paste this link into the browser on this computer:\n{url}",
              file=sys.stderr if args.json else sys.stdout, flush=True)
        webbrowser.open(url)
        got = wait_for_callback(server, time.time() + args.timeout)
    finally:
        server.server_close()
    if not got:
        raise Problem(f"No Google sign-in came back within {args.timeout // 60} minutes. Run login --google again.")
    if "code" not in got:
        raise Problem("Google sign-in didn't finish: " + (got.get("error_description") or got.get("error") or "unknown error"))
    finish_session(args, request("POST", "/auth/v1/token?grant_type=pkce", {"auth_code": got["code"], "code_verifier": verifier}))


def cmd_verify(args) -> None:
    finish_verify(args, args.email.strip().lower(), args.code.strip())


def cmd_whoami(args) -> None:
    token = load_token(required=False)
    if not token:
        return out(args, {"signed_in": False}, "Not signed in. Run: login --google, or login --email <your email>")
    c = jwt_claims(token)
    expires = datetime.fromtimestamp(c["exp"], timezone.utc)
    school = rpc("is_school_email", {"addr": c.get("email", "")})
    methods = sign_in_methods(token)
    out(args, {"signed_in": True, "email": c.get("email"), "user_id": c.get("sub"), "sign_in_methods": methods,
               "expires_at": expires.isoformat(), "can_vote": bool(school)},
        f"Signed in as {c.get('email')} (account {str(c.get('sub'))[:8]}) until {when(expires.isoformat())}.\n"
        f"This account signs in with: {', '.join(methods) or 'unknown'}."
        + ("" if school else "\nVoting needs a school email; this address can submit but not vote."))


def my_rows(token: str) -> list:
    return rpc("my_submissions", token=token) or []


def cmd_mine(args) -> None:
    token = load_token()
    me = jwt_claims(token).get("sub")
    rows = my_rows(token)
    if not rows:
        return out(args, [], "Your team has no entries yet (none submitted by you or listing your email).")
    blocks = []
    for r in rows:
        e = entry_from_row(r)
        who = "you submitted it and can edit it" if r.get("owner_id") == me else \
            "a teammate submitted it; only they can edit it"
        block = [f"[{r['status']}] {entry_text(r['track'], e).lstrip()}", f"  ({who}; id {r['id']})"]
        if r.get("social_urls"):
            block.append("  More posts: " + ", ".join(r["social_urls"]))
        if r.get("review_note"):
            block.append(f"  Note from the organizers: {r['review_note']}")
        blocks.append("\n".join(block))
    out(args, rows, "\n\n".join(blocks))


def gather_entry(args, track: str, existing: Optional[dict]) -> dict:
    e = entry_from_row(existing) if existing else {k: "" for k in ("team", "name", "pitch", "repo", "platform", "post", "website", "video")}
    if not existing:
        e["members"] = []
    if args.file:
        try:
            data = json.loads(Path(args.file).read_text())
        except (OSError, ValueError) as exc:
            raise Problem(f"Can't read {args.file}: {exc}") from None
        for key in ("team", "name", "pitch", "repo", "platform", "post", "website", "video"):
            if key in data:
                e[key] = str(data[key] or "")
        if "members" in data:
            e["members"] = [m if isinstance(m, dict) else parse_member(str(m)) for m in data["members"]]
    for key in ("team", "name", "pitch", "repo", "platform", "post", "website", "video"):
        value = getattr(args, key)
        if value is not None:
            e[key] = value.strip()
    if args.member:
        e["members"] = [parse_member(m) for m in args.member]
    e["platform"] = e["platform"].lower()
    e["repo"] = normalize_github(e["repo"]) if e["repo"] else ""
    e["members"] = [{"name": str(m.get("name", "")).strip(), "email": str(m.get("email", "")).strip()} for m in e["members"]]
    return e


def cmd_submit(args) -> None:
    track = track_id(args.track)
    token = load_token()
    claims = jwt_claims(token)
    rows = my_rows(token)
    mine = next((r for r in rows if r["track"] == track and r.get("owner_id") == claims.get("sub")), None)
    teams = next((r for r in rows if r["track"] == track and r.get("owner_id") != claims.get("sub")), None)
    if teams and not mine:
        raise Problem(f"You're on {teams['team_name']}'s entry for this track; whoever submitted it can update it "
                      "(sign in as them), or ask them to remove you first.")
    if mine and mine.get("status") == "rejected":
        raise Problem("The organizers took this one down; ask them if something needs to change.")
    st = live_status()
    if not st["tracks"][track]["open"] and not (mine and mine.get("status") == "changes_requested"):
        raise Problem(f"Submissions for this track are not open: {describe_window(st['tracks'][track])}.")
    if track != "skills" and not any(r["track"] == "skills" and r["status"] in ("submitted", "changes_requested", "verified", "published")
                                     for r in rows):
        raise Problem("Tracks 2 and 3 open once your team has submitted Track 1.")

    e = gather_entry(args, track, mine)
    problems = check_entry(track, e)
    if problems:
        raise Problem("Not sent yet. Fix these first:\n- " + "\n- ".join(problems))
    payload = rpc_args(track, e)
    notes = []
    if claims.get("email") and claims["email"].lower() not in [m["email"].lower() for m in e["members"]]:
        notes.append(f"Note: you ({claims['email']}) aren't listed as a member.")
    if not mine:
        notes.append(f"Note: this starts a new entry owned by the account of {claims.get('email')}. If your team already "
                     "sent one for this track (on the website or with another address), sign in with that account "
                     "instead, so you update it rather than adding a second one.")
    action = "Update" if mine else "New entry"
    preview = f"{action}, goes live in the public gallery as soon as it is sent:\n{entry_text(track, e)}"
    if notes:
        preview += "\n" + "\n".join(notes)
    if not args.yes:
        return out(args, {"sent": False, "preview": payload, "update": bool(mine)},
                   preview + "\n\nNothing sent. Check it with the team, then run the same command with --yes.")

    row = rpc("submit_entry", payload, token)
    shown = find_in_gallery(track, row["id"])
    status_line = ("It's in the public gallery now." if shown else
                   f"Saved with status {row['status']}; it isn't in the public gallery right now.")
    out(args, {"sent": True, "entry": row, "in_gallery": bool(shown), "gallery": GALLERY_URL},
        f"{'Updated' if mine else 'Submitted'}: {row['name']} by {row['team_name']} ({TRACKS[track]}). {status_line}\n"
        f"Gallery: {GALLERY_URL}\n"
        "You can keep editing while the track is open: run submit again with only the fields that change.")


def cmd_posts(args) -> None:
    track = track_id(args.track)
    token = load_token()
    me = jwt_claims(token).get("sub")
    row = next((r for r in my_rows(token) if r["track"] == track and r.get("owner_id") == me), None)
    if not row:
        raise Problem("Submit to this track first (only whoever submitted the entry can add posts).")
    posts = list(row.get("social_urls") or [])
    if args.clear:
        posts = []
    for url in args.remove or []:
        posts = [p for p in posts if p != url.strip()]
    for url in args.add or []:
        url = url.strip()
        if not HTTPS_LINK.match(url):
            raise Problem(f"Links must start with https:// ({url}).")
        if url not in posts and url != row.get("video_url"):
            posts.append(url)
    if len(posts) > MAX_EXTRA_POSTS:
        raise Problem(f"Up to {MAX_EXTRA_POSTS} more posts besides the main one (now {len(posts)}).")
    listing = "\n".join(f"  {p}" for p in posts) or "  (none)"
    if not args.yes:
        return out(args, {"sent": False, "social_urls": posts},
                   f"Main post: {row.get('video_url')}\nMore posts after this change:\n{listing}\n\n"
                   "Nothing sent. Run the same command with --yes to save.")
    saved = rpc("update_launch_links", {"p_track": track, "p_video_url": None, "p_social_urls": posts}, token)
    out(args, {"sent": True, "entry": saved},
        f"Saved. Main post: {saved.get('video_url')}\nMore posts:\n" + ("\n".join(f"  {p}" for p in saved.get("social_urls") or []) or "  (none)"))


def cmd_gallery(args) -> None:
    track = track_id(args.track)
    rows = rpc("get_leaderboard") if track == "skills" else rpc("get_gallery", {"p_track": track})
    rows = rows or []
    if not rows:
        return out(args, rows, f"No projects in the {TRACKS[track]} gallery yet. {GALLERY_URL}")
    lines = [f"{TRACKS[track]} ({len(rows)}), {GALLERY_URL}"]
    for i, r in enumerate(rows, 1):
        votes = f" · {r['votes']} votes" if track == "skills" and r.get("votes") is not None else ""
        lines.append(f"{i:>3}. {r.get('emoji', '')} {r['name']} by {r['team_name']}{votes}: {r['pitch']}".replace("  ", " "))
        link = r.get("link") if track == "skills" else (r.get("link") or r.get("video_url") or r.get("repo_url"))
        if link:
            lines.append(f"     {link}")
    out(args, rows, "\n".join(lines))


def cmd_logout(args) -> None:
    path = session_path()
    token = load_token(required=False)
    if token:
        try:
            request("POST", "/auth/v1/logout?scope=local", {}, token)  # this sign-in only, not the website's
        except Problem:
            pass  # the local token goes either way
    existed = path.exists()
    if existed:
        path.unlink()
    out(args, {"signed_out": True, "removed": str(path) if existed else None},
        f"Signed out{'; removed ' + str(path) if existed else ''}.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hackathon.py", description="The Cubbie Hackathon from the command line.")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="which tracks and voting are open right now (live)").set_defaults(fn=cmd_status)

    s = sub.add_parser("login", help="sign in with Google in the browser, or get a 6-digit code by email")
    how = s.add_mutually_exclusive_group(required=True)
    how.add_argument("--google", action="store_true", help="sign in with Google in your browser")
    how.add_argument("--email", help="email a 6-digit code to this address")
    s.add_argument("--timeout", type=int, default=300, help="seconds to wait for the Google sign-in (default 300)")
    s.set_defaults(fn=cmd_login)

    s = sub.add_parser("verify", help="finish signing in with the emailed code")
    s.add_argument("--email", required=True)
    s.add_argument("--code", required=True)
    s.set_defaults(fn=cmd_verify)

    sub.add_parser("whoami", help="who is signed in").set_defaults(fn=cmd_whoami)
    sub.add_parser("mine", help="your team's entries").set_defaults(fn=cmd_mine)

    s = sub.add_parser("submit", help="submit or update your team's entry (preview unless --yes)")
    s.add_argument("--track", required=True, help="skills (1), agents (2) or groupchat (3)")
    s.add_argument("--file", help="JSON with any of: team, name, pitch, members, repo, platform, post, website, video")
    s.add_argument("--team", help="team name")
    s.add_argument("--name", help="project name (defaults to the team name)")
    s.add_argument("--pitch", help="one-liner, up to 140 characters")
    s.add_argument("--member", action="append", help='"Name <email>", repeat for each member (1-4); replaces the list')
    s.add_argument("--repo", help="GitHub repo: the Skill (Track 1) or the project (Tracks 2 and 3)")
    s.add_argument("--platform", help="Track 1: tiktok or instagram")
    s.add_argument("--post", help="Track 1: the public social post with the demo video")
    s.add_argument("--website", help="Tracks 2 and 3: project website (optional)")
    s.add_argument("--video", help="Tracks 2 and 3: demo video link (optional)")
    s.add_argument("--yes", action="store_true", help="send it (without this, only a preview)")
    s.set_defaults(fn=cmd_submit)

    s = sub.add_parser("posts", help="Track 1: more social posts with your demo (up to 5; until voting closes)")
    s.add_argument("--track", default="skills")
    s.add_argument("--add", action="append", help="a post link to add")
    s.add_argument("--remove", action="append", help="a post link to remove")
    s.add_argument("--clear", action="store_true", help="remove all extra posts")
    s.add_argument("--yes", action="store_true", help="save it (without this, only a preview)")
    s.set_defaults(fn=cmd_posts)

    s = sub.add_parser("gallery", help="the public gallery of a track")
    s.add_argument("--track", default="skills")
    s.set_defaults(fn=cmd_gallery)

    sub.add_parser("logout", help="sign out and delete the saved token").set_defaults(fn=cmd_logout)
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except Problem as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

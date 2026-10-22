---
name: cubbie-hackathon
description: Guide a team through the Cubbie Hackathon (hackathon.cubbie.ai), from the rules and live deadlines to finding an idea, building and testing a Track 1 Cubbie Skill, planning Track 2 or 3, and submitting or editing the team's entry from the terminal. Use when someone mentions the Cubbie hackathon, its tracks, deadlines, judging, prizes or gallery, wants a Skill idea for Cubbie, or wants to submit or update their hackathon project.
---

# Cubbie Hackathon

Cubbie lives in students' iMessage and handles everyday college life. The hackathon asks teams to "teach Cubbie a
new trick". This skill explains the event, walks a team through each track, and submits or edits their entry
without the website. Site: https://hackathon.cubbie.ai. Questions for the organizers: https://discord.gg/7eJADTbQMT.

## Rules for you

- **Facts** come only from `references/rules.md`, `references/ideas.md`, `../cubbie-skill-creator/references/` and,
  for anything about time, from the live `status` command.
  Never state a date, deadline, prize, score weight or judging criterion that isn't there. Where the event says
  something is still being finalized (Track 1's exact cutoff, Tracks 2 and 3 criteria), say so.
- **Time**: run `status` before you say what is open, closed or due. It prints each window in the user's local
  time and UTC. A window with no close time has no deadline set yet; don't guess one.
- **Publishing**: an entry is public the moment it is sent (team name, project name, one-liner and links; member
  emails stay private). Before `submit --yes` or `posts --yes`, show the preview to the user and get a clear yes.
- **Sign-in**: offer Google first. `login --google` opens Google in the browser on this computer and waits (up to
  5 minutes) until the user picks their account, so give the command a long timeout or run it in the background.
  Google's screen names `mputiuoljihmxpqhmpeb.supabase.co`, the hackathon's sign-in service; that is expected. The
  other way is `login --email`: a 6-digit code from hello@hackathon.cubbie.ai, which the user tells you or enters
  with `verify`. If your sandbox can't open a browser or a local port, have the user run the login in their own
  terminal. Never ask for passwords. The script saves only the access token (about an hour); `logout` ends only
  this sign-in, not the website's.
- **Identity**: one email address is one account, whether the user signs in with Google or an email code, here or
  on the website. A different address is a different account, even for the same person (a school alias, a personal
  Gmail, Gmail with or without dots, a `+tag`), and it can't edit entries the other account sent. Before
  submitting, run `whoami` and check the address is the one the team used on the website.
- **Script**: run `python3 scripts/hackathon.py <command>` from this skill's folder (Python 3.9+, standard
  library only). Add `--json` when you want to parse the output. Database errors are written for students: relay
  them as they are.

## 1. Start here: where is the team?

Most participants won't read a guide; you are the guide. On first use:

1. Run `python3 scripts/hackathon.py status`.
2. Reply in a few short lines: what the hackathon is (teach Cubbie, the AI in students' iMessage, a new trick),
   the three tracks in one line each, what is open right now from `status`, and that you can take them from idea
   to submission, including submitting for them.
3. Ask where the team is, and offer these as choices:
   - Looking for an idea → section 2, step 1
   - Have an idea, not built yet → section 2, step 1 (sharpen and check it), then step 3
   - Built, testing on Cubbie → section 2, step 4
   - Ready to submit or update → section 4
   - Track 2 or 3 → section 3
   - Just a question (rules, prizes, deadlines) → `references/rules.md`
4. Ask for the team (1 to 4 people, a name and email each) when it's needed, at the latest before submitting. If
   they've signed in, `mine` shows what the team already has.

Keep a short Track 1 checklist in the conversation and show it when a step finishes, so the team always sees what
is left:

```text
Track 1  [x] idea  [x] Skill written  [ ] passes checks  [ ] works on our Cubbie  [ ] demo posted  [ ] submitted
```

Go one step at a time, skip what's done, and keep each message short. Explain a rule when it matters for their
next step, not up front.

## 2. Track 1: a Cubbie Skill

Track 1's judges look mainly at public votes on the site and the demo video's social engagement; Tracks 2 and 3
are judged privately. Track 1 also unlocks Tracks 2 and 3.

1. **Find the moment.** Read `references/ideas.md` and start from one moment of a student's week. With no idea
   yet, show three or four of its notification prompts and ask which one they lived this week; with an idea,
   sharpen it into one situation a student would text about. Then run its "Is it doable on Cubbie?" check, using
   `../cubbie-skill-creator/references/cubbie-capabilities.md` (what Cubbie can do) and `cubbie-auth.md` next to
   it (how sign-in works); `ideas.md` links the same files on GitHub in case that folder isn't there. Reshape the
   idea before anything is built if a check fails.
2. **See a Skill work first** (five minutes, recommended for first-timers): have them text Cubbie the link of one
   of the kit's examples, such as
   https://github.com/imaginix-inc/cubbie-hackathon-kit/tree/main/examples/canvas-deadline-nudge, reply "yes" and
   try it. The examples' README explains the three shapes (instructions only, a script with a key, a CLI with a
   sign-in). Cubbie itself: https://cubbie.ai. If the team can't get Cubbie running, they ask the organizers on
   Discord; don't guess how access works.
3. **Build it with `cubbie-skill-creator`** (in this kit; in Codex, `$cubbie-skill-creator`). Hand over: the
   moment, the abilities and sign-in you settled on, that it's a Track 1 entry for the Cubbie Hackathon, and that
   it has to end in a public GitHub repo. It interviews them, writes the Skill, checks it against Cubbie's install
   rules, helps publish it, and prints two links (a branch link and a link pinned to the commit) plus a checklist
   for testing on their own Cubbie. If that skill isn't installed, point them to the kit's README.
4. **Test on Cubbie.** They text the branch link to Cubbie and go through the checklist. After each fix: push,
   text the branch link again (that installs the newest push), repeat. Track 1 is done when Cubbie installs the
   Skill from its link and the main flow works on a real account.
5. **Demo video.** A short public video showing the student moment and Cubbie handling it, posted on TikTok or
   Instagram (the only platforms the form accepts). Offer a shot list: the moment in the first seconds, the real
   iMessage exchange, the result. Length, hashtags or tags haven't been announced; don't make them up.
6. **Submit** (section 4): the pinned link, platform, post link, team, one-liner. The pinned link always installs
   exactly what they tested, for voters too. They can submit as soon as they have a repo and a post, then keep
   editing while the window is open.
7. **Reach.** Votes need a school email and happen on the site; social views, likes, comments and shares are read
   automatically. More posts with the demo (up to 5 besides the main one) can be added with `posts` until voting
   closes.

When the Skill changes after submitting, push, get the new pinned link from `cubbie-skill-creator` (its
`github_link.py` script), and update the entry with `submit --track skills --repo <new link>`.

## 3. Tracks 2 and 3

Only after the team's Track 1 entry is in (the database refuses otherwise). Both share one window, and a team can
enter either or both.

- **Track 2, Agent-to-Agent Coordination**: personal agents for different students that exchange what matters and
  reach a shared outcome (a study session, a split trip, plans around classes and events).
- **Track 3, Group Chat Assistant**: an AI a group would invite into its chat, more useful, playful or surprising,
  tied to campus life.

They don't have to use Cubbie; any messaging app and any open-source framework work. Help them pick a real campus
scenario, scope a working prototype, and plan how to show it: for multi-agent work, how agents handle conflicting
constraints, what they share, and when they ask their students to confirm; and why students would say "We need
this". Judging is private; full criteria are announced before kickoff. They submit a GitHub repo (public, so the
gallery can show its preview card), and optionally a website and a demo video.

## 4. Submit or update the entry

```bash
python3 scripts/hackathon.py login --google                                 # Google in the browser
python3 scripts/hackathon.py login --email you@school.edu                   # or: emails a 6-digit code
python3 scripts/hackathon.py verify --email you@school.edu --code 123456    # finishes the email sign-in
python3 scripts/hackathon.py whoami                                         # which address and account
python3 scripts/hackathon.py mine                                           # the team's entries, if any

# Track 1 (preview first; the same command with --yes sends it)
python3 scripts/hackathon.py submit --track skills --team "Night Owls" --name "Dorm Chef" \
  --pitch "It's 1 AM and nothing is open." \
  --member "Ana Ruiz <ana@school.edu>" --member "Ben Wu <ben@school.edu>" \
  --repo https://github.com/night-owls/dorm-chef/tree/<commit>/dorm-chef \
  --platform tiktok --post https://www.tiktok.com/@nightowls/video/123

# Track 2 or 3
python3 scripts/hackathon.py submit --track agents --team "Night Owls" --pitch "..." \
  --member "Ana Ruiz <ana@school.edu>" --repo https://github.com/night-owls/study-sync \
  --website https://study-sync.example.com --video https://youtu.be/...

python3 scripts/hackathon.py posts --track skills --add https://www.instagram.com/reel/...   # Track 1 extra posts
python3 scripts/hackathon.py gallery --track skills
python3 scripts/hackathon.py logout
```

- Sign in as the person who should own the entry, ideally with their school email. Only the owner can edit it;
  teammates listed on it see it in `mine`.
- On an update, pass only what changes; everything else is kept from the saved entry. `--member` replaces the
  whole list, so repeat every member. `--file entry.json` takes the same fields as JSON (`team`, `name`, `pitch`,
  `members` as `[{"name", "email"}]`, `repo`, `platform`, `post`, `website`, `video`).
- The flow: `status` → `login` → `whoami` → `mine` → `submit` (preview) → show the user → `submit ... --yes`.
  When the preview says it starts a new entry but the team already has one, stop: they are signed in with another
  address. After sending, the script checks the public gallery and prints its link; share it with the team.

## When something goes wrong

| Message | What to do |
| --- | --- |
| Not signed in / sign-in expired | `login` again; email codes last 10 minutes, one per email per 60 seconds |
| That code didn't work | Check the 6 digits or ask for a new code |
| No Google sign-in came back / The Google sign-in expired | The browser step wasn't finished in time; run `login --google` again, or use `login --email` |
| `mine` is empty but the team already submitted | Signed in with another address; `logout`, then sign in with the address the team used |
| Submissions for this track are not open | Show `status`; the window is closed or not open yet |
| Tracks 2 and 3 open once your team has submitted Track 1 | Submit Track 1 first, from any teammate's account |
| You're already on X's entry for this track | The owner edits it; sign in as them |
| The organizers took this one down | Contact the organizers on Discord |
| The hackathon backend changed | Update this kit (`git pull` in its folder, or reinstall) |

Anything else from the database is a rule message for students: relay it, fix the field, preview again.

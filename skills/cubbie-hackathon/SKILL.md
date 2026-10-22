---
name: cubbie-hackathon
description: Guide a team through the Cubbie Hackathon (hackathon.cubbie.ai), from the rules and live deadlines to building a Track 1 Cubbie Skill, planning Track 2 or 3, and submitting or editing the team's entry from the terminal. Use when someone mentions the Cubbie hackathon, its tracks, deadlines, judging, prizes or gallery, or wants to submit or update their hackathon project.
---

# Cubbie Hackathon

Cubbie lives in students' iMessage and handles everyday college life. The hackathon asks teams to "teach Cubbie a
new trick". This skill explains the event, walks a team through each track, and submits or edits their entry
without the website. Site: https://hackathon.cubbie.ai. Questions for the organizers: https://discord.gg/7eJADTbQMT.

## Rules for you

- **Facts** come only from `references/rules.md` and, for anything about time, from the live `status` command.
  Never state a date, deadline, prize, score weight or judging criterion that isn't there. Where the event says
  something is still being finalized (Track 1's exact cutoff, Tracks 2 and 3 criteria), say so.
- **Time**: run `status` before you say what is open, closed or due. It prints each window in the user's local
  time and UTC. A window with no close time has no deadline set yet; don't guess one.
- **Publishing**: an entry is public the moment it is sent (team name, project name, one-liner and links; member
  emails stay private). Before `submit --yes` or `posts --yes`, show the preview to the user and get a clear yes.
- **Sign-in**: the user gives their email, gets a 6-digit code from hello@hackathon.cubbie.ai, and either tells it
  to you or runs `verify` themselves. Never ask for passwords. The script saves only the session's access token
  (about an hour) and `logout` deletes it.
- **Script**: run `python3 scripts/hackathon.py <command>` from this skill's folder (Python 3.9+, standard
  library only). Add `--json` when you want to parse the output. Database errors are written for students: relay
  them as they are.

## 1. Get oriented

1. `python3 scripts/hackathon.py status` and summarize what is open.
2. Ask who is on the team (1 to 4 people, name and email each), which tracks they want, and what they have so
   far. If they already signed in, `mine` shows the team's entries.
3. Explain the shape in a few lines: Track 1 (a Cubbie Skill) is for every team and unlocks Tracks 2 and 3;
   Track 1's judges look mainly at public votes on the site and the demo video's social engagement; Tracks 2
   and 3 are judged privately. Details and prizes
   are in `references/rules.md`; read it before answering rule questions.

## 2. Track 1: a Cubbie Skill

Walk the team through these steps, one at a time, and skip what they've already done.

1. **Pick the moment.** A specific moment of student life (studying, friends, money, jobs and internships,
   networking, daily life, or their own idea) where Cubbie could notice, start or take care of something. Push for
   one concrete situation a student would text about.
2. **Build it with `cubbie-skill-creator`** (in this kit; in Codex, `$cubbie-skill-creator`). Hand over: the
   moment, that it's a Track 1 entry for the Cubbie Hackathon, and that it has to end in a public GitHub repo.
   It interviews them, writes the Skill, checks it against Cubbie's install rules, helps publish it, and prints the
   pinned install link plus a checklist for testing on their own Cubbie. If that skill isn't installed, point them
   to the kit's README.
3. **Test on Cubbie.** They text the install link to Cubbie and go through the checklist. Fix, push, repeat.
4. **Demo video.** A short video showing the student moment and Cubbie handling it, posted publicly on TikTok or
   Instagram (the only platforms the form accepts). Help with a script or shot list if they want: the problem in
   a sentence, the real iMessage exchange, the result.
5. **Submit** (section 4): Skill link, platform, post link, team, one-liner. They can submit as soon as they have
   a repo and a post, then keep editing while the window is open.
6. **Reach.** Votes need a school email and happen on the site; social views, likes, comments and shares are read
   automatically. More posts with the demo (up to 5 besides the main one) can be added with `posts` until voting
   closes.

When the Skill changes after submitting, push, get the new pinned link from `cubbie-skill-creator`
(`scripts/github_link.py`), and update the entry with `submit --track skills --repo <new link>`.

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
python3 scripts/hackathon.py login --email you@school.edu                   # emails a 6-digit code
python3 scripts/hackathon.py verify --email you@school.edu --code 123456    # saves the session token
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
- The flow: `status` → `login`/`verify` → `mine` → `submit` (preview) → show the user → `submit ... --yes`. After
  sending, the script checks the public gallery and prints its link; share it with the team.

## When something goes wrong

| Message | What to do |
| --- | --- |
| Not signed in / sign-in expired | `login` again; codes last 10 minutes, one per email per 60 seconds |
| That code didn't work | Check the 6 digits or ask for a new code |
| Submissions for this track are not open | Show `status`; the window is closed or not open yet |
| Tracks 2 and 3 open once your team has submitted Track 1 | Submit Track 1 first, from any teammate's account |
| You're already on X's entry for this track | The owner edits it; sign in as them |
| The organizers took this one down | Contact the organizers on Discord |
| The hackathon backend changed | Update this kit (`git pull` in its folder, or reinstall) |

Anything else from the database is a rule message for students: relay it, fix the field, preview again.

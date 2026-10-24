# Cubbie Hackathon: tracks, rules and judging

Source: the event site https://hackathon.cubbie.ai and its submit rules, as of 2026-10-22. The site is still marked
as a working draft ("dates, place and scoring are still being finalized"). When this file and the site disagree,
the site wins; when something is not written here or on the site, say it is not announced yet and point to the
Discord: https://discord.gg/7eJADTbQMT. Open and close times are never written here: read them live with
`python3 scripts/hackathon.py status`.

## The idea

Cubbie (https://cubbie.ai) lives in students' iMessage and handles everyday college life. The hackathon's tagline
is "Teach Cubbie a new trick": build a Skill students would miss if it disappeared.

## Tracks at a glance

| | Track 1 · Cubbie Skills | Track 2 · Agent-to-Agent Coordination | Track 3 · Group Chat Assistant |
| --- | --- | --- | --- |
| Who | Every team; it unlocks Tracks 2 and 3 | Teams that submitted Track 1 | Teams that submitted Track 1 |
| Built on | A Cubbie Skill, run by Cubbie | Anything: any messaging app, any open-source framework | Same as Track 2 |
| Hand in | Skill's GitHub repo + public TikTok or Instagram post with the demo video | GitHub repo; website and demo video optional | Same as Track 2 |
| Winners | Public votes on the site + the video's social engagement | Judges, privately | Judges, privately |
| Window | `skills_*` (see `status`) | `general_*`, shared with Track 3 | `general_*`, shared with Track 2 |

Teams list 1 to 4 members (name and email each) on every entry.

## Track 1 · Cubbie Skills

Challenge: build a Cubbie Skill that solves a student problem so well students would miss it if it disappeared.
Pick a moment of college life that deserves better: studying, making friends, saving and earning money, jobs and
internships, networking, daily life, or something the organizers haven't thought of. What could Cubbie notice,
start, or take care of that makes a student say "I need this"?

How it works (from the site):
- The organizers provide a Skills interface and full docs. (The `cubbie-skill-creator` skill in this kit carries
  what Cubbie can do and how it installs a Skill, and walks you through writing, checking and publishing one.)
- Write your Skill against it and submit it to Cubbie: Cubbie installs a Skill when a student texts it the Skill's
  GitHub link.
- Cubbie runs it with its existing abilities; no app or backend to build.
- Finish within the first 10 hours of the hackathon. The site adds: "Exact Track 1 cutoff is confirmed with the
  organizers before kickoff." The cutoff that counts is the Track 1 close time in `status`.

Show us:
- A working Skill running on Cubbie.
- A clear student use case.
- A short public video showing its value.

Judging: "Post your video on social media and get it in front of students. Judges mainly look at public votes on
this site and your video's engagement on social media." The demo goes on TikTok or Instagram (the only two
platforms the form accepts); the site reads views, likes, comments and shares of those posts automatically while
voting is open and combines them with site votes into one score on the Track 1 board.

## Tracks 2 and 3 (the General Track, split in two; same rules and judging)

Track 2 · Agent-to-Agent Coordination: build personal AI agents for campus life that work with each other. Agents
representing different students exchange the information that matters and work toward a shared outcome:
scheduling a study session, splitting a trip, planning around classes and events.

Track 3 · Group Chat Assistant: build an AI that joins a group chat and makes it more useful, playful, or
surprising, something students would actually want to invite into their group. Tie it to real campus life:
coordinating friends, planning around classes and events, or anything else that makes college better.

How (both):
- Open only to teams that submitted Track 1.
- Doesn't need to be built on Cubbie.
- Any messaging app: iMessage, Slack, WhatsApp, Discord, or another.
- Any open-source framework.

Show us (both):
- A working prototype tied to a real campus scenario.
- Multi-agent? Show how agents handle conflicting constraints, what they share, and when they ask their students
  to confirm.
- A clear reason students would say "We need this".

Judging (both): "Judged privately on what you show us. Full criteria are announced before kickoff." Their gallery
lists published projects (team, project name, one-liner, website, demo video, GitHub repo, newest first) with no
votes or ranking. A gallery card opens the website, else the demo video, else the GitHub repo. GitHub's preview
card only shows for public repos.

## Prizes (from the organizers' prize posters, as shown on the site)

| Track | 1st | 2nd |
| --- | --- | --- |
| Track 1 | Gaming monitor (31.5" curved, WQHD, 180 Hz) | Anker headphones |
| Track 2 | Google Fitbit Charge 6 | Anker speaker |
| Track 3 | Google Home speaker | Gaming mouse |

Track 1 also gets "priority for a Cubbie internship". Separately, a giveaway: use Cubbie, give feedback in the
Discord, and one student is drawn to win a PS5.

## Submitting and editing (enforced by the site's database)

- Sign in with Google or with a 6-digit code by email, on the site or with this kit. One email address is one
  account either way (checked on 2026-10-23: Google on the site, Google in the kit and an email code all reached the
  same account). A different address is a different account, even for the same person: a school alias, a personal
  Gmail, Gmail with or without dots, a `+tag`. Google uses the Google account's primary address. Use your school
  email: anyone can submit, but only school emails can vote.
- One entry per person per track. Whoever sends it owns it; the members listed on it see it but can't start a
  second entry for that track, and only the owner can edit it.
- No review gate: an entry is live in the public gallery the moment it is sent (Track 1 can be voted on at once).
- The team edits freely while the track's window is open. Edits keep the entry live and keep its votes. Closing
  the window locks entries.
- Organizers can still send an entry back with a note (it leaves the gallery until the team edits it, which is
  allowed even after the window closes) or take it down (the team can't bring it back).
- Public: team name, project name, one-liner, links. Not public: members and their emails.
- Track 1 can add up to 5 more social posts with the demo (besides the main one) until voting closes; their
  reach counts too.

Field limits: team name and project name up to 60 characters (project name defaults to the team name), one-liner
up to 140, 1 to 4 members with distinct emails, every link `https://`. Track 1: the Skill link must be a GitHub
repo (`https://github.com/<owner>/<repo>` or a folder inside it) and the post must be on the platform picked.
Tracks 2 and 3: GitHub repo required; website (one link) and demo video optional.

## Voting (Track 1 only)

Voting needs a school email (`*.edu` or a known school domain; `+tag` aliases are refused), happens on the site
while the voting window is open, one vote per project, not for an entry you own or are listed on, and you can take
a vote back. The per-person cap is in `status`.

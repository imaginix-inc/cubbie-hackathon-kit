# From a student moment to a Track 1 idea

Use this while a team is looking for an idea or checking whether theirs works on Cubbie. It condenses the
organizers' build guide (2026-10-19) and the idea cards from the first version of the hackathon site. For what
Cubbie can do and the rules a Skill must follow, read `cubbie-skill-creator`'s
`references/cubbie-capabilities.md` and `references/cubbie-auth.md` (in the sibling folder
`../cubbie-skill-creator/`, or at
https://github.com/imaginix-inc/cubbie-hackathon-kit/tree/main/skills/cubbie-skill-creator/references).

## What makes a strong Track 1 Skill

- **One moment in a student's week.** "It's Sunday night and I have no idea what's due" beats "a deadline API".
  The site's challenge: something students would miss if it disappeared, that makes them say "I need this".
- **Cubbie brings the abilities, the Skill brings the know-how.** No app or backend: name what Cubbie should do in
  plain words ("read the student's Canvas due dates", "set a check-in at 9 pm"). Add scripts only for what Cubbie
  can't do on its own (a specific API, exact math, parsing a file, a command-line tool).
- **Recurring value.** Scheduled check-ins bring students back; let the student pick the time and how often.
- **The student's yes.** Sending, booking, submitting or paying always waits for it; payment goes to the student.
- **Written for a text thread.** Short messages, one idea each, links on their own line.
- **Little or no sign-in.** Every sign-in step costs installs. Prefer public data or accounts already connected to
  Cubbie (Canvas, Google); see the sign-in ladder in `cubbie-auth.md`.
- **It demos in a short video.** Track 1 is won mostly on public votes and the demo's social engagement, so the
  moment should be one viewers recognize in seconds, and the Skill's result should be visible in the iMessage
  thread.

## Seven starting points

| Area | Example Skill | The moment | What it does | Cubbie abilities | Sign-in | Watch out for |
| --- | --- | --- | --- | --- | --- | --- |
| Studying | Exam Sprint | "Midterm in 3 days. Syllabus: 14 pages." | Turns the syllabus and course materials into a plan, practice questions and reminders | Canvas, documents, reminders, wake-up calls | Accounts already connected | Cite the course materials; help them learn, don't do graded work for them |
| Food and dining | Late-Night Food Run | "It's 1 AM. Nothing's open. Or is it?" | Compares what's open, checks the dining hall menu, prepares an order | Web, browser, memory (diet, budget), reminders | None for menus; website sign-in for ordering | Cubbie never pays; the student takes over the browser to check out |
| Jobs and internships | Internship Radar | "3 postings close Friday. You found out Thursday." | Finds postings that fit the major, tracks deadlines, drafts cover letters | Web, scripts for a job board API, reminders, documents, Gmail drafts | None, or the student's own API key | Apply or send emails only after the student says yes |
| Money | Budget Buddy | "$12.07 until Friday." | Tracks spending from receipts and email, finds student discounts | Email events, files (receipt photos), memory, web | None, or connected accounts | No bank logins and no moving money |
| Campus systems | Study Room Booker | "Finals week. Every room is 'unavailable'." | Books a library room, checks rec center slots or laundry | Browser, reminders, calendar | Website sign-in in Cubbie's browser | Sites differ by school; say which schools it supports |
| Friends and social | Hangout Planner | "Everyone's 'free sometime'." | Finds a free evening, suggests places, sets a reminder | Calendar, web, reminders | Accounts already connected | Cubbie texts only its own student; reaching friends goes through the student |
| Daily life | Shuttle Tracker | "Next shuttle: ??? Also it's raining." | Next campus shuttle, weather before class | Web, scripts for a public transit feed, reminders | None (public feeds) | Keep messages short and timely |

## Conversation starters

When a team has no idea yet, show a few of these notifications and ask which one they've lived through this week,
then turn it into a moment, a Skill and the abilities it needs.

| Notification | Leads to |
| --- | --- |
| Canvas: "PSET 4 · Due tonight at 11:59 PM" | Studying |
| Calendar: "ECON 201 midterm · Thursday 9:00 AM" | Studying |
| group project: "can someone start the slides 🙏" | Studying |
| Dining: "Late night dining · Closes in 20 min" | Food |
| Mom: "did u eat today" | Food |
| Mail: "Re: Re: Re: interview time? 'Does Thursday 2pm work…'" | Jobs |
| Job board: "3 internships close this Friday" | Jobs |
| Pay: "Alex requested $23.40 · 🍕 friday pizza" | Money |
| Bank: "Balance $12.07" | Money |
| Library: "Study rooms · 0 available today" | Campus |
| Laundry: "Dryer 3 · Done 40 min ago" | Campus |
| roommates 🏠: "anyone free this weekend??" | Social |
| club board: "meeting moved to 8pm???" | Social |
| Transit: "Shuttle B · Delayed 25 min" | Daily life |
| Weather: "Rain at 2 PM · You have class at 2:10" | Daily life |

These are illustrations, not real messages.

## Is it doable on Cubbie? Check before building

1. Every ability it needs is in `cubbie-capabilities.md`, named in plain words.
2. Its sign-in is the lowest rung that works in `cubbie-auth.md`; Cubbie can't host the team's own keys for every
   student, and nobody pastes passwords or keys into the chat.
3. Nothing it needs is under "Not supported yet" (MCP servers, `apt`, plain HTTP, databases, OAuth buttons for the
   team's own app, scripts calling Cubbie's abilities, Cubbie texting other people).
4. Scripts get their data from Cubbie as arguments or a file; they can't call Canvas, the calendar or memory
   themselves.
5. The main flow fits in a few text messages, and the result shows up in the thread.

If a check fails, reshape the idea (a different data source, a lower sign-in rung, the student doing one step)
before writing anything.

## Done for Track 1

The organizers' guide set the bar: Cubbie installs the Skill from its GitHub link, and its main flow runs on a
real account. The site asks for a working Skill running on Cubbie, a clear student use case and a short public
video showing its value.

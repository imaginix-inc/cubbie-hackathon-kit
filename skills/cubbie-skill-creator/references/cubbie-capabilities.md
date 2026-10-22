# What Cubbie can already do

Cubbie is an AI assistant that lives in a student's iMessage. It already knows the student's classes and can look
things up, remember, remind, browse and make calls. A Cubbie Skill does not reimplement any of this. It names the
ability it needs **in plain words** in `SKILL.md` ("check the student's Canvas due dates", "set a reminder for 8 pm"),
and Cubbie picks its own tool and fills in the exact parameters.

Never write Cubbie tool names, parameters or JSON into `SKILL.md`: they change, and other agents do not have them.
Plain words keep the Skill readable in Claude Code and Codex too.

## Abilities

*Connected* abilities work once the student has linked that account to Cubbie.

| Ability | What Cubbie does | How a Skill can name it | A Skill could... |
| --- | --- | --- | --- |
| Canvas (*connected*) | Reads courses, assignments and due dates, grades, announcements, discussions, course pages, files and the Canvas inbox; searches and reads course materials | "Read the student's Canvas assignments due in the next 7 days", "search the course materials for the midterm topics" | Turn a syllabus into a weekly study plan; warn before a grade-heavy week |
| Reminders and scheduled check-ins | Runs a task once or on a schedule and reaches the student by text or by **phone call** | "Create a daily check-in at 9 pm that lists what is due tomorrow", "call the student at 7 am" | Send a 9 pm "what's due tomorrow" check-in; call the student to wake them for an exam |
| Background tasks | Works on a longer job on its own and reports back when done | "Do this as a background task and text the student the shortlist when it is ready" | Compare ten apartment listings and send a shortlist later |
| Web | Searches the web, reads pages and PDFs, finds images | "Search the web for...", "read the dining hall menu page" | Pull today's dining hall menu or a club's event page |
| Browser | Opens a site in its own cloud browser, clicks and fills forms; the student can sign in or take over for a step such as payment | "Open the library booking site in the browser and pick the slot", "hand the browser to the student to pay" | Book a study room on a campus site that has no API |
| Google (*connected*) | Gmail, Calendar, Drive, Docs, Sheets, Tasks and Contacts | "Draft (do not send) an email to the professor", "add the exam dates to the student's Google Calendar" | Draft an email to a professor; add exam dates to the calendar |
| Email events (*connected*) | Searches the student's synced email and the events extracted from it | "Search the student's email for the interview time" | Find the internship interview time buried in an email thread |
| Documents and slides | Creates Word, PDF, Excel, Markdown, calendar (.ics) and HTML files, and slide decks | "Make a one-page PDF study guide and send it" | Produce a one-page resume or a study guide PDF |
| Files and media | Reads photos, PDFs and documents the student sends; transcribes voice notes and videos | "Read the receipt photo the student sent" | Turn a photo of a whiteboard into clean notes |
| Memory | Remembers facts and preferences about the student across conversations | "Remember the student's dietary needs", "use the budget the student set before" | Remember dietary needs or a budget and use them next time |
| Secure input | Sends a private page to collect a password, API key, phone or email; the value never enters the chat | Usually automatic for `secrets` in `cubbie.yaml`; otherwise "collect the student's library card number through a secure page" | Collect a key your Skill needs |
| Code sandbox | Runs Python and Node scripts in the student's private sandbox, with files that persist; a long command (a login, a build) can run in the background for up to an hour | "Run `python3 scripts/plan.py --course <id>`" | Run your Skill's own scripts and command-line tools |

Cubbie also writes replies, follows up proactively within the student's notification settings, and asks before it
sends a message to someone else, submits work or changes an account.

## Rules that shape a Skill

- **Scripts cannot call Cubbie's abilities.** There is no Cubbie token in the sandbox. Have Cubbie fetch what the
  script needs (Canvas, calendar, memory) first, then pass it to the script as arguments or a file. In the other
  direction, have the script print what Cubbie needs next (for a PDF, the text or Markdown to put in it).
- **Scheduled check-ins run later, on their own.** Word each one so it makes sense days later: which Skill, which
  course or item, and what to check or run.
- **Plan for a missing connection.** For each *connected* ability, say what to do when the student has not linked
  the account: for example, ask them to connect Canvas and stop, or fall back to asking for the dates.
- **Cubbie texts only its own student.** Reaching friends, classmates or professors goes through the student: draft
  the message and let the student send it, or send it only after the student says yes.
- **The student's yes is always required** for sending, booking, submitting or paying. A Skill cannot grant that
  approval. For payment, hand the browser to the student.
- **Keep personal data with the student.** Let Cubbie remember preferences. Send data to your own server only when
  the Skill says so plainly and the host is declared in `cubbie.yaml`.

## Built-in Skills

Cubbie ships two Skills of its own. Their names are reserved, and Cubbie already handles their requests:

- `email-to-professor`: drafts formal emails to professors or TAs (absence, extension, office hours, grade questions); never sends without the student's yes.
- `study-plan-builder`: builds or adjusts a day-by-day study or review plan from free time and deadlines.

A Skill in the same area should add something these do not (a specific workflow, a script, a recurring check-in) and
say so in its description, so Cubbie can tell when to use it.

## Not supported yet

| Supported | Not supported yet |
| --- | --- |
| Skills in the Agent Skills format, from public GitHub repositories | MCP servers, remote or local |
| Python and Node scripts; pip and npm packages; prebuilt binaries by URL with a SHA-256 | System packages (`apt`), install scripts (`curl \| sh`), git or URL dependencies |
| HTTPS to the hosts you declare and to PyPI and npm; other hosts once the student approves them | Plain HTTP, SSH, databases; reaching a server you start from outside the sandbox |
| Sign-in through Cubbie's browser, CLI login links and student API keys | "Sign in with ..." (OAuth) buttons for your own app; hosting your team's keys for all students |
| Cubbie's abilities, called by Cubbie as your `SKILL.md` describes | Scripts calling Cubbie's abilities directly; Cubbie texting people other than its student |

Packages: pin exact versions in `cubbie.yaml` (most reliable). A Skill without `cubbie.yaml` still installs: Cubbie
reads the commands in `metadata.requires.bins` and the install commands in `SKILL.md` and the README, works out the
PyPI or npm packages, pins their latest versions and shows them as "added by Cubbie" for the student to approve.

Limits per Skill: at most 10 MiB and 300 files (1 MiB each), up to 10 hosts and 5 keys; the repository archive Cubbie
downloads must be at most 30 MiB. One link to a folder of Skills installs up to 40 of them together, sharing one set
of packages. Cubbie also caps how many Skills a student can install (50 by default).

## Scenario starting points

The sign-in column refers to the approaches in [cubbie-auth.md](cubbie-auth.md).

| Scenario and example Skill | Abilities to combine | Sign-in | Watch out for |
| --- | --- | --- | --- |
| **Food and dining.** "Late-night food run": compare what is open, check the dining hall menu, prepare an order | Web, browser, memory (diet and budget), reminders | 1 for menus; 3 for ordering sites | Cubbie never pays; the student takes over the browser to check out |
| **Campus systems.** "Study room booker": book a library room, check rec center slots or laundry | Browser, reminders, calendar | 3 | Sites differ by school; say which schools the Skill supports |
| **Studying.** "Exam sprint": turn the syllabus and course materials into a plan, practice questions and reminders | Canvas, documents, reminders and wake-up calls | 2 | Cite the course materials; help the student learn, do not do graded work for them |
| **Money.** "Budget buddy": track spending from receipts and email, find student discounts | Email events, files (receipt photos), memory, web | 1 or 2 | No bank logins and no moving money |
| **Jobs and internships.** "Internship radar": find postings that fit the student's major, track deadlines, draft cover letters | Web, scripts for a job board API, reminders, documents, Gmail drafts | 1, or 5 if the API needs a key | Submit applications or send emails only after the student says yes |
| **Friends and social.** "Hangout planner": find a free evening, suggest places, set a reminder | Calendar, web, reminders | 2 | Cubbie texts only its own student; reaching friends goes through the student |
| **Daily life.** "Shuttle tracker": next campus shuttle, weather before class | Web, scripts for a public transit feed, reminders | 1 | Keep messages short and timely |

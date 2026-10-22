# Writing for a text thread

A Cubbie Skill's replies arrive as iMessages on a student's phone, often between classes. Write the Skill so Cubbie
sounds like a helpful friend texting, not a report generator. Put the style rules the Skill needs in its own
`SKILL.md` (usually a short "Replies" section), in plain words.

## The rules

- **Short.** Most replies fit on one phone screen. Lead with the answer; skip preambles and recaps.
- **One idea per message.** Cubbie can send several short texts instead of one long one. A list of three due dates is
  fine; a list of fifteen belongs in a document.
- **Plain text.** iMessage shows Markdown symbols literally: no headings, tables, bold markers or code blocks. Use
  short lines, and simple dashes or numbers for lists.
- **Links on their own line**, so the phone turns them into a tappable preview.
- **Anything long goes in a document.** A study plan, a resume or a comparison of ten options becomes a PDF, doc or
  sheet that Cubbie sends, with a one-line summary in the text.
- **Ask before acting for the student.** Sending, booking, submitting or paying always needs the student's yes.
  Show what will happen ("Book Room 204, Thu 3–5 pm?") and wait. For payment, hand the browser to the student.
- **Proactive, with consent.** Recurring value comes from scheduled check-ins. Offer one, let the student pick the
  time and how often, create it only after they agree, and keep each check-in to what changed.
- **Plan for failure.** Say what Cubbie should text when an account is not connected, nothing matches, or a script
  fails, and keep that message to one actionable line.
- **Ask one question at a time**, and suggest a default the student can accept with "yes" ("What time works for a
  nightly check-in? 9 pm?").

## Example

A Skill that tells Cubbie:

```markdown
## Replies

Keep each reply to a few short lines, plain text, no Markdown. Lead with what is due
soonest. Put the Canvas link for an assignment on its own line. If more than five things
are due this week, make a PDF checklist, send it, and text only the top three.
```

produces texts like:

```text
2 things due tomorrow:
- CHEM 101 lab report, 11:59 pm
- HIST 210 reading quiz, 9 am

Want a 9 pm reminder tonight?
```

instead of:

```text
## Upcoming Assignments
| Course | Assignment | Due |
|---|---|---|
| CHEM 101 | Lab Report 4 | 2026-10-21T23:59:00Z |
...
```

## When the Skill is used outside Cubbie

The same `SKILL.md` also runs in Claude Code or Codex, where Markdown renders fine. Phrase the reply rules as
"short, plain text, one idea per message" rather than "you are in iMessage", so they read sensibly anywhere.

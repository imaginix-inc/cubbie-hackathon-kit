---
name: canvas-deadline-nudge
description: Sets reminders before upcoming Canvas assignment deadlines. Use when the student asks what is due soon and wants to be reminded, says they keep missing due dates, or asks for reminders before every assignment in a course.
---

# Canvas Deadline Nudge

This Skill uses only Cubbie's built-in capabilities. It has no scripts and no `cubbie.yaml`.

## When to use

- "What's due this week? Remind me before each one."
- "I keep missing deadlines in BIO 201, can you nudge me?"
- "Remind me the night before every assignment this month."

Do not use it for study plans, exam preparation or anything that changes Canvas.

## Steps

1. Get upcoming assignments with Cubbie's **Canvas** capability (assignments and due dates).
   Look 7 days ahead unless the student named a course or a different range.
   If Canvas is not connected, tell the student, offer to connect it, and stop.
2. Leave out assignments that Canvas reports as already submitted.
   Keep assignments without a due date aside and list them separately at the end.
3. For each remaining assignment, propose two reminders in the student's time zone:
   24 hours before the due time and 2 hours before it. Drop any reminder time that has already passed.
   If something is due in less than 2 hours, say so right away instead of scheduling a reminder for it.
4. Show the plan as a short list (course, assignment, due time, reminder times) and ask the student to
   confirm or adjust it. Do not create any reminder before the student says yes.
5. After the student confirms, create each reminder with Cubbie's **Reminders** capability.
   Each reminder names the course, the assignment and the due time, plus the assignment link when Canvas returned one.

## Output

After creating reminders, reply in two or three lines: how many reminders were set, the next one,
and any assignments without a due date. Keep the full list for when the student asks.

## When something fails

- Nothing is due in the window: say so and offer to look 14 days ahead.
- Some reminders could not be created: list which ones and offer to retry once. Do not retry silently.
- Use only assignments and dates that Canvas returned. Never guess a due date.

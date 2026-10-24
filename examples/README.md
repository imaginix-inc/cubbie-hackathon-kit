# Example Cubbie Skills

Three small, working Skills that show the three shapes a Cubbie Skill usually takes. Each is a plain
Agent Skills folder (a `SKILL.md`, plus scripts where needed), passes `cubbie-skill-creator`'s checks without
warnings and installs on Cubbie as it is.

| Skill | Shape | What it shows |
| --- | --- | --- |
| [`canvas-deadline-nudge`](canvas-deadline-nudge) | Instructions only | Using Cubbie's own abilities (Canvas, reminders) in plain words; asking before acting; what to say when Canvas isn't connected |
| [`weather-before-class`](weather-before-class) | A Python script with a package and a student's key | A Setup step with a pinned package in its own virtual environment, an API key collected on a secure page and named in the run command; a `--sample` mode; exit codes mapped to replies |
| [`netlify-publish`](netlify-publish) | A command-line tool with a sign-in | An npm CLI installed with `npm install -g`, a two-step browser sign-in, and state remembered under `HOME` between conversations |

## Try one on your own Cubbie

Text Cubbie the folder's link, for example:

```text
https://github.com/imaginix-inc/cubbie-hackathon-kit/tree/main/examples/canvas-deadline-nudge
```

Cubbie tells you what it is about to fetch and asks first, since it is someone else's code; reply "yes". It
fetches the repository with git, copies the folder to your drive at `/user/skills/<name>/`, and sets up what the
Skill's `SKILL.md` asks for (a package, a key, a sign-in). Then talk to it the way a student would ("what's due
this week? remind me before each one"). From your next message on, "What Skills do I have?" lists it. Text the link
again to update a Skill, and ask "remove canvas-deadline-nudge" to delete its folder. Installs are per student:
installing a Skill adds it only for you.

Doing this once before you write your own Skill shows you exactly what your users will see.

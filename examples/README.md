# Example Cubbie Skills

Three small, working Skills that show the three shapes a Cubbie Skill usually takes. Each is a plain
Agent Skills folder (no extra files), passes `cubbie-skill-creator`'s checks and installs on Cubbie as it is.

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

Cubbie replies with a summary (what the Skill does, the commit, the install commands it gives and the keys it
reads) and asks before installing; reply "yes". The folder lands on your drive at `/user/skills/<name>/`. Then talk to it the way a student would ("what's due this week? remind me before
each one"). "What Skills do I have?" lists your Skills, and "remove canvas-deadline-nudge" takes it off again.
Installs are per student: installing a Skill adds it only for you.

Doing this once before you write your own Skill shows you exactly what your users will see.

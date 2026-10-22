# Example Cubbie Skills

Three small, working Skills that show the three shapes a Cubbie Skill usually takes. Each one passes
`cubbie-skill-creator`'s checks and installs on Cubbie as it is.

| Skill | Shape | What it shows |
| --- | --- | --- |
| [`canvas-deadline-nudge`](canvas-deadline-nudge) | Instructions only | Using Cubbie's own abilities (Canvas, reminders) in plain words; asking before acting; what to say when Canvas isn't connected |
| [`weather-before-class`](weather-before-class) | A Python script with a package and a student's key | `cubbie.yaml` with a pinned pip package, one website and an API key collected on a secure page; a `--sample` mode; exit codes mapped to replies |
| [`netlify-publish`](netlify-publish) | A command-line tool with a sign-in | An npm CLI, a two-step browser sign-in, and state remembered between conversations |

## Try one on your own Cubbie

Text Cubbie the folder's link, for example:

```text
https://github.com/imaginix-inc/cubbie-hackathon-kit/tree/main/examples/canvas-deadline-nudge
```

Cubbie replies with a summary (what the Skill does, the commit, packages, websites, keys and sign-ins) and asks
before installing; reply "yes". Then talk to it the way a student would ("what's due this week? remind me before
each one"). "What Skills do I have?" lists your Skills, and "remove canvas-deadline-nudge" takes it off again.
Installs are per student: installing a Skill adds it only for you.

Doing this once before you write your own Skill shows you exactly what your users will see.

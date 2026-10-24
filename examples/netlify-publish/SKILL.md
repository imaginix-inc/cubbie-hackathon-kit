---
name: netlify-publish
description: Publishes a folder of web pages to the student's own Netlify account and sends back the link. Use when the student wants to put a web page, portfolio or class project online, or update their site.
---

# Netlify Publish

## When to use

- "Put my portfolio online."
- "Can you publish the page you made for my CS project?"
- "Update my site with the new version."

Only static files: a folder with an `index.html`. No build step and no server code.

## Setup (first time only)

Install the Netlify CLI once; Cubbie keeps global npm packages across restarts:

```bash
npm install -g netlify-cli@27.12.1
```

If `netlify` is not found later, run this again.

## Sign in (first time only)

The student signs in to their own free Netlify account in the browser. There is no key to paste.

1. Run `python3 scripts/publish.py status`. Exit code 0 means the student is signed in; go to Publish.
2. Start the sign-in:

   ```bash
   netlify login --request "Cubbie wants to publish web pages for you" --json
   ```

   It returns at once with a `ticket_id` and a `url`.
3. Send the student the `url`, ask them to approve it in the browser (they can create a free account there),
   and to reply when done. End your turn; do not wait or poll.
4. When the student replies, run `netlify login --check <ticket_id> --json` and read `status`:
   - `authorized`: signed in. The sign-in is kept for later conversations. Continue with Publish.
   - `pending`: not approved yet. Ask the student to finish in the browser, then check again.
   - `denied`: declined or expired. Start again from step 2.

## Publish

1. Find the folder to publish, usually under `/workspace/your_files/`. It must contain `index.html`.
   If the student has a single HTML file, put it in a new folder as `index.html` first.
2. Pick a site name with lowercase letters, digits and hyphens, for example `maya-portfolio`.
   Reuse the same name to update a site published before.
3. Tell the student that everything in the folder becomes public at a `netlify.app` link, and publish only after they say yes.
4. Run:

   ```bash
   python3 scripts/publish.py deploy --dir "<folder>" --name <site-name>
   ```

   If another Netlify user already has the name, Netlify adds a suffix; the script remembers the site it created.
5. Send the student the link the script printed.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Invalid site name | Pick a name with lowercase letters, digits and hyphens |
| 3 | Not signed in, or the sign-in expired | Sign in again (steps 2 to 4 above) |
| 4 | Folder missing or no `index.html` | Ask the student which folder to publish |
| 5 | Netlify error | Tell the student briefly. If it lists several teams, ask which one and add `--team <slug>`. If the saved site no longer exists, add `--new-site` |

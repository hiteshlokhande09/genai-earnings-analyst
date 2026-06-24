# 09 — Pushing to GitHub

This guide pushes the project to GitHub **safely** — the most important word
here is *safely*, because the one thing you must never commit is your
`.env` file with the Llama 3 API key. The project already ships a `.gitignore`
that excludes `.env`, `data/`, `__pycache__/`, and model caches, so if you
follow these steps you're protected.

> **Do this yourself.** Creating the repo, authenticating, and pushing involve
> your own GitHub credentials. The steps below are exactly what to run.

---

## 0. One-time prerequisites

- Install **git**: <https://git-scm.com/downloads> (verify with `git --version`).
- A free **GitHub account**: <https://github.com>.
- Tell git who you are (once per machine):

```bash
git config --global user.name  "Your Name"
git config --global user.email "your@email.com"
```

---

## 1. Confirm the secret is protected

From the project root:

```bash
cat .gitignore
```

Make sure it lists `.env`. Confirm you have **no** real `.env` committed — only
`.env.example` (a template with no real key) should ever be tracked. If you
created a `.env`, that's fine locally; `.gitignore` keeps it out of git.

---

## 2. Initialise the repository

```bash
cd genai-earnings-analyst
git init
git add .
git status        # review the list — confirm .env is NOT listed
git commit -m "Initial commit: GenAI Financial Earnings Report Analyst"
```

If `git status` shows `.env`, **stop** and fix `.gitignore` before committing.

---

## 3. Create the repository on GitHub

Two options:

**A. Web UI (simplest).** Go to <https://github.com/new>, name it
`genai-earnings-analyst`, leave it empty (no README/.gitignore/license — you
already have them), and click *Create repository*. GitHub then shows you the
remote URL.

**B. GitHub CLI.** If you have `gh` installed and authenticated:

```bash
gh repo create genai-earnings-analyst --private --source=. --remote=origin
```

(Use `--public` instead of `--private` if you want it visible.)

---

## 4. Connect and push (if you used the web UI)

Copy the HTTPS URL GitHub gave you, then:

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/genai-earnings-analyst.git
git push -u origin main
```

You'll be prompted to authenticate. For HTTPS, use a **Personal Access Token**
as the password (GitHub no longer accepts account passwords on the command
line): create one at *GitHub → Settings → Developer settings → Personal access
tokens*, with `repo` scope.

---

## 5. Verify

Refresh the repo page on GitHub. You should see all the `.py` files, the
`knowledge transfer/` folder, `README.md`, `requirements.txt`, and
`.env.example` — but **not** `.env`, `data/`, or `__pycache__/`.

---

## Ongoing workflow

After the first push, day-to-day updates are:

```bash
git add .
git commit -m "Describe what changed"
git push
```

---

## If you ever commit a secret by accident

1. **Revoke the key immediately** at your LLM provider (Groq/Together/etc.) and
   issue a new one.
2. Remove the file from tracking: `git rm --cached .env && git commit -m "Remove .env"`.
3. Because git keeps history, rotating the key is the real fix — assume any
   key that was ever pushed is compromised. (For full history scrubbing, tools
   like `git filter-repo` exist, but rotating the key is what actually protects
   you.)

---

## Optional niceties

- Add a `LICENSE` file (MIT is common for academic projects).
- Add screenshots of the dashboard + a sample PDF to the README so reviewers see
  output without running anything.
- Tag your review submissions: `git tag review-1 && git push --tags`.

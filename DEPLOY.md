# Deploy as a private web app (Hugging Face Spaces)

Goal: open the slide finder from your phone, for **you only**. It runs as a *private* Space,
visible only when you are logged in to Hugging Face.

> **Keep it private.** The index contains the text of the course slides. The authors allow
> sharing with credit (see the notice on slide 1), but the PDFs may include your lecturer's
> own additions, so do not make the Space public. Never commit `chroma_db/` to GitHub
> (`.gitignore` already blocks it).

What you need to know before starting:
- The app uses about **1.2 GB of RAM** (measured), so small free hosts (512 MB) cannot run it.
  Hugging Face's documentation lists 16 GB for free CPU Spaces, but some users report the free
  tier was restricted: check the hardware options when you create the Space.
- The first search after the Space has been idle is slow (the model loads again).
- `Dockerfile` was written but **not tested locally** (Docker is not installed on this PC).
  The first build on Hugging Face is the real test; its log shows any error.

## 1. Create the Space
1. Sign up at huggingface.co, then *New Space*.
2. SDK: **Docker** (Blank). Hardware: **CPU basic** (free). Visibility: **Private**.
3. Create a *write* access token: Settings → Access Tokens.

## 2. Build a folder to upload (outside the GitHub repo)
From the project folder, in PowerShell:

```powershell
$build = "..\space_build"
New-Item -ItemType Directory -Force $build | Out-Null
Copy-Item Dockerfile, .dockerignore, requirements.txt $build
Copy-Item app $build -Recurse -Force
Copy-Item chroma_db $build -Recurse -Force
@"
---
title: Slide Finder
sdk: docker
app_port: 7860
---
"@ | Set-Content -Encoding utf8 "$build\README.md"
```

The index (`chroma_db/`) is the one built on your PC with `python -m app.cli index`.
The PDFs are **not** uploaded.

## 3. Push to the Space

```powershell
cd ..\space_build
git init -b main
git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
git add -A
git commit -m "Deploy slide finder"
git push space main
```

Git asks for a username and password: use your Hugging Face username and the **token** as the password.
The Space builds automatically (a few minutes). Open it while logged in to Hugging Face, on your
phone too.

## Updating
After changing the code or re-running `python -m app.cli index`, repeat step 2 and then
`git add -A`, `git commit`, `git push space main` inside `..\space_build`.

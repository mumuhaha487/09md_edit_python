# Flask Markdown Sync

A minimal Flask app that serves a static editor UI from `public/`, uploads images to an image bed,
and syncs generated Markdown files into a Git repository. It supports CNB, GitHub, GitLab, and
other Git providers by combining `GIT_BASE_URL` and `REPO` to form the remote URL automatically.

## Features
- Static UI served from `public/`.
- Image upload proxy to a configurable image bed.
- Markdown sync to a Git repo with auto-commit and push.
- Auto-loads environment variables from `project/.env`.

## Run
```bash
cd /workspace/project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server listens on port `3000` by default. Set `PORT` to override.

## Environment Variables
Required for Git sync:
- `REPO` Example: `user/repo`
- `GIT_USERNAME` Example: `user`
- `TOKEN` Personal access token or app token

Optional Git settings:
- `GIT_BASE_URL` Base host for your Git provider. Example values: `https://cnb.cool`,
  `https://github.com`, `https://gitlab.com`.
- `REMOTE_URL` Full Git remote URL override. If set, it is used directly and
  `GIT_BASE_URL` is ignored for cloning. If `GIT_BASE_URL` is not set, it will
  be derived from `REMOTE_URL`.
- `GIT_AUTHOR_NAME` Git commit author name. Default: `GIT_USERNAME`.
- `GIT_AUTHOR_EMAIL` Git commit author email. Default: `${GIT_USERNAME}@users.noreply.cnb.cool`.
- `MARKDOWN_TARGET_DIR` Target directory inside the repo. Default: `123`.

Image bed:
- `IMAGE_BED_UPLOAD_URL` Upload endpoint.
- `IMAGE_BED_PUBLIC_BASE_URL` Public base URL for rendering images.
- `IMAGE_BED_TOKEN` Bearer token for image bed API.

## Git URL Behavior
Clone URL behavior:
- If `REMOTE_URL` is set, it is used as-is.
- Otherwise, it is built as `${GIT_BASE_URL}/${REPO}.git`.

File URL generation behavior after upload:
- `cnb.cool` and GitLab use `/-/blob/`.
- GitHub uses `/blob/`.
- Other hosts fall back to `/blob/`.

If your Git host has a different web URL pattern, you can still use this app
by overriding `REMOTE_URL` and adjusting `GIT_BASE_URL` or the code in `build_file_url()`.

## Pros and Cons
Pros:
- Minimal dependencies and easy to deploy.
- Works with multiple Git providers.
- No Node.js required.

Cons:
- Git operations are performed on every upload (clone + commit + push).
- File URL generation is heuristic for non-standard Git hosts.

## Project Structure
- `app.py` Flask server and API handlers.
- `public/` Static frontend.
- `requirements.txt` Python dependencies.
- `.env` Runtime configuration.

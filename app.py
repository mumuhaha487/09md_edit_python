import base64
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import quote, urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def env(name, default=None):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


cnb_git_username = env("GIT_USERNAME", "mumuemhaha")
cnb_repo = env("REPO", "mumuemhaha/test")
cnb_token = env("TOKEN", "cOB6LW54nY56U168bLhFDmw27pC")
remote_url_override = env("REMOTE_URL")
git_base_url_env = os.environ.get("GIT_BASE_URL")
if git_base_url_env and git_base_url_env.strip():
    git_base_url = git_base_url_env.rstrip("/")
elif remote_url_override:
    parsed = urlparse(remote_url_override)
    if parsed.scheme and parsed.netloc:
        git_base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    else:
        git_base_url = "https://cnb.cool"
else:
    git_base_url = "https://cnb.cool"
cnb_git_author_name = env("GIT_AUTHOR_NAME", cnb_git_username)
cnb_git_author_email = env("GIT_AUTHOR_EMAIL", f"{cnb_git_username}@users.noreply.cnb.cool")
markdown_target_dir = env("MARKDOWN_TARGET_DIR", "123")
image_bed_upload_url = env("IMAGE_BED_UPLOAD_URL", "https://image.0ha.top/upload")
image_bed_public_base_url = env("IMAGE_BED_PUBLIC_BASE_URL", "https://image.0ha.top").rstrip("/")
image_bed_token = env("IMAGE_BED_TOKEN", "imgbed_kLM2BsoFaqgCYfdd0GYwngAGulAVUBQY")


def build_remote_url():
    if remote_url_override:
        return remote_url_override
    return f"{git_base_url}/{cnb_repo}.git"


def build_file_url(branch, relative_file_path):
    base = git_base_url.rstrip("/")
    host = urlparse(base).netloc.lower()
    encoded_branch = quote(branch)
    encoded_path = quote(relative_file_path, safe="/")
    if "cnb.cool" in host:
        return f"{base}/{cnb_repo}/-/blob/{encoded_branch}/{encoded_path}"
    if "gitlab" in host:
        return f"{base}/{cnb_repo}/-/blob/{encoded_branch}/{encoded_path}"
    if "github.com" in host:
        return f"{base}/{cnb_repo}/blob/{encoded_branch}/{encoded_path}"
    return f"{base}/{cnb_repo}/blob/{encoded_branch}/{encoded_path}"

app = Flask(__name__, static_folder="public", static_url_path="")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config")
def api_config():
    return jsonify({"imagePublicBaseUrl": image_bed_public_base_url})


def run_git(args, cwd):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or f"git 失败，退出码 {result.returncode}"
        raise RuntimeError(message)
    return result


def get_git_auth_args():
    basic_auth = base64.b64encode(f"{cnb_git_username}:{cnb_token}".encode()).decode()
    return ["-c", f"http.extraHeader=Authorization: Basic {basic_auth}"]


def safe_markdown_file_name(input_name):
    only_name = os.path.basename(input_name or "")
    normalized = re.sub(r"[^\w.\-()\u4e00-\u9fa5]", "-", only_name)
    if not normalized:
        return "untitled.md"
    if normalized.endswith(".md"):
        return normalized
    return f"{normalized}.md"


def normalize_target_dir(input_dir):
    normalized = (
        str(input_dir or "")
        .replace("\\", "/")
        .split("/")
    )
    cleaned = []
    for segment in normalized:
        segment = segment.strip()
        if not segment or segment in {".", ".."}:
            continue
        cleaned.append(segment)
    if not cleaned:
        return "123"
    return "/".join(cleaned)


def ensure_directory_tree(base_dir, relative_dir):
    segments = [seg for seg in relative_dir.split("/") if seg]
    current_path = base_dir
    for segment in segments:
        current_path = os.path.join(current_path, segment)
        if os.path.exists(current_path):
            if not os.path.isdir(current_path):
                os.remove(current_path)
                os.makedirs(current_path, exist_ok=True)
        else:
            os.makedirs(current_path, exist_ok=True)
    return current_path


@app.post("/api/upload")
def api_upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        timestamp = int(time.time() * 1000)
        original_ext = os.path.splitext(file.filename or "")[1] or ".png"
        new_filename = f"{timestamp}_image{original_ext}"

        files = {
            "file": (
                new_filename,
                file.stream,
                file.mimetype or "application/octet-stream",
            )
        }
        headers = {"Authorization": f"Bearer {image_bed_token}"}
        response = requests.post(
            image_bed_upload_url,
            headers=headers,
            files=files,
            timeout=30,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = response.text
        return jsonify(data)
    except Exception as error:
        return (
            jsonify({"error": "Internal server error", "details": str(error)}),
            500,
        )


@app.post("/api/upload-markdown")
def api_upload_markdown():
    temp_root = ""
    try:
        payload = request.get_json(silent=True) or {}
        name = payload.get("name")
        content = payload.get("content")

        if not name or not isinstance(name, str):
            return jsonify({"error": "文件名缺失"}), 400
        if not isinstance(content, str):
            return jsonify({"error": "Markdown 内容缺失"}), 400

        file_name = safe_markdown_file_name(name)
        temp_root = tempfile.mkdtemp(prefix="md-sync-")
        repo_dir = os.path.join(temp_root, "repo")
        auth_args = get_git_auth_args()

        run_git(
            [*auth_args, "clone", "--depth", "1", build_remote_url(), repo_dir],
            cwd=BASE_DIR,
        )

        branch = "main"
        try:
            head_ref = run_git(
                ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                cwd=repo_dir,
            )
            raw = head_ref.stdout.strip()
            if raw.startswith("origin/"):
                branch = raw[len("origin/") :]
        except Exception:
            local_branch = run_git(
                ["rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_dir,
            )
            branch = local_branch.stdout.strip() or "main"

        normalized_target_dir = normalize_target_dir(markdown_target_dir)
        target_dir = ensure_directory_tree(repo_dir, normalized_target_dir)
        relative_file_path = posixpath.join(normalized_target_dir, file_name)

        with open(os.path.join(target_dir, file_name), "w", encoding="utf-8") as handle:
            handle.write(content)

        run_git(["config", "user.name", cnb_git_author_name], cwd=repo_dir)
        run_git(["config", "user.email", cnb_git_author_email], cwd=repo_dir)
        run_git(["config", "commit.gpgsign", "false"], cwd=repo_dir)
        run_git(["add", "--", relative_file_path], cwd=repo_dir)

        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", relative_file_path],
            cwd=repo_dir,
        )
        has_changes = diff_check.returncode != 0

        if has_changes:
            run_git(
                [
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-m",
                    f"sync markdown: {relative_file_path}",
                ],
                cwd=repo_dir,
            )
            run_git(
                [*auth_args, "push", "origin", f"HEAD:{branch}"],
                cwd=repo_dir,
            )

        file_url = build_file_url(branch, relative_file_path)

        return jsonify(
            {
                "url": file_url,
                "branch": branch,
                "name": file_name,
                "path": relative_file_path,
            }
        )
    except Exception as error:
        return (
            jsonify({"error": "Git 上传 Markdown 失败", "details": str(error)}),
            500,
        )
    finally:
        if temp_root:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    port = int(env("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)

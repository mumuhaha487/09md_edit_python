# Flask Markdown 同步服务

这是一个最小化的 Flask 应用，负责从 `public/` 提供静态编辑器界面、将图片上传到图床，并把生成的 Markdown 文件同步到 Git 仓库。支持 CNB、GitHub、GitLab 等平台，通过 `GIT_BASE_URL` 与 `REPO` 自动拼接远程地址。

## 功能
- 从 `public/` 提供静态页面。
- 图片上传代理到可配置的图床。
- Markdown 同步到 Git 仓库（自动提交并推送）。
- 自动读取 `project/.env` 环境变量。

## 运行
```bash
cd /workspace/project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

默认监听 `3000` 端口，可通过环境变量 `PORT` 覆盖。

## 环境变量
Git 同步所需：
- `REPO` 示例：`user/repo`
- `GIT_USERNAME` 示例：`user`
- `TOKEN` 个人访问令牌或应用令牌

Git 可选设置：
- `GIT_BASE_URL` Git 平台基础地址，例如：`https://cnb.cool`、`https://github.com`、`https://gitlab.com`。
- `REMOTE_URL` 完整 Git 远程地址覆盖项。设置后将直接使用该值进行克隆，并忽略 `GIT_BASE_URL`。如果未设置 `GIT_BASE_URL`，会从 `REMOTE_URL` 推导。
- `GIT_AUTHOR_NAME` Git 提交作者名，默认 `GIT_USERNAME`。
- `GIT_AUTHOR_EMAIL` Git 提交作者邮箱，默认 `${GIT_USERNAME}@users.noreply.cnb.cool`。
- `MARKDOWN_TARGET_DIR` 仓库内目标目录，默认 `123`。

图床：
- `IMAGE_BED_UPLOAD_URL` 上传接口。
- `IMAGE_BED_PUBLIC_BASE_URL` 公网访问基础地址。
- `IMAGE_BED_TOKEN` 图床接口 Bearer Token。

## Git URL 规则
克隆地址：
- 如果设置了 `REMOTE_URL`，直接使用。
- 否则使用 `${GIT_BASE_URL}/${REPO}.git` 自动拼接。

上传后文件 URL 规则：
- `cnb.cool` 与 GitLab 使用 `/-/blob/`。
- GitHub 使用 `/blob/`。
- 其他主机默认使用 `/blob/`。

如果你的 Git 平台 Web URL 规则不同，可以通过覆盖 `REMOTE_URL`，并在 `build_file_url()` 中调整逻辑。

## 优缺点
优点：
- 依赖少，部署简单。
- 兼容多个 Git 平台。
- 不依赖 Node.js。

缺点：
- 每次上传都会执行一次 Git 操作（clone + commit + push）。
- 对非标准 Git 平台的文件 URL 生成是启发式逻辑。

## 项目结构
- `app.py` Flask 服务端及 API 处理逻辑。
- `public/` 前端静态资源。
- `requirements.txt` Python 依赖。
- `.env` 运行时配置。

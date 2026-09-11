# AGENT.md

## 1. Executable Commands

- Dependency setup (local): `python -m venv .venv`
- Activate on Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Activate on POSIX shells: `source .venv/bin/activate`
- Install dependencies: `python -m pip install -r requirements.txt`
- Development run: `python main.py`
- Desktop run: `python app_main.py`
- Build from spec: `pyinstaller --noconfirm video_analyzer.spec`
- Windows build with asset copying: `bash build_windows.sh` (Git Bash/WSL; requires `.venv`)
- Linting with autofix: Not configured
- Formatting: Not configured
- Full test suite: Not configured; no test files or test runner configuration is present
- Targeted test: Not configured
- Single-file syntax validation (read-only): `python -c "import ast, pathlib; p=pathlib.Path('src/ui.py'); ast.parse(p.read_text(encoding='utf-8'), filename=str(p)); print(f'Parsed {p}')"`
- Type checking: Not configured
- Dependency health check: `.venv\Scripts\python.exe -m pip check`
- Local Windows packaging: `installer.bat` (installs PyInstaller, builds, and copies runtime assets)
- Local POSIX packaging: `bash installer.sh` (requires `.venv`; installs PyInstaller and builds)

## 2. Operational Boundaries

### Always Do

- Run commands from the repository root; configuration and assets are loaded through relative paths.
- Inspect neighboring code and reuse existing provider, configuration, localization, and output-file patterns.
- For bug fixes, reproduce the issue with the smallest available read-only check or focused test before changing code.
- Keep the diff limited to files required by the task and run the narrowest relevant validation afterward.
- Preserve user video files; generated transcriptions are written beside inputs or under a selected timestamped output folder.

### Ask First

- Add, remove, or upgrade dependencies in `requirements.txt`.
- Change public UI behavior, provider endpoints, persistent output naming, or release artifacts.
- Modify GitHub Actions permissions, release triggers, signing, or authentication behavior.
- Rename or delete shared modules, configuration files, or runtime assets.

### Never Do

- Never commit `.env`, API keys, `secrets/`, tokens, credentials, or private configuration.
- Never delete or weaken checks, tests, or error handling to make validation pass.
- Never manually edit generated `build/`, `dist/`, `__pycache__/`, `temp_frames/`, logs, or packaged outputs.
- Never run mass formatting or unrelated refactors.

## 3. Repository-Specific Constraints

- Use Python with `pip` and `requirements.txt`; no lockfile or alternate package-manager workflow is configured.
- `settings/default.yaml` and `settings/locales.yaml` are runtime inputs; do not move or rename them without updating the loaders.
- Local vision processing requires `ffmpeg` and `ffprobe` available on `PATH`; Ollama defaults to `127.0.0.1:11434` and LM Studio to `127.0.0.1:1234`.
- Gemini access uses `GEMINI_API_KEY` from `.env` or `secrets/gemini.yaml`; keep both locations out of commits.
- PyInstaller uses `app_main.py`, `video_analyzer.spec`, `logo.ico`, `hooks/`, and `runtime_hook.py`; preserve the generated `dist/VideoAnalyzer` layout.
- `temp_frames/` is disposable processing state and is removed/recreated during frame extraction; do not store source data there.

## CI, Docker, and Release

- No Dockerfile, Compose file, devcontainer, or container command is configured.
- GitHub Actions has only a release workflow; it runs on tags matching `v*`, uses Python 3.11, installs requirements plus PyInstaller, and runs `pyinstaller --noconfirm video_analyzer.spec`.
- CI release targets Windows, macOS, and Linux; Linux additionally installs native GTK/WebKit build dependencies and `ffmpeg`.
- Release archives are `VideoAnalyzer-{platform}-{tag}.zip` on Windows/macOS and `.tar.gz` on Linux, each accompanied by a SHA256 file and uploaded with `CHANGELOG.md`.

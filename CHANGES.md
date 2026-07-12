# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-07-13
### Added
- **OpenRouter Support**: Added full support for online LLMs via OpenRouter (e.g. `google/gemma-4-26b-a4b-it:free`), allowing the bot to run without a local Ollama instance and saving ~5GB of disk space.
- **Environment Variable Security**: Added manual `.env` file loading and config interpolation to prevent accidental credential leaks.
- **Git Protection**: Added `.gitignore` to protect `.env`, browser cache profiles, local transcript logs, and temporary debug files from git.
- **Dynamic Audio Monitor Loopback**: Restored host system loopback routing to automatically capture host audios (e.g., Spotify, browser songs, meetings) without manual PulseAudio routing.

### Fixed
- **Whisper Lag & Backlog Queue**: Refactored the transcription worker to download the model in a background thread and drop audio chunks recorded during the loading phase. This prevents audio backups and stops live transcripts from arriving late on the dashboard.
- **CUDA Library Dependency**: Restricted WhisperModel to `device="cpu"` and `compute_type="int8"` inside Docker to resolve the missing `libcublas.so.12` error since the container lacks full CUDA drivers.
- **CI Validation**: Expanded syntax validation in `.github/workflows/ci.yml` to recursively compile and check all subfolders (`sensors/`, `workers/`, `web/`, etc.).

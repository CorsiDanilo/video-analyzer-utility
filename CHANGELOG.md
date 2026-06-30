# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-06-30

### Added

- **AI Assistant Response Language Selector**: Added a language radio button (`Italiano` / `English`, default: `Italiano`) inside the 🤖 AI Assistant (Post-Processing) section. The selected language controls the language in which the LLM (Gemini, Ollama, LM Studio) is instructed to reply, independently from the UI display language.
- English system prompt variants (`SYSTEM_PROMPT_EN`, `SYSTEM_PROMPT_FIX_TEXT_EN`) added to `src/llm_vision.py`.
- `response_language` parameter added to `query_gemini`, `query_ollama`, and `query_lmstudio` in `src/llm_vision.py`.
- Locale key `response_language_label` added (English + Italian) to `settings/locales.yaml`.

## [1.1.0] - 2026-06-29


### Added

- **Local Model Readiness Polling**: Added readiness verification for Ollama and LM Studio. The system polls the respective local endpoints (`/api/ps` for Ollama and `/v1/models` for LM Studio) every 2s for up to 60s before executing vision AI tasks or assistant queries.
- **Dynamic LM Studio Model Loading**: Added automatic model loading triggers calling `/api/v1/models/load` (with `/v1/models/load` fallback) to dynamically load LM Studio models on request.
- **Progress Indicators**: Integrated UI status messages (e.g., `⏳ checking model status...`, `⏳ model loading...`, `⏳ sending request...`) to improve visibility of background operations.
- **Ollama Timeout**: Increased Ollama API connection/read timeout to 120s to prevent failures during dynamic loading.
- **Localized Status Strings**: Added new keys for all status indicators to `settings/locales.yaml` in English and Italian.

## [1.0.1] - 2026-06-25
### Added
- **Fix Text** preset button (✏️ Correggi Testo) added to the AI Assistant section.
- When Fix Text is selected and a query is submitted to the LLM, a dedicated `SYSTEM_PROMPT_FIX_TEXT` instructs the model to use **all available tokens** to maximise output and return the full corrected text without omissions or truncation.
- `SYSTEM_PROMPT_FIX_TEXT` constant added to `src/llm_vision.py`.
- `fix_text=False` parameter added to `query_ollama`, `query_lmstudio`, and `query_gemini` in `src/llm_vision.py`.
- `fix_text_mode` Gradio state added to the UI; automatically set to `True` when Fix Text is clicked and reset to `False` on other presets or field reset.
- Locale keys `preset_fix` and `preset_fix_val` added (English + Italian) to `settings/locales.yaml`.

## [1.0.0] - 2026-06-21
### Added
- Reorganized localization and configurations directory structure.
- Created multi-platform GitHub Action release pipeline.
- Added `build_windows.sh` script for compilation.

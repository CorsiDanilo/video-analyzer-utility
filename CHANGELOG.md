# Changelog

All notable changes to this project will be documented in this file.

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

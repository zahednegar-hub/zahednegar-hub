# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-31

### Added

- `Fanoos` agent that streams reviews from the xAI Responses API (`https://api.x.ai/v1`) with
  the `web_search` and `x_search` Agent Tools enabled on every request.
- The validated Fanoos persona embedded verbatim in `fanoos/system_prompt.py`.
- `Review` dataclass and a parser that reads the model's JSON summary and falls back to its
  Markdown sections.
- Portfolio input from a URL (page text pre-fetched) or a local PDF.
- `fanoos review` CLI: streamed bilingual report with right-aligned Persian, scorecard, `--json`,
  `--raw`, `--no-stream`, `--lang`, `--focus`, `--model`, `--no-fetch` and `--bidi`.
- Clear error messages and exit codes for a missing or rejected API key, network failures,
  rate limits (429), other API errors, malformed output and unreadable input.
- Offline pytest suite and GitHub Actions CI on Linux, macOS and Windows with Python 3.10 and 3.12.

[Unreleased]: https://github.com/zahednegar-hub/fanoos/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zahednegar-hub/fanoos/releases/tag/v0.1.0

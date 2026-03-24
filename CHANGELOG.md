# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [0.1.1] - 2026-03-24

### Changed

- README: document full `config.yaml` shape (all keys, comments, and library example loading YAML).

## [0.1.0] - 2025-03-24

### Added

- `SmartCompactor` with hybrid parsing: regex → key-value fallback → raw pass-through.
- YAML-driven config: `dedup_window_seconds`, `error_threshold`, `aliases`, `level_overrides`, `log_pattern`, `output_template`.
- CLI `logcompact stream` reading stdin (pipe-friendly).
- Time-window deduplication, ERROR → CRITICAL escalation, level overrides (e.g. HTTP 5xx).
- Alias conflict handling (conflicting keys pass through as raw lines).
- Ordered emission of compacted groups by earliest timestamp / stream sequence.
- GPL-3.0-only license.

[Unreleased]: https://github.com/NikhilBudaniya/log-compactor/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/NikhilBudaniya/log-compactor/releases/tag/v0.1.1
[0.1.0]: https://github.com/NikhilBudaniya/log-compactor/releases/tag/v0.1.0

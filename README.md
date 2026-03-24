# Log Compactor

A real-time, configurable log deduplication and compaction utility. It supports dynamic regex parsing, key-value extraction, raw pass-through for unstructured lines, time-window deduplication, and error escalation.

## Installation

From the project root (development):

```bash
pip install -e ".[dev]"
```

Or install the package only:

```bash
pip install -e .
```

The `dev` extra includes pytest.

## Pipe any command’s output

Install the package, add a `config.yaml` (or pass `--config`), and pipe stdout through the CLI:

```bash
pytest -q 2>&1 | logcompact stream -c /path/to/config.yaml
```

```bash
python app.py 2>&1 | logcompact stream
```

If you omit `-c`, the CLI looks for `config.yaml` in the current working directory.

## Configuration (`config.yaml`)

The CLI loads a YAML file into the same structure `SmartCompactor` expects as a dict. Example:

```yaml
# Seconds: identical structured lines (same level + fields) within this span are compacted together.
dedup_window_seconds: 5

# If the level is ERROR and the same message repeats at least this many times in one group, output shows CRITICAL.
error_threshold: 2

# Optional. Named groups must include ts and level; other groups become fields. If no match, key=value parsing is tried.
log_pattern: '^(?P<ts>\S+)\s+(?P<level>\S+)\s+(?P<action>login|logout|upload)\s+(?P<user>\S+)$'

# {ts} is the formatted time range, {level} the level, {fields} sorted key=value; extra {field_name} come from captured fields.
output_template: "{ts} [{level}] {fields}"

# Rename keys (e.g. user_id -> user). If both old and new keys exist with different values, the line is passed through unchanged.
aliases:
  user_id: "user"

# If field value parses as an integer in [min, max], replace the log level with new_level (e.g. HTTP 5xx -> ERROR).
level_overrides:
  - field: "code"
    min: 500
    max: 599
    new_level: "ERROR"
```

A copy of this example lives in [`config.yaml`](config.yaml) at the repo root.

## Library usage

```python
import yaml
from compactor import SmartCompactor

with open("config.yaml") as f:
    settings = yaml.safe_load(f)
compactor = SmartCompactor(settings)
for line in compactor.compact_stream(open("app.log")):
    print(line)
```

You can also pass the same keys as a plain dict (no file) for quick experiments.

## Tests

```bash
pytest
```

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for version history and release notes.

## License

This project is licensed under the [GNU General Public License v3.0 only](https://www.gnu.org/licenses/gpl-3.0.html). See the [`LICENSE`](LICENSE) file for the full license text.

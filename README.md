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

## Library usage

```python
from compactor import SmartCompactor

settings = {"dedup_window_seconds": 5, "error_threshold": 2}
compactor = SmartCompactor(settings)
for line in compactor.compact_stream(open("app.log")):
    print(line)
```

## Tests

```bash
pytest
```

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for version history and release notes.

## License

This project is licensed under the [GNU General Public License v3.0 only](https://www.gnu.org/licenses/gpl-3.0.html). See the [`LICENSE`](LICENSE) file for the full license text.

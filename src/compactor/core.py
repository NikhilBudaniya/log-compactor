import heapq
import re
from datetime import datetime
from typing import Any, Dict, Generator, Tuple, Union

from pydantic import BaseModel, ValidationError


class LogEntry(BaseModel):
    ts: datetime
    level: str
    fields: Dict[str, str]


class SafeDict(dict):
    """Prevents KeyError if a template variable is missing from the log."""

    def __missing__(self, key):
        return f"{{{key}}}"


Signature = Tuple[str, Tuple[Tuple[str, str], ...]]


class SmartCompactor:
    def __init__(self, settings: dict):
        self.window = settings.get("dedup_window_seconds", 5)
        self.error_threshold = settings.get("error_threshold", 2)
        self.aliases = settings.get("aliases", {})
        self.overrides = settings.get("level_overrides", [])
        self.output_template = settings.get("output_template", "{ts} {level} {fields}")

        pattern_str = settings.get("log_pattern")
        self.pattern = re.compile(pattern_str) if pattern_str else None

    def _parse_and_enrich(self, line: str) -> Union[LogEntry, str]:
        line_stripped = line.strip()
        if not line_stripped:
            return line_stripped

        ts_raw, level = None, None
        fields: Dict[str, str] = {}
        matched_regex = False

        # 1. Try Regex Pattern (Dynamic parsing)
        if self.pattern:
            match = self.pattern.match(line_stripped)
            if match:
                data = match.groupdict()
                if "ts" in data and "level" in data:
                    ts_raw = data.pop("ts")
                    level = data.pop("level")
                    fields = data
                    matched_regex = True

        # 2. Try Key-Value Fallback
        if not matched_regex:
            parts = line_stripped.split()
            if len(parts) >= 2:
                ts_raw = parts[0]
                level = parts[1]
                for f in parts[2:]:
                    if "=" in f:
                        k, v = f.split("=", 1)
                        fields[k] = v

        # Apply Aliases and Overrides
        if ts_raw and level:
            for old_key, new_key in self.aliases.items():
                if old_key in fields and new_key in fields and fields[old_key] != fields[new_key]:
                    return line_stripped

            for old_key, new_key in self.aliases.items():
                if old_key in fields:
                    fields[new_key] = fields.pop(old_key)

            for override in self.overrides:
                if override["field"] in fields:
                    try:
                        val = int(fields[override["field"]])
                        if override["min"] <= val <= override["max"]:
                            level = override["new_level"]
                    except ValueError:
                        pass
            try:
                return LogEntry(ts=ts_raw, level=level, fields=fields)
            except ValidationError:
                pass

        # 3. Raw Pass-Through
        return line_stripped

    def _generate_signature(self, entry: LogEntry) -> Signature:
        field_key = tuple(sorted(entry.fields.items()))
        return (entry.level, field_key)

    def _flush_expired_groups(
        self, groups: Dict, pending: list, current_ts: datetime
    ) -> Generator[str, None, None]:
        """Emit groups older than dedup_window_seconds (no duplicates seen in that time)."""
        expired_sigs = []
        for sig, group in groups.items():
            age = (current_ts - group["start_ts"]).total_seconds()
            if age > self.window:
                expired_sigs.append(sig)

        for sig in expired_sigs:
            g = groups.pop(sig)
            heapq.heappush(pending, (g["start_ts"], g["seq"], g))

        yield from self._emit_ready_groups(pending, groups)

    def _emit_ready_groups(
        self, pending: list, groups: Dict[Signature, Any]
    ) -> Generator[str, None, None]:
        def open_min_key():
            if not groups:
                return None
            return min((g["start_ts"], g["seq"]) for g in groups.values())

        while pending:
            ts, s, grp = pending[0]
            om = open_min_key()
            if om is None:
                heapq.heappop(pending)
                yield self._format_group(grp)
                continue
            if (ts, s) < om:
                heapq.heappop(pending)
                yield self._format_group(grp)
            else:
                break

    def compact_stream(self, log_stream) -> Generator[str, None, None]:
        groups: Dict[Signature, Any] = {}
        pending: list = []
        line_seq = 0

        for line in log_stream:
            line_seq += 1
            entry = self._parse_and_enrich(line)

            if isinstance(entry, str):
                yield from self._emit_ready_groups(pending, groups)
                yield entry
                continue

            # Check if any groups have expired (no duplicates in dedup_window_seconds)
            yield from self._flush_expired_groups(groups, pending, entry.ts)

            sig = self._generate_signature(entry)

            if sig in groups:
                time_diff = (entry.ts - groups[sig]["start_ts"]).total_seconds()
                if time_diff > self.window:
                    g = groups.pop(sig)
                    heapq.heappush(pending, (g["start_ts"], g["seq"], g))
                    yield from self._emit_ready_groups(pending, groups)

            if sig not in groups:
                groups[sig] = {
                    "start_ts": entry.ts,
                    "last_ts": entry.ts,
                    "level": entry.level,
                    "fields": entry.fields,
                    "count": 1,
                    "seq": line_seq,
                }
            else:
                groups[sig]["last_ts"] = entry.ts
                groups[sig]["count"] += 1

        for g in groups.values():
            heapq.heappush(pending, (g["start_ts"], g["seq"], g))
        groups.clear()
        yield from self._emit_ready_groups(pending, groups)

    def _format_group(self, group: dict) -> str:
        start, end = group["start_ts"], group["last_ts"]
        level = group["level"]

        if level == "ERROR" and group["count"] >= self.error_threshold:
            level = "CRITICAL"

        ts_str = start.isoformat()
        if group["count"] > 1:
            if start.date() == end.date():
                ts_str += f"~{end.strftime('%H:%M:%S')}"
            else:
                ts_str += f"~{end.isoformat()}"

        count_str = f" (x{group['count']})" if group["count"] > 1 else ""

        format_kwargs = SafeDict(
            ts=ts_str,
            level=level,
            fields=" ".join(f"{k}={v}" for k, v in sorted(group["fields"].items())),
        )
        format_kwargs.update(group["fields"])

        formatted_line = self.output_template.format_map(format_kwargs)
        return f"{formatted_line}{count_str}".strip()

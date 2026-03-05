from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from code_insights.language_stats import count_total_lines, detect_language, extract_code_lines
from code_insights.scanner import collect_source_files


@dataclass(frozen=True)
class MonitorSettings:
    profile: str = "balanced"
    rhythm_window_seconds: int = 300
    rhythm_bucket_seconds: int = 5
    recent_changes_window_seconds: int = 5
    burst_history_limit: int = 8
    hotspot_view_limit: int = 6
    hotspot_dir_cap: int = 64
    alert_file_churn_threshold: int = 12
    alert_removed_lines_threshold: int = 80
    alert_single_file_delta_threshold: int = 120


def build_monitor_settings(profile: str = "balanced") -> MonitorSettings:
    normalized = profile.strip().lower()
    if normalized == "agent":
        return MonitorSettings(
            profile="agent",
            burst_history_limit=10,
            hotspot_view_limit=8,
            hotspot_dir_cap=96,
            alert_file_churn_threshold=20,
            alert_removed_lines_threshold=160,
            alert_single_file_delta_threshold=220,
        )
    return MonitorSettings(profile="balanced")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_metric_totals() -> dict[str, int]:
    return {
        "added_lines": 0,
        "removed_lines": 0,
    }


def _empty_diff() -> dict[str, object]:
    return {
        "total": _empty_metric_totals(),
        "effective": _empty_metric_totals(),
        "files_added": 0,
        "files_removed": 0,
        "files_modified": 0,
        "files_changed": 0,
        "changes": [],
        "scan_errors": 0,
    }


def _empty_radar() -> dict[str, object]:
    return {
        "rhythm": [0],
        "bursts": [],
        "active_burst": None,
        "hotspots": [],
        "alerts": [],
        "recent_changes": [],
        "recent_window_seconds": 5,
    }


def _snapshot_entry(
    *,
    mtime_ns: int,
    size: int,
    total_lines: int,
    effective_lines: int,
    total_signature: list[int],
    effective_signature: list[int],
) -> dict[str, object]:
    return {
        "mtime_ns": int(mtime_ns),
        "size": int(size),
        "total_lines": int(total_lines),
        "effective_lines": int(effective_lines),
        "total_signature": list(total_signature),
        "effective_signature": list(effective_signature),
    }


def _signature_seq(lines: list[str]) -> list[int]:
    return [hash(line) for line in lines]


def _read_file_metrics(path: Path) -> dict[str, object] | None:
    language = detect_language(path.suffix)
    if language is None:
        return None

    text = path.read_bytes().decode("utf-8", errors="ignore")
    total_line_values = text.splitlines()
    effective_line_values = extract_code_lines(language, text)
    total_lines = count_total_lines(text)
    effective_lines = len(effective_line_values)
    return {
        "total_lines": total_lines,
        "effective_lines": effective_lines,
        "total_signature": _signature_seq(total_line_values),
        "effective_signature": _signature_seq(effective_line_values),
    }


def _sequence_added_removed(previous: list[int], current: list[int]) -> tuple[int, int]:
    matcher = SequenceMatcher(a=previous, b=current, autojunk=False)
    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            removed += i2 - i1
            added += j2 - j1
    return added, removed


def _add_metric_delta(diff: dict[str, object], metric: str, delta: int) -> None:
    metric_totals = diff.get(metric)
    if not isinstance(metric_totals, dict):
        return
    if delta > 0:
        metric_totals["added_lines"] = int(metric_totals.get("added_lines", 0)) + delta
    elif delta < 0:
        metric_totals["removed_lines"] = int(metric_totals.get("removed_lines", 0)) + (-delta)


def _abs_change_score(row: dict[str, object]) -> tuple[int, str]:
    added_total = int(row.get("added_total", 0) or 0)
    removed_total = int(row.get("removed_total", 0) or 0)
    added_effective = int(row.get("added_effective", 0) or 0)
    removed_effective = int(row.get("removed_effective", 0) or 0)
    churn = max(added_total + removed_total, added_effective + removed_effective)
    return churn, str(row.get("path", ""))


def _dir_from_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) <= 1:
        return "."
    return parts[0]


def _metric_totals(diff: dict[str, object], key: str) -> tuple[int, int]:
    value = diff.get(key)
    metrics = value if isinstance(value, dict) else {}
    return int(metrics.get("added_lines", 0)), int(metrics.get("removed_lines", 0))


def build_line_diff(
    previous: dict[str, dict[str, object]],
    current: dict[str, dict[str, object]],
    *,
    change_limit: int = 8,
) -> dict[str, object]:
    diff = _empty_diff()
    changes: list[dict[str, object]] = []

    previous_keys = set(previous)
    current_keys = set(current)

    for path in sorted(current_keys - previous_keys):
        current_row = current[path]
        added_total = int(current_row.get("total_lines", 0))
        removed_total = 0
        added_effective = int(current_row.get("effective_lines", 0))
        removed_effective = 0
        delta_total = added_total
        delta_effective = added_effective

        diff["files_added"] = int(diff["files_added"]) + 1
        _add_metric_delta(diff, "total", added_total)
        _add_metric_delta(diff, "effective", added_effective)
        changes.append(
            {
                "path": path,
                "delta_total": delta_total,
                "delta_effective": delta_effective,
                "added_total": added_total,
                "removed_total": removed_total,
                "added_effective": added_effective,
                "removed_effective": removed_effective,
                "kind": "added",
            }
        )

    for path in sorted(previous_keys - current_keys):
        previous_row = previous[path]
        added_total = 0
        removed_total = int(previous_row.get("total_lines", 0))
        added_effective = 0
        removed_effective = int(previous_row.get("effective_lines", 0))
        delta_total = -removed_total
        delta_effective = -removed_effective

        diff["files_removed"] = int(diff["files_removed"]) + 1
        _add_metric_delta(diff, "total", -removed_total)
        _add_metric_delta(diff, "effective", -removed_effective)
        changes.append(
            {
                "path": path,
                "delta_total": delta_total,
                "delta_effective": delta_effective,
                "added_total": added_total,
                "removed_total": removed_total,
                "added_effective": added_effective,
                "removed_effective": removed_effective,
                "kind": "removed",
            }
        )

    for path in sorted(previous_keys & current_keys):
        previous_row = previous[path]
        current_row = current[path]

        previous_total = int(previous_row.get("total_lines", 0))
        current_total = int(current_row.get("total_lines", 0))
        previous_effective = int(previous_row.get("effective_lines", 0))
        current_effective = int(current_row.get("effective_lines", 0))

        previous_total_signature = previous_row.get("total_signature", [])
        previous_total_seq = previous_total_signature if isinstance(previous_total_signature, list) else []
        current_total_signature = current_row.get("total_signature", [])
        current_total_seq = current_total_signature if isinstance(current_total_signature, list) else []
        previous_effective_signature = previous_row.get("effective_signature", [])
        previous_effective_seq = (
            previous_effective_signature if isinstance(previous_effective_signature, list) else []
        )
        current_effective_signature = current_row.get("effective_signature", [])
        current_effective_seq = current_effective_signature if isinstance(current_effective_signature, list) else []

        if previous_total_seq and current_total_seq:
            added_total, removed_total = _sequence_added_removed(previous_total_seq, current_total_seq)
        else:
            raw_delta_total = current_total - previous_total
            added_total = max(0, raw_delta_total)
            removed_total = max(0, -raw_delta_total)

        if previous_effective_seq and current_effective_seq:
            added_effective, removed_effective = _sequence_added_removed(
                previous_effective_seq,
                current_effective_seq,
            )
        else:
            raw_delta_effective = current_effective - previous_effective
            added_effective = max(0, raw_delta_effective)
            removed_effective = max(0, -raw_delta_effective)

        delta_total = added_total - removed_total
        delta_effective = added_effective - removed_effective

        if added_total == 0 and removed_total == 0 and added_effective == 0 and removed_effective == 0:
            continue

        diff["files_modified"] = int(diff["files_modified"]) + 1
        _add_metric_delta(diff, "total", added_total)
        _add_metric_delta(diff, "total", -removed_total)
        _add_metric_delta(diff, "effective", added_effective)
        _add_metric_delta(diff, "effective", -removed_effective)
        changes.append(
            {
                "path": path,
                "delta_total": delta_total,
                "delta_effective": delta_effective,
                "added_total": added_total,
                "removed_total": removed_total,
                "added_effective": added_effective,
                "removed_effective": removed_effective,
                "kind": "modified",
            }
        )

    diff["files_changed"] = (
        int(diff["files_added"]) + int(diff["files_removed"]) + int(diff["files_modified"])
    )

    ranked = sorted(changes, key=lambda row: (-_abs_change_score(row)[0], _abs_change_score(row)[1]))
    diff["changes"] = ranked[:change_limit]
    return diff


def build_static_monitor_state(
    *,
    tracked_files: int,
    interval_seconds: int = 3,
    last_scan_at: str | None = None,
    profile: str = "balanced",
) -> dict[str, object]:
    return {
        "enabled": False,
        "status": "idle",
        "interval_seconds": interval_seconds,
        "last_scan_at": last_scan_at or _now_iso(),
        "tracked_files": tracked_files,
        "profile": profile,
        "interval": _empty_diff(),
        "cumulative": _empty_diff(),
        "radar": _empty_radar(),
    }


class FileChangeMonitor:
    def __init__(
        self,
        repo_path: Path,
        *,
        exclude_patterns: list[str] | None = None,
        interval_seconds: int = 3,
        settings: MonitorSettings | None = None,
    ) -> None:
        self._repo_path = repo_path
        self._exclude_patterns = exclude_patterns or []
        self._interval_seconds = interval_seconds
        self._settings = settings or build_monitor_settings("balanced")
        self._previous_snapshot: dict[str, dict[str, object]] | None = None
        self._cumulative = _empty_diff()

        self._rhythm_net_events: list[tuple[float, int]] = []
        self._recent_change_events: list[dict[str, object]] = []
        self._recent_bursts: list[dict[str, object]] = []
        self._active_burst: dict[str, object] | None = None
        self._hotspot_totals: dict[str, dict[str, int]] = {}

    def initialize(self) -> dict[str, object]:
        snapshot, scan_errors = self._scan_snapshot(previous_snapshot=None)
        self._previous_snapshot = snapshot
        self._cumulative = _empty_diff()
        self._reset_radar_runtime()

        interval = _empty_diff()
        interval["scan_errors"] = scan_errors
        cycle_at = _now_iso()
        cycle_ts = datetime.now(timezone.utc).timestamp()
        radar = self._update_radar(interval, cycle_at=cycle_at, cycle_ts=cycle_ts)
        return self._build_state(snapshot=snapshot, interval=interval, radar=radar)

    def poll(self) -> dict[str, object]:
        snapshot, scan_errors = self._scan_snapshot(previous_snapshot=self._previous_snapshot)

        if self._previous_snapshot is None:
            interval = _empty_diff()
        else:
            interval = build_line_diff(
                self._previous_snapshot,
                snapshot,
            )
            self._accumulate(interval)

        interval["scan_errors"] = scan_errors
        cycle_at = _now_iso()
        cycle_ts = datetime.now(timezone.utc).timestamp()
        radar = self._update_radar(interval, cycle_at=cycle_at, cycle_ts=cycle_ts)

        self._previous_snapshot = snapshot
        return self._build_state(snapshot=snapshot, interval=interval, radar=radar)

    def _scan_snapshot(
        self,
        *,
        previous_snapshot: dict[str, dict[str, object]] | None,
    ) -> tuple[dict[str, dict[str, object]], int]:
        current_snapshot: dict[str, dict[str, object]] = {}
        scan_errors = 0

        for path in collect_source_files(self._repo_path, self._exclude_patterns):
            rel_path = path.relative_to(self._repo_path).as_posix()
            previous_entry = previous_snapshot.get(rel_path) if previous_snapshot else None

            try:
                stat = path.stat()
            except OSError:
                scan_errors += 1
                if previous_entry:
                    current_snapshot[rel_path] = dict(previous_entry)
                continue

            mtime_ns = int(stat.st_mtime_ns)
            size = int(stat.st_size)
            if previous_entry and mtime_ns == int(previous_entry.get("mtime_ns", -1)) and size == int(
                previous_entry.get("size", -1)
            ):
                current_snapshot[rel_path] = dict(previous_entry)
                continue

            try:
                metrics = _read_file_metrics(path)
            except OSError:
                scan_errors += 1
                if previous_entry:
                    current_snapshot[rel_path] = dict(previous_entry)
                continue

            if metrics is None:
                continue

            total_lines = int(metrics.get("total_lines", 0))
            effective_lines = int(metrics.get("effective_lines", 0))
            total_signature = metrics.get("total_signature", [])
            total_signature_values = total_signature if isinstance(total_signature, list) else []
            effective_signature = metrics.get("effective_signature", [])
            effective_signature_values = (
                effective_signature if isinstance(effective_signature, list) else []
            )
            current_snapshot[rel_path] = _snapshot_entry(
                mtime_ns=mtime_ns,
                size=size,
                total_lines=total_lines,
                effective_lines=effective_lines,
                total_signature=total_signature_values,
                effective_signature=effective_signature_values,
            )

        return current_snapshot, scan_errors

    def _accumulate(self, interval: dict[str, object]) -> None:
        for metric in ("total", "effective"):
            cumulative_metric = self._cumulative.get(metric)
            interval_metric = interval.get(metric)
            if not isinstance(cumulative_metric, dict) or not isinstance(interval_metric, dict):
                continue
            cumulative_metric["added_lines"] = int(cumulative_metric.get("added_lines", 0)) + int(
                interval_metric.get("added_lines", 0)
            )
            cumulative_metric["removed_lines"] = int(cumulative_metric.get("removed_lines", 0)) + int(
                interval_metric.get("removed_lines", 0)
            )

        self._cumulative["files_added"] = int(self._cumulative["files_added"]) + int(interval["files_added"])
        self._cumulative["files_removed"] = int(self._cumulative["files_removed"]) + int(interval["files_removed"])
        self._cumulative["files_modified"] = int(self._cumulative["files_modified"]) + int(interval["files_modified"])
        self._cumulative["files_changed"] = int(self._cumulative["files_changed"]) + int(interval["files_changed"])
        self._cumulative["scan_errors"] = int(self._cumulative.get("scan_errors", 0)) + int(
            interval.get("scan_errors", 0)
        )
        self._cumulative["changes"] = list(interval.get("changes", []))

    def _reset_radar_runtime(self) -> None:
        self._rhythm_net_events = []
        self._recent_change_events = []
        self._recent_bursts = []
        self._active_burst = None
        self._hotspot_totals = {}

    def _update_radar(
        self,
        interval: dict[str, object],
        *,
        cycle_at: str,
        cycle_ts: float,
    ) -> dict[str, object]:
        self._record_rhythm_net(interval, cycle_ts)
        self._record_recent_changes(interval, cycle_at=cycle_at, cycle_ts=cycle_ts)
        self._update_bursts(interval, cycle_at=cycle_at)
        self._update_hotspots(interval)
        alerts = self._build_alerts(interval)

        active_burst = dict(self._active_burst) if self._active_burst else None
        bursts = [dict(item) for item in self._recent_bursts[: self._settings.burst_history_limit]]
        hotspots = self._hotspot_view()

        return {
            "rhythm": self._build_rhythm_series(cycle_ts),
            "bursts": bursts,
            "active_burst": active_burst,
            "hotspots": hotspots,
            "alerts": alerts,
            "recent_changes": self._build_recent_changes_view(),
            "recent_window_seconds": self._settings.recent_changes_window_seconds,
        }

    def _record_rhythm_net(self, interval: dict[str, object], cycle_ts: float) -> None:
        added, removed = _metric_totals(interval, "total")
        net = int(added - removed)
        self._rhythm_net_events.append((cycle_ts, net))

        min_ts = cycle_ts - float(self._settings.rhythm_window_seconds)
        self._rhythm_net_events = [row for row in self._rhythm_net_events if float(row[0]) >= min_ts]

    def _build_rhythm_series(self, cycle_ts: float) -> list[int]:
        bucket_seconds = max(1, int(self._settings.rhythm_bucket_seconds))
        window_seconds = max(bucket_seconds, int(self._settings.rhythm_window_seconds))
        bucket_count = max(1, window_seconds // bucket_seconds)
        series = [0] * bucket_count

        min_ts = cycle_ts - float(window_seconds)
        for ts, net in self._rhythm_net_events:
            if ts < min_ts:
                continue
            age = cycle_ts - ts
            if age < 0:
                continue
            idx_from_end = int(age // bucket_seconds)
            if idx_from_end >= bucket_count:
                continue
            series[bucket_count - 1 - idx_from_end] += int(net)

        return series

    def _record_recent_changes(self, interval: dict[str, object], *, cycle_at: str, cycle_ts: float) -> None:
        changes = interval.get("changes", [])
        changes_list = changes if isinstance(changes, list) else []

        for change in changes_list:
            if not isinstance(change, dict):
                continue
            self._recent_change_events.append(
                {
                    "at": cycle_at,
                    "ts": cycle_ts,
                    "path": str(change.get("path", "-")),
                    "delta_total": int(change.get("delta_total", 0) or 0),
                    "delta_effective": int(change.get("delta_effective", 0) or 0),
                    "added_total": int(change.get("added_total", 0) or 0),
                    "removed_total": int(change.get("removed_total", 0) or 0),
                    "added_effective": int(change.get("added_effective", 0) or 0),
                    "removed_effective": int(change.get("removed_effective", 0) or 0),
                    "kind": str(change.get("kind", "-")),
                }
            )

        min_ts = cycle_ts - float(self._settings.recent_changes_window_seconds)
        self._recent_change_events = [
            row for row in self._recent_change_events if float(row.get("ts", 0.0)) >= min_ts
        ]

    def _build_recent_changes_view(self) -> list[dict[str, object]]:
        view: list[dict[str, object]] = []
        for row in sorted(self._recent_change_events, key=lambda item: float(item.get("ts", 0.0)), reverse=True):
            view.append(
                {
                    "at": str(row.get("at", "")),
                    "path": str(row.get("path", "-")),
                    "delta_total": int(row.get("delta_total", 0) or 0),
                    "delta_effective": int(row.get("delta_effective", 0) or 0),
                    "added_total": int(row.get("added_total", 0) or 0),
                    "removed_total": int(row.get("removed_total", 0) or 0),
                    "added_effective": int(row.get("added_effective", 0) or 0),
                    "removed_effective": int(row.get("removed_effective", 0) or 0),
                    "kind": str(row.get("kind", "-")),
                }
            )
        return view

    def _new_burst(self, *, cycle_at: str) -> dict[str, object]:
        return {
            "started_at": cycle_at,
            "last_at": cycle_at,
            "cycles": 0,
            "files_changed": 0,
            "total_added": 0,
            "total_removed": 0,
            "effective_added": 0,
            "effective_removed": 0,
        }

    def _update_bursts(self, interval: dict[str, object], *, cycle_at: str) -> None:
        files_changed = int(interval.get("files_changed", 0) or 0)
        total_added, total_removed = _metric_totals(interval, "total")
        effective_added, effective_removed = _metric_totals(interval, "effective")

        if files_changed <= 0:
            if self._active_burst:
                self._recent_bursts.insert(0, dict(self._active_burst))
                self._recent_bursts = self._recent_bursts[: self._settings.burst_history_limit]
                self._active_burst = None
            return

        if self._active_burst is None:
            self._active_burst = self._new_burst(cycle_at=cycle_at)

        burst = self._active_burst
        burst["last_at"] = cycle_at
        burst["cycles"] = int(burst.get("cycles", 0)) + 1
        burst["files_changed"] = int(burst.get("files_changed", 0)) + files_changed
        burst["total_added"] = int(burst.get("total_added", 0)) + total_added
        burst["total_removed"] = int(burst.get("total_removed", 0)) + total_removed
        burst["effective_added"] = int(burst.get("effective_added", 0)) + effective_added
        burst["effective_removed"] = int(burst.get("effective_removed", 0)) + effective_removed

    def _update_hotspots(self, interval: dict[str, object]) -> None:
        changes = interval.get("changes", [])
        changes_list = changes if isinstance(changes, list) else []

        for change in changes_list:
            if not isinstance(change, dict):
                continue
            path = str(change.get("path", ""))
            if not path:
                continue
            directory = _dir_from_path(path)
            added_total = int(change.get("added_total", 0) or 0)
            removed_total = int(change.get("removed_total", 0) or 0)
            added_effective = int(change.get("added_effective", 0) or 0)
            removed_effective = int(change.get("removed_effective", 0) or 0)
            delta_total = added_total + removed_total
            delta_effective = added_effective + removed_effective

            row = self._hotspot_totals.setdefault(
                directory,
                {"touches": 0, "total_delta": 0, "effective_delta": 0},
            )
            row["touches"] = int(row.get("touches", 0)) + 1
            row["total_delta"] = int(row.get("total_delta", 0)) + delta_total
            row["effective_delta"] = int(row.get("effective_delta", 0)) + delta_effective

        self._trim_hotspots()

    def _trim_hotspots(self) -> None:
        if len(self._hotspot_totals) <= self._settings.hotspot_dir_cap:
            return

        ranked = sorted(
            self._hotspot_totals.items(),
            key=lambda item: (
                -(int(item[1].get("total_delta", 0)) + int(item[1].get("effective_delta", 0))),
                -int(item[1].get("touches", 0)),
                item[0],
            ),
        )
        self._hotspot_totals = dict(ranked[: self._settings.hotspot_dir_cap])

    def _hotspot_view(self) -> list[dict[str, object]]:
        ranked = sorted(
            self._hotspot_totals.items(),
            key=lambda item: (
                -(int(item[1].get("total_delta", 0)) + int(item[1].get("effective_delta", 0))),
                -int(item[1].get("touches", 0)),
                item[0],
            ),
        )

        view: list[dict[str, object]] = []
        for directory, row in ranked[: self._settings.hotspot_view_limit]:
            view.append(
                {
                    "dir": directory,
                    "touches": int(row.get("touches", 0)),
                    "total_delta": int(row.get("total_delta", 0)),
                    "effective_delta": int(row.get("effective_delta", 0)),
                }
            )
        return view

    def _build_alerts(self, interval: dict[str, object]) -> list[dict[str, str]]:
        alerts: list[dict[str, str]] = []

        files_changed = int(interval.get("files_changed", 0) or 0)
        scan_errors = int(interval.get("scan_errors", 0) or 0)
        _, total_removed = _metric_totals(interval, "total")

        if scan_errors > 0:
            alerts.append({"level": "warn", "message": f"Read errors detected: {scan_errors}"})

        if files_changed >= self._settings.alert_file_churn_threshold:
            alerts.append(
                {
                    "level": "warn",
                    "message": f"High file churn this cycle ({files_changed} files)",
                }
            )

        if total_removed >= self._settings.alert_removed_lines_threshold:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"Large deletion burst ({total_removed} lines removed)",
                }
            )

        max_single_delta = 0
        changes = interval.get("changes", [])
        changes_list = changes if isinstance(changes, list) else []
        for row in changes_list:
            if not isinstance(row, dict):
                continue
            delta_total = abs(int(row.get("delta_total", 0) or 0))
            delta_effective = abs(int(row.get("delta_effective", 0) or 0))
            max_single_delta = max(max_single_delta, delta_total, delta_effective)

        if max_single_delta >= self._settings.alert_single_file_delta_threshold:
            alerts.append(
                {
                    "level": "warn",
                    "message": f"Large single-file edit detected ({max_single_delta} lines)",
                }
            )

        if not alerts:
            alerts.append({"level": "ok", "message": "No active alerts"})

        return alerts

    def _build_state(
        self,
        *,
        snapshot: dict[str, dict[str, int]],
        interval: dict[str, object],
        radar: dict[str, object],
    ) -> dict[str, object]:
        return {
            "enabled": True,
            "status": "running",
            "interval_seconds": self._interval_seconds,
            "last_scan_at": _now_iso(),
            "tracked_files": len(snapshot),
            "profile": self._settings.profile,
            "interval": interval,
            "cumulative": dict(self._cumulative),
            "radar": radar,
        }

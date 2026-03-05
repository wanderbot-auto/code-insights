from pathlib import Path

import code_insights.monitor as monitor_module
from code_insights.monitor import FileChangeMonitor, build_line_diff, build_monitor_settings


def test_build_line_diff_tracks_added_removed_and_modified_lines() -> None:
    previous = {
        "a.py": {"total_lines": 3, "effective_lines": 2},
        "b.js": {"total_lines": 4, "effective_lines": 3},
        "keep.ts": {"total_lines": 5, "effective_lines": 5},
    }
    current = {
        "a.py": {"total_lines": 5, "effective_lines": 2},
        "c.ts": {"total_lines": 2, "effective_lines": 2},
        "keep.ts": {"total_lines": 2, "effective_lines": 1},
    }

    diff = build_line_diff(previous, current)

    assert diff["total"]["added_lines"] == 4
    assert diff["total"]["removed_lines"] == 7
    assert diff["effective"]["added_lines"] == 2
    assert diff["effective"]["removed_lines"] == 7
    assert diff["files_added"] == 1
    assert diff["files_removed"] == 1
    assert diff["files_modified"] == 2
    assert diff["files_changed"] == 4
    assert len(diff["changes"]) == 4


def test_build_line_diff_for_single_modified_file_tracks_add_and_remove_separately() -> None:
    previous = {
        "a.py": {
            "total_lines": 3,
            "effective_lines": 3,
            "total_signature": [11, 12, 13],
            "effective_signature": [21, 22, 23],
        }
    }
    current = {
        "a.py": {
            "total_lines": 4,
            "effective_lines": 4,
            "total_signature": [11, 99, 13, 14],
            "effective_signature": [21, 88, 23, 24],
        }
    }

    diff = build_line_diff(previous, current)

    assert diff["files_changed"] == 1
    assert diff["files_modified"] == 1
    assert diff["total"]["added_lines"] == 2
    assert diff["total"]["removed_lines"] == 1
    assert diff["effective"]["added_lines"] == 2
    assert diff["effective"]["removed_lines"] == 1
    assert len(diff["changes"]) == 1
    row = diff["changes"][0]
    assert row["added_total"] == 2
    assert row["removed_total"] == 1
    assert row["added_effective"] == 2
    assert row["removed_effective"] == 1


def test_file_change_monitor_initializes_and_polls(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "b.js").write_text("const x = 1;\n", encoding="utf-8")

    monitor = FileChangeMonitor(repo, interval_seconds=3)
    initial = monitor.initialize()

    assert initial["status"] == "running"
    assert initial["tracked_files"] == 2
    assert initial["interval"]["files_changed"] == 0
    assert "radar" in initial
    assert len(initial["radar"]["rhythm"]) >= 1
    assert initial["radar"]["recent_window_seconds"] == monitor_module.DEFAULT_RECENT_CHANGES_WINDOW_SECONDS
    assert initial["radar"]["recent_repeat_threshold"] == monitor_module.DEFAULT_RECENT_REPEAT_THRESHOLD

    (repo / "a.py").write_text("x = 1\n\ny = 2\n", encoding="utf-8")
    (repo / "b.js").unlink()
    (repo / "c.ts").write_text("const a = 1;\nconst b = 2;\n", encoding="utf-8")

    update = monitor.poll()
    assert update["tracked_files"] == 2
    assert update["interval"]["total"]["added_lines"] == 4
    assert update["interval"]["total"]["removed_lines"] == 1
    assert update["interval"]["effective"]["added_lines"] == 3
    assert update["interval"]["effective"]["removed_lines"] == 1
    assert update["interval"]["files_added"] == 1
    assert update["interval"]["files_removed"] == 1
    assert update["interval"]["files_modified"] == 1
    assert update["interval"]["files_changed"] == 3
    assert len(update["radar"]["rhythm"]) >= 2
    assert update["radar"]["active_burst"] is not None
    assert len(update["radar"]["hotspots"]) >= 1
    assert len(update["radar"]["alerts"]) >= 1
    assert len(update["radar"]["recent_changes"]) >= 1

    steady = monitor.poll()
    assert steady["interval"]["files_changed"] == 0
    assert steady["cumulative"]["total"]["added_lines"] == 4
    assert steady["cumulative"]["total"]["removed_lines"] == 1
    assert steady["cumulative"]["effective"]["added_lines"] == 3
    assert steady["cumulative"]["effective"]["removed_lines"] == 1
    assert steady["cumulative"]["files_changed"] == 3
    assert steady["radar"]["active_burst"] is None
    assert len(steady["radar"]["bursts"]) >= 1


def test_file_change_monitor_reuses_cached_metrics_for_unchanged_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")

    monitor = FileChangeMonitor(repo, interval_seconds=3)
    monitor.initialize()

    def _fail_on_read(_path: Path) -> None:
        raise AssertionError("unchanged file should reuse cached metrics")

    monkeypatch.setattr(monitor_module, "_read_file_metrics", _fail_on_read)
    update = monitor.poll()
    assert update["interval"]["files_changed"] == 0


def test_build_monitor_settings_agent_profile_is_less_sensitive() -> None:
    balanced = build_monitor_settings("balanced")
    agent = build_monitor_settings("agent")

    assert balanced.profile == "balanced"
    assert agent.profile == "agent"
    assert agent.alert_file_churn_threshold > balanced.alert_file_churn_threshold
    assert agent.alert_removed_lines_threshold > balanced.alert_removed_lines_threshold
    assert agent.alert_single_file_delta_threshold > balanced.alert_single_file_delta_threshold


def test_recent_changes_view_aggregates_repeat_count_by_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")

    monitor = FileChangeMonitor(repo, interval_seconds=3)
    monitor.initialize()
    monitor._recent_change_events = [  # type: ignore[attr-defined]
        {
            "at": "2026-01-01T00:00:03+00:00",
            "ts": 3.0,
            "path": "a.py",
            "delta_total": 1,
            "delta_effective": 1,
            "added_total": 1,
            "removed_total": 0,
            "added_effective": 1,
            "removed_effective": 0,
            "kind": "modified",
        },
        {
            "at": "2026-01-01T00:00:02+00:00",
            "ts": 2.0,
            "path": "b.py",
            "delta_total": 1,
            "delta_effective": 1,
            "added_total": 1,
            "removed_total": 0,
            "added_effective": 1,
            "removed_effective": 0,
            "kind": "added",
        },
        {
            "at": "2026-01-01T00:00:01+00:00",
            "ts": 1.0,
            "path": "a.py",
            "delta_total": 2,
            "delta_effective": 2,
            "added_total": 2,
            "removed_total": 0,
            "added_effective": 2,
            "removed_effective": 0,
            "kind": "modified",
        },
    ]
    monitor._recent_change_history = [  # type: ignore[attr-defined]
        {
            "at": "2026-01-01T00:00:03+00:00",
            "ts": 3.0,
            "path": "a.py",
            "delta_total": 1,
            "delta_effective": 1,
            "added_total": 1,
            "removed_total": 0,
            "added_effective": 1,
            "removed_effective": 0,
            "kind": "modified",
        },
        {
            "at": "2026-01-01T00:00:02+00:00",
            "ts": 2.0,
            "path": "b.py",
            "delta_total": 1,
            "delta_effective": 1,
            "added_total": 1,
            "removed_total": 0,
            "added_effective": 1,
            "removed_effective": 0,
            "kind": "added",
        },
    ]

    view = monitor._build_recent_changes_view()  # type: ignore[attr-defined]
    by_path = {str(item["path"]): item for item in view}
    assert by_path["a.py"]["repeat_count"] == 2
    assert by_path["b.py"]["repeat_count"] == 1


def test_recent_changes_view_keeps_recent_history_when_window_is_empty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")

    monitor = FileChangeMonitor(repo, interval_seconds=3)
    monitor.initialize()
    monitor._recent_change_events = []  # type: ignore[attr-defined]
    monitor._recent_change_history = [  # type: ignore[attr-defined]
        {
            "at": "2026-01-01T00:00:03+00:00",
            "ts": 3.0,
            "path": "a.py",
            "delta_total": 1,
            "delta_effective": 1,
            "added_total": 1,
            "removed_total": 0,
            "added_effective": 1,
            "removed_effective": 0,
            "kind": "modified",
        }
    ]

    view = monitor._build_recent_changes_view()  # type: ignore[attr-defined]
    assert len(view) == 1
    assert view[0]["path"] == "a.py"
    assert view[0]["repeat_count"] == 1

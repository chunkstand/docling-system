from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import collect_git_diff, collect_git_numstat


def test_git_diff_collectors_wire_base_and_staged(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, *, cwd, capture_output, text):
        commands.append(command)
        assert cwd == tmp_path
        assert capture_output is True
        assert text is True
        return Completed()

    monkeypatch.setattr("app.hotspot_prevention_diff.subprocess.run", fake_run)

    collect_git_diff(project_root=tmp_path, base="HEAD~1")
    collect_git_numstat(project_root=tmp_path, staged=True)

    assert commands == [
        ["git", "diff", "--no-ext-diff", "--unified=3", "HEAD~1"],
        ["git", "diff", "--no-ext-diff", "--numstat", "--cached"],
    ]


def test_git_diff_collectors_reject_base_with_staged(tmp_path: Path) -> None:
    try:
        collect_git_diff(project_root=tmp_path, base="HEAD", staged=True)
    except ValueError as exc:
        assert "--base and --staged cannot be used together" in str(exc)
    else:
        raise AssertionError("expected ValueError")

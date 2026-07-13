"""M-13 acceptance: чекер приёмки + CLI verify-acceptance (TSK-1301)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from workshop.__main__ import main
from workshop.acceptance import (
    CHANGELOG_NOT_FOUND,
    NO_ACCEPTED_FILES,
    verify_acceptance,
)
from workshop.result import Err, Ok


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _seed_workshop_dir(tmp_path: Path) -> Path:
    """Цех с CHANGELOG из двух записей; один файл переприниматся во второй записи."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "base.md").write_text("промпт v2", encoding="utf-8")
    (tmp_path / "graph.json").write_text('{"nodes": []}', encoding="utf-8")

    changelog = (
        "# CHANGELOG\n\n"
        "## запись 1 (устаревшая приёмка base.md)\n\n"
        "| Файл | Роль | sha256[:16] |\n|---|---|---|\n"
        f"| `prompts/base.md` | промпт | `{_digest('промпт v1')}` |\n\n"
        "## запись 2 (актуальная)\n\n"
        "| Файл | Роль | sha256[:16] |\n|---|---|---|\n"
        f"| `prompts/base.md` | промпт | `{_digest('промпт v2')}` |\n"
        f"| `graph.json` | граф | `{_digest('{\"nodes\": []}')}` |\n"
    )
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


def test_clean_acceptance_later_entry_wins(tmp_path: Path) -> None:
    workshop_dir = _seed_workshop_dir(tmp_path)
    result = verify_acceptance(workshop_dir / "CHANGELOG.md")
    assert isinstance(result, Ok)
    # base.md совпадает с ПОЗДНЕЙ записью (v2), хотя ранняя запись устарела
    assert result.value.is_clean
    assert set(result.value.matched) == {"prompts/base.md", "graph.json"}


def test_drift_detected(tmp_path: Path) -> None:
    workshop_dir = _seed_workshop_dir(tmp_path)
    (workshop_dir / "graph.json").write_text('{"nodes": [], "правка": 1}', encoding="utf-8")
    result = verify_acceptance(workshop_dir / "CHANGELOG.md")
    assert isinstance(result, Ok)
    assert result.value.is_clean is False
    assert result.value.mismatched == ("graph.json",)


def test_missing_file_detected(tmp_path: Path) -> None:
    workshop_dir = _seed_workshop_dir(tmp_path)
    (workshop_dir / "prompts" / "base.md").unlink()
    result = verify_acceptance(workshop_dir / "CHANGELOG.md")
    assert isinstance(result, Ok)
    assert result.value.missing == ("prompts/base.md",)


def test_removed_marker_retires_path(tmp_path: Path) -> None:
    """Поздняя запись `removed` снимает переехавший файл с проверки — missing нет."""
    workshop_dir = _seed_workshop_dir(tmp_path)
    (workshop_dir / "prompts" / "base.md").unlink()  # файл «переехал»
    changelog = workshop_dir / "CHANGELOG.md"
    changelog.write_text(
        changelog.read_text(encoding="utf-8")
        + "\n## запись 3 (переезд base.md)\n\n"
        "| Файл | Роль | sha256[:16] |\n|---|---|---|\n"
        "| `prompts/base.md` | перемещён | `removed` |\n",
        encoding="utf-8",
    )
    result = verify_acceptance(changelog)
    assert isinstance(result, Ok)
    assert result.value.is_clean
    assert result.value.matched == ("graph.json",)


def test_changelog_not_found(tmp_path: Path) -> None:
    result = verify_acceptance(tmp_path / "нет.md")
    assert isinstance(result, Err)
    assert result.code == CHANGELOG_NOT_FOUND


def test_no_accepted_files(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# CHANGELOG\n\nтолько текст, таблиц нет\n", encoding="utf-8")
    result = verify_acceptance(changelog)
    assert isinstance(result, Err)
    assert result.code == NO_ACCEPTED_FILES


def test_cli_accepts_dir_and_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    workshop_dir = _seed_workshop_dir(tmp_path)

    assert main(["verify-acceptance", str(workshop_dir)]) == 0
    assert "2 файлов актуальны" in capsys.readouterr().out

    (workshop_dir / "graph.json").write_text("{}", encoding="utf-8")
    assert main(["verify-acceptance", str(workshop_dir)]) == 1
    captured = capsys.readouterr()
    assert "ИЗМЕНЁН без приёмки: graph.json" in captured.err

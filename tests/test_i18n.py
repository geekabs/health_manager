"""i18n 文言."""

from __future__ import annotations

import pytest

from modules.i18n import LANG_EN, LANG_JA, is_english, tr


def test_tr_ja_app_title() -> None:
    s = tr(LANG_JA, "app_title")
    assert "ヘルス" in s or "ダッシュボード" in s


def test_tr_en_app_title() -> None:
    assert tr(LANG_EN, "app_title") == "Healthcare Dashboard"


def test_tr_format_skipped_csv() -> None:
    ja = tr(LANG_JA, "zip_warn_skipped_csv", n=3)
    assert "3" in ja
    en = tr(LANG_EN, "zip_warn_skipped_csv", n=3)
    assert "3" in en


def test_tr_unknown_key_returns_key() -> None:
    assert tr(LANG_JA, "nonexistent_key_xyz") == "nonexistent_key_xyz"


@pytest.mark.parametrize(
    "lang,expected",
    [
        (LANG_EN, True),
        (LANG_JA, False),
    ],
)
def test_is_english(lang: str, expected: bool) -> None:
    assert is_english(lang) is expected

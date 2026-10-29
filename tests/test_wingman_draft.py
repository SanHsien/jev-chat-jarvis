from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wingman.core.draft import _clean, _parse_candidates  # noqa: E402


def test_parse_candidates_preserves_brackets_at_end_of_candidate() -> None:
    # 候選結尾帶方括號（如 [公司]、[微笑]），不能被誤當作陣列邊界削掉
    assert _parse_candidates('["好的[公司]"]') == ["好的[公司]"]
    assert _clean("好的[公司]") == "好的[公司]"


def test_parse_candidates_multiline_unmatched_brackets() -> None:
    # 整段 JSON 解析失敗走逐行解析備援時，不能將未配對的邊界括號「[」誤當作候選
    s = '[\n"甲",\n"乙",\n"丙"\n]\n以上'
    assert _parse_candidates(s) == ["甲", "乙", "丙"]


def test_parse_candidates_multiline_split_bracket_lines() -> None:
    # 跨行方括號且尾隨雜訊時，逐行解析應正確剝除未配對邊界括號並保留候選
    s = '["甲",\n"乙"]\n["丙"]x'
    assert _parse_candidates(s) == ["甲", "乙", "丙"]

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import index_gen


def test_inspiration_index_groups_by_status():
    items = [
        {"path": "00-灵感库/a.md", "source": "发散", "status": "pending", "captured": "2026-07-11 10:00"},
        {"path": "00-灵感库/b.md", "source": "外部输入", "status": "carded", "captured": "2026-07-10 09:00"},
    ]
    lines = index_gen.inspiration_index_lines(items)
    text = "\n".join(lines)
    assert "待加工" in text
    assert "已转卡片" in text
    assert "[[00-灵感库/a.md" in text or "[[a" in text


def test_wiki_index_has_sections():
    pages = {"sources": ["06-Wiki/sources/s.md"], "entities": [], "concepts": ["06-Wiki/concepts/c.md"], "syntheses": []}
    lines = index_gen.wiki_index_lines(pages)
    text = "\n".join(lines)
    assert "Sources" in text or "来源" in text
    assert "Concepts" in text or "概念" in text


def test_empty_inputs_no_crash():
    assert isinstance(index_gen.inspiration_index_lines([]), list)
    assert isinstance(index_gen.wiki_index_lines({"sources": [], "entities": [], "concepts": [], "syntheses": []}), list)

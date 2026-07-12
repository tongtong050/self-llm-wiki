import sys, os
from pathlib import Path

# 让 tools 包可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import _utils


def test_source_dir_map_is_general():
    m = _utils._SOURCE_DIR_MAP
    assert m["00-灵感库"] == ("Inspiration", "inspiration")
    assert m["01-项目"] == ("Card", "card")
    assert m["02-长期关注"] == ("Card", "card")
    assert m["03-参考资料"] == ("Reference", "reference")
    # 地铁目录必须已移除
    assert "03-故障记录" not in m
    assert "02-工作任务" not in m


def test_exclude_dirs_general():
    ex = _utils._EXCLUDE_DIR_NAMES
    assert "07-系统" in ex
    assert "06-Wiki" in ex
    assert "09-AI总结" not in ex


def test_identify_template_by_dir():
    assert _utils.identify_template("01-项目/some-card.md") == "Card"
    assert _utils.identify_template("00-灵感库/x.md") == "Inspiration"
    assert _utils.identify_template("03-参考资料/y.md") == "Reference"


def test_identify_template_by_frontmatter():
    assert _utils.identify_template("whatever.md", {"type": "card"}) == "Card"
    assert _utils.identify_template("whatever.md", {"type": "inspiration"}) == "Inspiration"


def test_identify_template_fallback_general():
    assert _utils.identify_template("99-unknown/z.md") == "General"


def test_call_llm_accepts_temperature_param():
    import inspect
    sig = inspect.signature(_utils.call_llm)
    assert "temperature" in sig.parameters

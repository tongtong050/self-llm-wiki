import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import collide


def test_overlap_identical_is_high():
    a = {"tags": {"认知", "系统"}, "sources": {"s1"}, "related": {"X"}}
    b = {"tags": {"认知", "系统"}, "sources": {"s1"}, "related": {"X"}}
    assert collide.overlap_score(a, b) > 0.9


def test_overlap_disjoint_is_zero():
    a = {"tags": {"认知"}, "sources": {"s1"}, "related": {"X"}}
    b = {"tags": {"经济"}, "sources": {"s2"}, "related": {"Y"}}
    assert collide.overlap_score(a, b) == 0.0


def test_overlap_partial_in_sweetspot():
    a = {"tags": {"认知", "系统", "决策"}, "sources": {"s1"}, "related": {"X"}}
    b = {"tags": {"认知", "系统"}, "sources": {"s1"}, "related": {"Y"}}
    s = collide.overlap_score(a, b)
    assert 0.4 < s < 0.9  # 部分重合


def test_find_candidates_filters_sweetspot():
    concepts = [
        {"path": "A.md", "sig": {"tags": {"认知", "系统"}, "sources": {"s1"}, "related": set()}},
        {"path": "B.md", "sig": {"tags": {"认知"}, "sources": {"s1"}, "related": set()}},
        {"path": "C.md", "sig": {"tags": {"经济"}, "sources": {"s9"}, "related": set()}},
    ]
    cands = collide.find_candidates(concepts, 0.3, 0.9)
    pairs = {(c["a"], c["b"]) for c in cands}
    # A-B 有重合应入选；A-C / B-C 不相关不入选
    assert ("A.md", "B.md") in pairs or ("B.md", "A.md") in pairs
    assert not any("C.md" in (c["a"], c["b"]) for c in cands)


def test_concept_signature_extracts_sets():
    fm = {"tags": ["认知", "系统"], "sources": ["s1"], "related": ["X", "Y"]}
    sig = collide.concept_signature(fm, "body text")
    assert sig["tags"] == {"认知", "系统"}
    assert sig["sources"] == {"s1"}
    assert sig["related"] == {"X", "Y"}

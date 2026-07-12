"""概念碰撞检测（默认轻量档：tags/来源/共引用重叠，零 token）。

可选向量增强：设 LLM_EMBED_MODEL 时改用 embedding 余弦相似度（本 Phase 仅预留接口，
向量档实现见后续；默认轻量档已可用）。
"""
from __future__ import annotations
import json
import os
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import _utils


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def concept_signature(fm: dict, body: str) -> dict:
    def _set(key):
        v = fm.get(key, [])
        if isinstance(v, list):
            return {str(x).strip() for x in v if str(x).strip()}
        if isinstance(v, str) and v.strip():
            return {v.strip()}
        return set()
    return {"tags": _set("tags"), "sources": _set("sources"), "related": _set("related")}


def overlap_score(a: dict, b: dict) -> float:
    # 三信号加权：tags 0.5 + sources 0.3 + related 0.2
    t = _jaccard(a.get("tags", set()), b.get("tags", set()))
    s = _jaccard(a.get("sources", set()), b.get("sources", set()))
    r = _jaccard(a.get("related", set()), b.get("related", set()))
    return round(0.5 * t + 0.3 * s + 0.2 * r, 4)


def find_candidates(concepts: list[dict], cmin: float, cmax: float) -> list[dict]:
    out = []
    for x, y in combinations(concepts, 2):
        score = overlap_score(x["sig"], y["sig"])
        if cmin <= score <= cmax:
            out.append({"a": x["path"], "b": y["path"], "score": score})
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def _load_concepts() -> list[dict]:
    concepts = []
    concept_dir = _utils.WIKI_DIR / "concepts"
    if not concept_dir.is_dir():
        return concepts
    for p in sorted(concept_dir.glob("*.md")):
        fm = _utils.read_frontmatter(p)  # takes a path, returns dict | None
        concepts.append({
            "path": str(p.relative_to(_utils.REPO_ROOT)).replace("\\", "/"),
            "sig": concept_signature(fm or {}, ""),
        })
    return concepts


def main() -> None:
    cmin = float(os.getenv("COLLIDE_MIN", "0.6"))
    cmax = float(os.getenv("COLLIDE_MAX", "0.75"))
    concepts = _load_concepts()
    cands = find_candidates(concepts, cmin, cmax)

    # 增量：排除已处理对
    done = set()
    if _utils.COLLISION_FILE.exists():
        try:
            prev = json.loads(_utils.COLLISION_FILE.read_text(encoding="utf-8"))
            for c in prev.get("processed", []):
                done.add(tuple(sorted((c["a"], c["b"]))))
        except (json.JSONDecodeError, KeyError):
            pass
    fresh = [c for c in cands if tuple(sorted((c["a"], c["b"]))) not in done]

    payload = {"candidates": fresh, "processed": [], "sweetspot": [cmin, cmax]}
    _utils.COLLISION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _utils.COLLISION_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"碰撞候选：{len(fresh)} 对（甜区 {cmin}-{cmax}，共 {len(concepts)} 概念）")


if __name__ == "__main__":
    main()

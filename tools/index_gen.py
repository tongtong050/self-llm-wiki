"""生成目录索引：00-灵感库/index.md 与 06-Wiki/index.md。"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import _utils


def _link(path: str) -> str:
    stem = Path(path).stem
    return f"- [[{path}|{stem}]]"


def inspiration_index_lines(items: list[dict]) -> list[str]:
    pending = [it for it in items if it.get("status") != "carded"]
    carded = [it for it in items if it.get("status") == "carded"]
    lines = ["# 灵感库索引", ""]
    lines.append(f"## 待加工 ({len(pending)})")
    for it in sorted(pending, key=lambda x: x.get("captured", ""), reverse=True):
        lines.append(f"{_link(it['path'])} · {it.get('source','')} · {it.get('captured','')}")
    lines.append("")
    lines.append(f"## 已转卡片 ({len(carded)})")
    for it in sorted(carded, key=lambda x: x.get("captured", ""), reverse=True):
        lines.append(f"{_link(it['path'])} · {it.get('source','')} · {it.get('captured','')}")
    lines.append("")
    return lines


def wiki_index_lines(pages: dict) -> list[str]:
    sections = [("Sources 来源", "sources"), ("Entities 实体", "entities"),
                ("Concepts 概念", "concepts"), ("Syntheses 综合", "syntheses")]
    lines = ["# Wiki 索引", ""]
    for title, key in sections:
        paths = pages.get(key, [])
        lines.append(f"## {title} ({len(paths)})")
        for p in sorted(paths):
            lines.append(_link(p))
        lines.append("")
    return lines


def _scan_inspirations() -> list[dict]:
    items = []
    d = _utils.REPO_ROOT / "00-灵感库"
    if not d.is_dir():
        return items
    for p in sorted(d.glob("*.md")):
        if p.name == "index.md":
            continue
        fm = _utils.read_frontmatter(p) or {}  # takes a path, returns dict | None
        if fm.get("type") != "inspiration":
            continue
        items.append({
            "path": str(p.relative_to(_utils.REPO_ROOT)).replace("\\", "/"),
            "source": str(fm.get("source", "")),
            "status": str(fm.get("status", "pending")),
            "captured": str(fm.get("captured", "")),
        })
    return items


def _scan_wiki() -> dict:
    pages = {"sources": [], "entities": [], "concepts": [], "syntheses": []}
    for key in pages:
        d = _utils.WIKI_DIR / key
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            pages[key].append(str(p.relative_to(_utils.REPO_ROOT)).replace("\\", "/"))
    return pages


def main() -> None:
    insp = _scan_inspirations()
    (_utils.REPO_ROOT / "00-灵感库").mkdir(parents=True, exist_ok=True)
    (_utils.REPO_ROOT / "00-灵感库" / "index.md").write_text(
        "\n".join(inspiration_index_lines(insp)) + "\n", encoding="utf-8")

    pages = _scan_wiki()
    _utils.WIKI_DIR.mkdir(parents=True, exist_ok=True)
    (_utils.WIKI_DIR / "index.md").write_text(
        "\n".join(wiki_index_lines(pages)) + "\n", encoding="utf-8")
    print(f"索引已生成：灵感 {len(insp)} 条，Wiki 页 {sum(len(v) for v in pages.values())} 个")


if __name__ == "__main__":
    main()

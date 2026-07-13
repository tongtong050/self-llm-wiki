"""Flomo/碎片素材扫描器：定期扫描 03-参考资料/ 中手动放入的 .md 碎片，识别"经典学术概念"。

这是一个轻量骨架（Phase 5B）。当前打印文件清单，概念识别部分由 Agent 在 Claudian 中完成。
完整版将集成 LLM 调用（小模型批量扫 + 输出到 06-Wiki/concepts/）。

使用方式：python tools/flomo_scan.py [--dir 03-参考资料]
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import _utils


def scan_files(source_dir: str = "03-参考资料") -> list[Path]:
    d = _utils.REPO_ROOT / source_dir
    if not d.is_dir():
        print(f"目录不存在: {d}")
        return []
    files = sorted(p for p in d.rglob("*.md") if not p.name.startswith("."))
    return files


def main():
    files = scan_files()
    print(f"扫描到 {len(files)} 个 .md 碎片（03-参考资料/ 下）")
    for f in files:
        rel = f.relative_to(_utils.REPO_ROOT)
        fm = _utils.read_frontmatter(f)
        title = (fm or {}).get("title", f.stem) if fm else f.stem
        print(f"  - {rel}  ({title})")
    if not files:
        print("请手动放入 .md 碎片到 03-参考资料/。Agent 将定期扫描并识别经典学术概念。")


if __name__ == "__main__":
    main()

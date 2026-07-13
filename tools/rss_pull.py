"""RSS 拉取器：从自定义 RSS 源拉取内容，保存为 Markdown 到 03-参考资料/。

使用方式：python tools/rss_pull.py [--feeds feeds-file] [--limit N]
feeds-file 默认 07-系统/rss-feeds.json（每行一个 URL 的 JSON 数组，或由 Dashboard
的 settings.rssFeeds 手动维护）。若文件不存在，从环境变量 RSS_FEEDS 取逗号分隔 URL。

依赖：pip install feedparser markdownify（可选；未安装时提示安装）。
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import _utils

DEFAULT_FEEDS = "07-系统/rss-feeds.json"


def load_feeds(feeds_path: str | None = None) -> list[str]:
    path = Path(feeds_path or DEFAULT_FEEDS)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(u).strip() for u in data if str(u).strip()]
    env = os.getenv("RSS_FEEDS", "")
    return [u.strip() for u in env.split(",") if u.strip()]


def pull_feed(url: str, limit: int = 10) -> list[dict]:
    """拉取单个 RSS 源，返回 [{title, content, author, published}].

    需要 feedparser + markdownify。未安装时打印提示并返回 []。
    """
    try:
        import feedparser
    except ImportError:
        print("请安装 feedparser: pip install feedparser")
        return []
    try:
        import markdownify  # noqa: F401 — used below
    except ImportError:
        print("可选依赖 markdownify 未安装，将以纯文本保存内容")

    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        content = entry.get("summary") or entry.get("content", [{}])[0].get("value", "")
        # 尝试把 HTML 转 Markdown
        try:
            from markdownify import markdownify as md  # noqa: F811
            content = md(content, heading_style="ATX")
        except Exception:
            pass  # 保持原文
        items.append({
            "title": entry.get("title", "Untitled"),
            "content": content,
            "author": entry.get("author", ""),
            "published": entry.get("published", ""),
        })
    return items


def save_to_vault(items: list[dict], source_url: str) -> int:
    out_dir = _utils.REPO_ROOT / "03-参考资料" / "rss"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for it in items:
        slug = _sanitize(it["title"])
        path = out_dir / f"{slug}.md"
        if path.exists():
            continue  # 已拉取过，跳过
        fm = [
            "---",
            "type: reference",
            "source: rss",
            f"url: {source_url}",
            f"date: {datetime.now().strftime('%Y-%m-%d')}",
            f"published: {it['published']}",
            "tags: []",
            "---",
        ]
        path.write_text("\n".join(fm) + f"\n\n# {it['title']}\n\n{it['content']}\n", encoding="utf-8")
        count += 1
    return count


def _sanitize(title: str) -> str:
    import re
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', '-', title.strip())
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')[:50] or "untitled"


def main():
    feeds = load_feeds()
    if not feeds:
        print("未配置 RSS 源。请在 07-系统/rss-feeds.json 放 JSON 数组或设 RSS_FEEDS 环境变量。")
        return
    total = 0
    for url in feeds:
        print(f"拉取: {url}")
        items = pull_feed(url)
        if items:
            n = save_to_vault(items, url)
            print(f"  新增 {n} 条")
            total += n
    print(f"共新增 {total} 条。保存到 03-参考资料/rss/")


if __name__ == "__main__":
    main()

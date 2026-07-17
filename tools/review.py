#!/usr/bin/env python3
"""
Process pending review items from review.md.

Usage:
    python tools/review.py
    python tools/review.py --dry-run    # show what would be done without doing it
    python tools/review.py --item 3     # process only item #3

Reads 07-系统/review.md, finds all [x]-checked pending review items,
executes the selected action (CreatePage / Skip), and updates review.md.
"""

import sys
import re
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools._utils import (
    REPO_ROOT, WIKI_DIR, REVIEW_FILE, INDEX_FILE, LOG_FILE, HOT_FILE,
    read_file, write_file, safe_write, call_llm, append_log, update_hot_md,
    read_frontmatter,
)


def parse_review_items(content: str) -> list[dict]:
    """Parse pending review items from review.md content."""
    items = []

    # Split at "## 已处理" — only parse pending section
    pending_section = content.split("\n## 已处理")[0]

    # Find all review items: ## [x] type | title or ## [ ] type | title
    pattern = r'## \[(.)\] (\w+) \| (.+?)\n(.*?)(?=\n## \[.|$)'
    for match in re.finditer(pattern, pending_section, re.DOTALL):
        checked = match.group(1) != ' '
        rtype = match.group(2)
        title = match.group(3).strip()
        body = match.group(4).strip()

        # Only process checked items
        if not checked:
            items.append({
                "checked": False,
                "type": rtype,
                "title": title,
                "body": body,
            })
            continue

        # Extract metadata
        source = extract_field(body, "来源")
        description = extract_field(body, "描述")
        related_pages_raw = extract_field(body, "关联页面")
        search_queries_raw = extract_field(body, "建议搜索")

        # Parse selected option
        selected_option = None
        for opt_match in re.finditer(r'- \[(.)\] (\w.+)', body):
            if opt_match.group(1) != ' ':
                selected_option = opt_match.group(2).strip()
                break

        items.append({
            "checked": True,
            "type": rtype,
            "title": title,
            "source": source,
            "description": description,
            "related_pages": related_pages_raw,
            "search_queries": search_queries_raw,
            "selected_option": selected_option,
        })

    return items


def extract_field(body: str, field: str) -> str:
    """Extract a field value from review item body."""
    pattern = rf'\*\*{field}\*\*: (.+)'
    match = re.search(pattern, body)
    return match.group(1).strip() if match else ""


def create_page_from_review(item: dict) -> bool:
    """Use LLM to create a wiki page from a review item."""
    today = date.today().isoformat()

    # Determine page type and path
    if item["type"] == "missing-page" or item["type"] == "suggestion":
        page_type = "concept"
        page_dir = WIKI_DIR / "concepts"
    else:
        page_type = "entity"
        page_dir = WIKI_DIR / "entities"

    # Generate safe filename from title
    slug = re.sub(r'[^\w一-鿿\-]', '', item["title"].replace(' ', '-'))
    page_path = f"{'concepts' if page_type == 'concept' else 'entities'}/{slug}.md"
    full_path = WIKI_DIR / page_path

    if full_path.exists():
        print(f"  [!]  Page already exists: {page_path}")
        return False

    prompt = f"""Create a wiki page based on this review item.

Review type: {item['type']}
Title: {item['title']}
Description: {item.get('description', 'No description')}
Related pages: {item.get('related_pages', 'None')}
Search suggestions: {item.get('search_queries', 'None')}

Write a complete wiki page with YAML frontmatter and body content in Chinese.
Type: {page_type}
Include [[wikilinks]] to related pages where relevant.
Today: {today}

Return ONLY the complete page (frontmatter + body), starting with ---."""

    raw = call_llm(prompt, max_tokens=2048)

    # Ensure it starts with frontmatter
    if not raw.strip().startswith("---"):
        raw = f"---\ntitle: \"{item['title']}\"\ntype: {page_type}\ntags: []\ncreated: {today}\nlast_updated: {today}\n---\n\n# {item['title']}\n\n{raw}"

    safe_write(full_path, raw)
    print(f"  [OK] Created: {page_path}")
    return True


def update_review_file(items: list[dict], dry_run: bool = False):
    """Move processed items from pending to done section."""
    if dry_run:
        return

    content = read_file(REVIEW_FILE)
    if "## 已处理" not in content:
        content += "\n## 已处理\n"

    today = date.today().isoformat()

    for item in items:
        if not item["checked"]:
            continue

        action = item.get("selected_option", "Skip")
        done_entry = f"### {item['type']} | {item['title']} — {'[OK] 已创建页面' if action == 'CreatePage' else '[SKIP] 已跳过'} — {today}\n"

        # Remove the pending item
        pattern = rf'## \[x\] {re.escape(item["type"])} \| {re.escape(item["title"])}.*?(?=\n## |$)'
        content = re.sub(pattern, '', content, count=1, flags=re.DOTALL)

        # Add to done section
        content = content.replace("## 已处理\n", f"## 已处理\n\n{done_entry}")

    # Update counts
    pending_count = content.count("## [x] ") + content.count("## [ ] ")
    content = re.sub(r'> 待处理: \d+ 条', f'> 待处理: {pending_count} 条', content)

    safe_write(REVIEW_FILE, content)


def main():
    dry_run = "--dry-run" in sys.argv
    item_filter = None

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--item" and i + 2 < len(sys.argv):
            item_filter = int(sys.argv[i + 2]) - 1  # 1-indexed to 0-indexed

    if not REVIEW_FILE.exists():
        print("No review.md found. Nothing to process.")
        return

    content = read_file(REVIEW_FILE)
    items = parse_review_items(content)

    checked = [i for i in items if i["checked"]]
    if not checked:
        print("No checked items to process. Edit review.md and check [x] next to items you want to action.")
        return

    if item_filter is not None:
        if 0 <= item_filter < len(checked):
            checked = [checked[item_filter]]
        else:
            print(f"Item #{item_filter + 1} not found in checked items (total: {len(checked)}).")
            return

    print(f"\nProcessing {len(checked)} review item(s):\n")

    created = 0
    skipped = 0

    for i, item in enumerate(checked):
        print(f"  [{i + 1}] {item['type']} | {item['title']}")
        action = item.get("selected_option", "Skip")
        print(f"      Action: {action}")

        if dry_run:
            print(f"      (dry-run — no changes made)")
            continue

        if action == "CreatePage" or action.startswith("Create Page"):
            if create_page_from_review(item):
                created += 1
        else:
            skipped += 1
            print(f"      [SKIP]  Skipped")

    if not dry_run:
        update_review_file(items, dry_run=False)
        print(f"\n  Created: {created} pages")
        print(f"  Skipped: {skipped} items")
        print(f"  Review.md updated")

    update_hot_md("review", {"entities": [], "concepts": []})


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Ingest a source document into the LLM Wiki.

Usage:
    python tools/ingest.py <path-to-source>
    python tools/ingest.py raw/articles/my-article.md
    python tools/ingest.py report.pdf                  # auto-converts to .md
    python tools/ingest.py slides.pptx notes.docx       # batch, mixed formats
    python tools/ingest.py raw/mixed/ --no-convert      # skip auto-conversion
    python tools/ingest.py --validate-only              # run validation only

Supported formats (auto-converted via markitdown):
    .pdf .docx .pptx .xlsx .html .htm .txt .csv .json .xml
    .rst .rtf .epub .ipynb .yaml .yml .tsv .wav .mp3

The LLM reads the source, extracts knowledge, and updates the wiki:
  - Creates wiki/sources/<slug>.md
  - Updates wiki/index.md
  - Updates wiki/overview.md (if warranted)
  - Creates/updates entity and concept pages
  - Appends to wiki/log.md
  - Flags contradictions
  - Runs post-ingest validation (broken links, index coverage)
"""

import sys
import json
import re
import shutil
import tempfile
import difflib
from pathlib import Path
from collections import defaultdict
from datetime import date

# Bootstrap shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools._utils import (
    REPO_ROOT, WIKI_DIR, INDEX_FILE, OVERVIEW_FILE, LOG_FILE, HOT_FILE,
    REVIEW_FILE, SCHEMA_FILE, CACHE_FILE,
    read_file, write_file, safe_write, write_page_safe, call_llm, sha256,
    extract_wikilinks, all_wiki_pages, append_log,
    identify_template, should_exclude,
    load_ingest_cache, save_ingest_cache, is_source_changed, update_ingest_cache,
    update_hot_md, merge_pages, read_frontmatter, mark_as_ingested,
    clip_page_content,
)

# File extensions that can be auto-converted to markdown via markitdown.
# .md files are ingested directly without conversion.
CONVERTIBLE_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".htm", ".txt", ".csv", ".json", ".xml",
    ".rst", ".rtf", ".epub", ".ipynb",
    ".yaml", ".yml", ".tsv",
    ".wav", ".mp3",  # audio transcription via markitdown
}
ALL_SUPPORTED_EXTENSIONS = {".md"} | CONVERTIBLE_EXTENSIONS


def clip(text: str, limit: int = 260) -> str:
    """Truncate text at word boundary instead of mid-word."""
    if len(text) <= limit:
        return text
    clipped = text[: limit - 3].rsplit(" ", 1)[0].rstrip()
    return clipped + "..."


def build_wiki_context() -> str:
    """Build wiki context string for the ingest prompt."""
    parts = []
    if INDEX_FILE.exists():
        parts.append(f"## index.md\n{read_file(INDEX_FILE)}")
    if OVERVIEW_FILE.exists():
        parts.append(f"## overview.md\n{read_file(OVERVIEW_FILE)}")
    # Recent source pages for contradiction checking
    sources_dir = WIKI_DIR / "sources"
    if sources_dir.exists():
        recent = sorted(sources_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for p in recent:
            parts.append(f"## sources/{p.name}\n{clip_page_content(p.read_text(encoding='utf-8'), 3000)}")
    return "\n\n---\n\n".join(parts)


def parse_json_from_response(text: str) -> dict:
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    # Find the outermost JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group())


def update_index(new_entry: str, section: str = "Sources"):
    content = read_file(INDEX_FILE)
    if not content:
        content = "# Wiki Index\n\n## Overview\n- [Overview](overview.md) — living synthesis\n\n## Sources\n\n## Entities\n\n## Concepts\n\n## Syntheses\n"
    section_header = f"## {section}"
    if section_header in content:
        content = content.replace(section_header + "\n", section_header + "\n" + new_entry + "\n")
    else:
        content += f"\n{section_header}\n{new_entry}\n"
    safe_write(INDEX_FILE, content)


def append_reviews(reviews: list[dict], source: Path):
    """Append new review items to REVIEW_FILE."""
    existing = read_file(REVIEW_FILE)
    today = date.today().isoformat()

    if not existing or "## 待处理 Review" not in existing:
        header = (
            "# 待处理 Review\n\n"
            f"> 最后更新: {today}\n"
            "> 待处理: 0 条 | 已处理: 0 条\n\n"
            "---\n\n"
        )
        existing = header

    new_entries = []
    for r in reviews:
        rtype = r.get("type", "uncertain")
        title = r.get("title", "Untitled")
        desc = r.get("description", "")
        related = r.get("related_pages", [])
        source_name = source.name if source else "unknown"
        search_qs = r.get("search_queries", [])

        entry = f"## [ ] {rtype} | {title}\n\n"
        entry += f"- **状态**: ⏳ 待处理\n"
        entry += f"- **来源**: {source_name}\n"
        entry += f"- **描述**: {desc}\n"
        if related:
            entry += f"- **关联页面**: {', '.join(f'[[{rp}]]' for rp in related)}\n"
        if search_qs:
            entry += f"- **建议搜索**: {' | '.join(search_qs)}\n"
        entry += "\n### 操作选项\n\n"
        entry += "- [ ] Create Page\n"
        entry += "- [ ] Skip\n\n"
        entry += "---\n\n"
        new_entries.append(entry)

    if not new_entries:
        return

    done_marker = "\n## 已处理"
    if done_marker in existing:
        parts = existing.split(done_marker, 1)
        body = parts[0] + "\n" + "".join(new_entries) + done_marker + parts[1]
    else:
        body = existing.rstrip() + "\n" + "".join(new_entries)

    pending_count = body.count("## [ ] ")
    body = body.replace("> 待处理: 0 条", f"> 待处理: {pending_count} 条")

    safe_write(REVIEW_FILE, body)


def check_page_conflict(page_path: str) -> bool:
    """Check if a wiki page already exists."""
    return (WIKI_DIR / page_path).exists()


def should_skip_merge(existing_content: str, incoming_content: str) -> bool:
    """Skip LLM merge if pages are near-identical."""
    ratio = difflib.SequenceMatcher(None, existing_content, incoming_content).ratio()
    return ratio > 0.9


def validate_ingest(changed_pages: list[str] | None = None) -> dict:
    """Validate wiki integrity after an ingest.

    Checks:
      1. Broken wikilinks in changed pages (or all pages if none specified)
      2. Pages not registered in index.md

    Returns dict with 'broken_links' and 'unindexed' lists.
    """
    existing_pages = {p.stem.lower() for p in all_wiki_pages()}
    index_content = read_file(INDEX_FILE).lower()

    # Determine which pages to scan for broken links
    if changed_pages:
        scan_paths = [WIKI_DIR / p for p in changed_pages if (WIKI_DIR / p).exists()]
    else:
        scan_paths = [p for p in WIKI_DIR.rglob("*.md")
                      if p.name not in ("index.md", "log.md", "lint-report.md")]

    # Check 1: Broken wikilinks
    broken_links = []
    for page_path in scan_paths:
        content = read_file(page_path)
        rel = str(page_path.relative_to(WIKI_DIR))
        for link in extract_wikilinks(content):
            # Normalize: strip paths, check stem only
            link_stem = Path(link).stem.lower() if '/' in link else link.lower()
            if link_stem not in existing_pages:
                broken_links.append((rel, link))

    # Check 2: Unindexed pages (only check changed pages)
    unindexed = []
    for p in (changed_pages or []):
        page_path = WIKI_DIR / p
        if page_path.exists():
            # Check if the page filename appears in index.md
            stem = page_path.stem.lower()
            if stem not in index_content and p not in ("log.md", "overview.md"):
                unindexed.append(p)

    return {"broken_links": broken_links, "unindexed": unindexed}


def convert_to_md(source: Path) -> Path:
    """Convert a non-markdown file to .md using markitdown.

    Returns the path to the converted .md file (placed next to the original
    with a .md extension, or in a temp location if the source dir is read-only).
    """
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("Error: markitdown not installed (needed to convert non-.md files).")
        print("  Install with: pip install markitdown")
        sys.exit(1)

    md = MarkItDown(enable_plugins=False)
    try:
        result = md.convert(str(source))
    except Exception as e:
        print(f"Error: failed to convert '{source.name}': {e}")
        sys.exit(1)

    # Write converted output next to source as <name>.md
    output = source.with_suffix(".md")
    try:
        output.write_text(result.text_content, encoding="utf-8")
    except OSError:
        # Fallback: source directory may be read-only
        tmp = Path(tempfile.mkdtemp()) / f"{source.stem}.md"
        tmp.write_text(result.text_content, encoding="utf-8")
        output = tmp

    print(f"  ✓ Converted {source.name} → {output.name}")
    return output


def get_template_instruction(template_name: str, source_name, today: str) -> str:
    """Return template-specific instruction string for the ingest prompt."""
    templates = {
        "Card": f"""Use the Card template. Source: {source_name}.
This is a knowledge card — a distilled idea with a core claim.
Extract: core claim/thesis, supporting reasoning, key concepts, related entities, cross-links.
Frontmatter: type: card, tags.
Concept priorities: academic/theoretical concepts, methods, frameworks, mental models.
Entity priorities: people, works, tools, organizations referenced.""",

        "Inspiration": f"""Use the Inspiration template. Source: {source_name}.
This is a raw inspiration/idea captured by the user.
Extract: the central idea, its source type (外部输入/发散/解决问题 if present), any nascent concepts worth tracking.
Frontmatter: type: inspiration, tags.
Concept priorities: emerging themes, questions, tentative concepts.
Entity priorities: anything concrete the idea references.""",

        "Reference": f"""Use the Reference template. Source: {source_name}.
This is external reference material (article, note, clipping).
Extract: summary, key points, applicable scope, key entities, cross-references.
Frontmatter: type: reference, tags.
Concept priorities: academic concepts, definitions, key findings.
Entity priorities: authors, sources, works, tools.""",

        "General": f"""Use the General template. Source: {source_name}.
This source has no matching directory or frontmatter type — use General template as fallback.
Extract: summary, key points, connections.
Frontmatter: type: source, date, uncertain: true, tags.
Mark as uncertain in review output.""",
    }
    return templates.get(template_name, templates["General"])


def ingest(source_path: str, auto_convert: bool = True, force: bool = False):
    """Ingest a single source document into the wiki.

    Steps: read → identify template → check cache → LLM generate → check conflicts → write → review → hot.md → mark source
    """
    source = Path(source_path)
    if not source.exists():
        print(f"Error: file not found: {source_path}")
        return False

    # Skip excluded directories
    if should_exclude(source):
        print(f"  ⚠️  Skipping excluded path: {source}")
        return False

    # Auto-convert non-markdown files
    converted_path = None
    if source.suffix.lower() != ".md":
        if not auto_convert:
            print(f"  Skipping non-.md file (--no-convert): {source.name}")
            return False
        if source.suffix.lower() not in CONVERTIBLE_EXTENSIONS:
            print(f"  ⚠️  Unsupported format: {source.suffix} — skipping {source.name}")
            return False
        print(f"  Converting {source.name} to markdown...")
        converted_path = convert_to_md(source)
        source = converted_path

    source_content = source.read_text(encoding="utf-8")
    today = date.today().isoformat()

    # Identify template
    fm = read_frontmatter(source)
    template = identify_template(source, fm)
    is_uncertain = (template == "General")

    # Cache check
    if not force and not is_source_changed(source_path, source_content):
        print(f"  ✓ Skipping (unchanged): {source.name}")
        return True

    print(f"\nIngesting: {source.name}")
    print(f"  Template: {template}{' (⚠ uncertain)' if is_uncertain else ''}")

    wiki_context = build_wiki_context()
    schema = read_file(SCHEMA_FILE)

    # Build source identity for prompt
    try:
        rel_source = source.relative_to(REPO_ROOT)
    except ValueError:
        rel_source = source.name

    template_instruction = get_template_instruction(template, rel_source, today)

    prompt = f"""You are maintaining a personal knowledge base wiki (ideas, cards, concepts). Process this source document using the specified template.

## Template to Use: {template}

{template_instruction}

## Schema and Conventions
{schema}

## Current Wiki State
{wiki_context if wiki_context else "(wiki is empty — this is the first source)"}

## Source Document (file: {rel_source})
=== SOURCE START ===
{source_content}
=== SOURCE END ===

## Instructions

1. Use the **{template}** template structure for the source page output.
2. Extract entities (people, works, tools, organizations) → create entity pages with `[[wikilinks]]`.
3. Extract concepts (ideas, methods, frameworks, themes) → create concept pages with `[[wikilinks]]`.
4. If the wiki context shows existing pages that relate to this content, cross-reference them.
5. Flag any contradictions with existing wiki content.
6. For `missing-page` or `suggestion` review types, include 2-3 keyword search queries.

Today's date: {today}

Return ONLY a valid JSON object (no markdown fences, no prose outside the JSON):
{{
  "title": "Human-readable title for this source",
  "slug": "kebab-case-slug",
  "source_page": "full markdown for wiki/sources/<slug>.md following the {template} template. CRITICAL: Aggressively convert people, works, tools, organizations, key concepts into [[Wikilinks]] inline.",
  "index_entry": "- [Title](sources/slug.md) — one-line Chinese summary",
  "overview_update": "full updated overview.md content, or null if no major change needed",
  "entity_pages": [
    {{"path": "entities/EntityName.md", "content": "full markdown with frontmatter and [[wikilinks]]"}}
  ],
  "concept_pages": [
    {{"path": "concepts/ConceptName.md", "content": "full markdown with frontmatter and [[wikilinks]]"}}
  ],
  "contradictions": ["describe contradiction with existing wiki content, or empty list"],
  "reviews": [
    {{
      "type": "contradiction|duplicate|missing-page|suggestion|uncertain",
      "title": "Short title",
      "description": "Detailed description in Chinese",
      "related_pages": ["entities/Page.md"],
      "options": ["CreatePage", "Skip"],
      "search_queries": ["keyword search 1", "keyword search 2"]
    }}
  ],
  "log_entry": "## [{today}] ingest | <title>\\n\\nAdded source. Key claims: ..."
}}
"""

    print(f"  calling API ...")
    raw = call_llm(prompt, max_tokens=8192, temperature=0.2)
    try:
        data = parse_json_from_response(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing API response: {e}")
        debug_path = Path(tempfile.gettempdir()) / "ingest_debug.txt"
        debug_path.write_text(raw, encoding="utf-8")
        print(f"Raw response saved to {debug_path}")
        return False

    slug = data.get("slug", source.stem)
    merge_count = 0

    # Write source page
    write_page_safe(f"sources/{slug}.md", data["source_page"])

    # Write entity pages (with conflict detection + merge)
    for page in data.get("entity_pages", []):
        path = page["path"]
        content = page["content"]
        if check_page_conflict(path):
            existing = read_file(WIKI_DIR / path)
            if should_skip_merge(existing, content):
                print(f"  → skipped merge (near-identical): {path}")
                continue
            print(f"  → merging: {path}")
            merged = merge_pages(existing, content, path, str(rel_source))
            write_page_safe(path, merged)
            merge_count += 1
        else:
            write_page_safe(path, content)

    # Write concept pages (with conflict detection + merge)
    for page in data.get("concept_pages", []):
        path = page["path"]
        content = page["content"]
        if check_page_conflict(path):
            existing = read_file(WIKI_DIR / path)
            if should_skip_merge(existing, content):
                print(f"  → skipped merge (near-identical): {path}")
                continue
            print(f"  → merging: {path}")
            merged = merge_pages(existing, content, path, str(rel_source))
            write_page_safe(path, merged)
            merge_count += 1
        else:
            write_page_safe(path, content)

    # Update overview
    if data.get("overview_update"):
        safe_write(OVERVIEW_FILE, data["overview_update"])

    # Update index
    for entry in [data["index_entry"]]:
        update_index_entry(entry, section="Sources")

    # Append log
    append_log(data.get("log_entry", f"## [{today}] ingest | {data.get('title', 'Unknown')}"))

    # Report contradictions
    contradictions = data.get("contradictions", [])
    if contradictions:
        print("\n  ⚠️  Contradictions detected:")
        for c in contradictions:
            print(f"     - {c}")

    # Write reviews
    reviews = data.get("reviews", [])
    if is_uncertain:
        reviews.append({
            "type": "uncertain",
            "title": f"Template uncertain for {source.name}",
            "description": f"No frontmatter type or known source directory. Used General template as fallback.",
            "related_pages": [f"sources/{slug}.md"],
            "options": ["CreatePage", "Skip"],
            "search_queries": [],
        })
    if reviews:
        append_reviews(reviews, source)

    # Update hot.md
    entities = [p["path"].split("/")[-1].replace(".md", "") for p in data.get("entity_pages", [])]
    concepts = [p["path"].split("/")[-1].replace(".md", "") for p in data.get("concept_pages", [])]
    update_hot_md("ingest", {
        "source": data.get("title", source.name),
        "entities": entities,
        "concepts": concepts,
    })

    # Mark source as ingested (frontmatter only)
    if auto_convert and source.suffix == ".md":
        mark_as_ingested(source_path)
    elif converted_path:
        # Don't modify converted temp files
        pass

    # Update cache
    update_ingest_cache(source_path, source_content)

    # Post-ingest validation
    created_pages = [f"sources/{slug}.md"]
    for page in data.get("entity_pages", []):
        created_pages.append(page["path"])
    for page in data.get("concept_pages", []):
        created_pages.append(page["path"])
    updated_pages = ["index.md", "log.md"]
    if data.get("overview_update"):
        updated_pages.append("overview.md")

    validation = validate_ingest(created_pages)

    print(f"\n{'='*50}")
    print(f"  ✅ Ingested: {data.get('title', 'Unknown')}")
    print(f"{'='*50}")
    print(f"  Template: {template}")
    print(f"  Created : {len(created_pages)} pages")
    for p in created_pages:
        print(f"           + {p}")
    print(f"  Updated : {len(updated_pages)} pages")
    for p in updated_pages:
        print(f"           ~ {p}")
    if merge_count:
        print(f"  Merged  : {merge_count} pages (LLM merge)")
    if contradictions:
        print(f"  Warnings: {len(contradictions)} contradiction(s)")
    if reviews:
        print(f"  Reviews : {len(reviews)} review item(s) → review.md")
    if validation["broken_links"]:
        print(f"  ⚠️  Broken links: {len(validation['broken_links'])}")
        for page, link in validation["broken_links"][:5]:
            print(f"           {page} → [[{link}]]")
    if validation["unindexed"]:
        print(f"  ⚠️  Not in index: {len(validation['unindexed'])}")
    if not validation["broken_links"] and not validation["unindexed"]:
        print("  ✓ Validation passed")
    print()
    return True


if __name__ == "__main__":
    # Handle --validate-only flag
    if len(sys.argv) == 2 and sys.argv[1] == "--validate-only":
        print("Running wiki validation (no ingest)...\n")
        result = validate_ingest()
        if result["broken_links"]:
            print(f"Broken wikilinks: {len(result['broken_links'])}")
            for page, link in result["broken_links"][:20]:
                print(f"  wiki/{page} → [[{link}]]")
            if len(result["broken_links"]) > 20:
                print(f"  ... and {len(result['broken_links']) - 20} more")
        else:
            print("No broken wikilinks found.")
        print()
        index_content = read_file(INDEX_FILE).lower()
        unindexed_all = []
        for p in WIKI_DIR.rglob("*.md"):
            if p.name in ("index.md", "log.md", "lint-report.md", "overview.md"):
                continue
            if p.stem.lower() not in index_content:
                unindexed_all.append(str(p.relative_to(WIKI_DIR)))
        if unindexed_all:
            print(f"Pages not in index.md: {len(unindexed_all)}")
            for up in unindexed_all[:20]:
                print(f"  wiki/{up}")
            if len(unindexed_all) > 20:
                print(f"  ... and {len(unindexed_all) - 20} more")
        else:
            print("All pages are indexed.")
        sys.exit(0)

    # Parse flags
    no_convert = "--no-convert" in sys.argv
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage: python tools/ingest.py <path-to-source> [path2 ...] [dir1 ...]")
        print("       python tools/ingest.py --validate-only")
        print("       python tools/ingest.py --no-convert  # skip auto-conversion of non-.md files")
        print(f"\nSupported formats: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    paths_to_process = []
    for arg in args:
        p = Path(arg)
        if p.is_file():
            ext = p.suffix.lower()
            if ext in ALL_SUPPORTED_EXTENSIONS:
                paths_to_process.append(p)
            else:
                print(f"  ⚠️  Skipping unsupported format: {p.name} ({ext})")
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in ALL_SUPPORTED_EXTENSIONS:
                    paths_to_process.append(f)
        else:
            import glob
            for f in glob.glob(arg, recursive=True):
                g_p = Path(f)
                if g_p.is_file() and g_p.suffix.lower() in ALL_SUPPORTED_EXTENSIONS:
                    paths_to_process.append(g_p)

    # Deduplicate while preserving order
    unique_paths = []
    seen = set()
    for p in paths_to_process:
        abs_p = p.resolve()
        if abs_p not in seen:
            seen.add(abs_p)
            unique_paths.append(p)

    if not unique_paths:
        print("Error: no supported files found to ingest.")
        print(f"Supported formats: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    if len(unique_paths) > 1:
        print(f"Batch mode: found {len(unique_paths)} files to ingest.")

    success = 0
    failed = 0
    for p in unique_paths:
        if ingest(str(p), auto_convert=not no_convert, force=force):
            success += 1
        else:
            failed += 1

    if len(unique_paths) > 1:
        print(f"\nBatch complete: {success} succeeded, {failed} failed")

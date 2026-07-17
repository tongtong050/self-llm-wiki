#!/usr/bin/env python3
"""
Query the LLM Wiki with intent classification and graph expansion.

Usage:
    python tools/query.py "What are the main themes across all sources?"
    python tools/query.py "How does ConceptA relate to ConceptB?" --save
    python tools/query.py "Summarize everything about EntityName" --save synthesis/my-analysis.md

Flags:
    --save              Save the answer back into the wiki
    --save <path>       Save to a specific wiki path
    --skip-classify     Skip intent classification (use default: fact_lookup)
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools._utils import (
    REPO_ROOT, WIKI_DIR, INDEX_FILE, LOG_FILE, SCHEMA_FILE, OVERVIEW_FILE,
    HOT_FILE, GRAPH_DIR,
    read_file, write_file, safe_write, call_llm, append_log, update_hot_md,
    clip_page_content, all_wiki_pages,
)


# ── Intent Classification ──────────────────────────────────────────────

INTENT_CLASSIFY_PROMPT = """Classify the user's query about a personal knowledge base (ideas, cards, concepts).

Query: {question}

Wiki index excerpt (first 2000 chars):
{index_excerpt}

Return ONLY a JSON object:
{{
  "intent": "chitchat|fact_lookup|summary|relationship|deep_analysis",
  "reason": "short explanation in Chinese",
  "keywords": ["keyword1", "keyword2"],
  "suggested_search": "reformulated search query for the wiki search"
}}

Intent definitions:
- chitchat: Greetings, small talk, "你好", "谢谢" — no retrieval needed
- fact_lookup: Looking for a specific fact, number, procedure, part name — narrow search, 1-3 pages
- summary: "有哪些", "总结一下", "概述", "常见" — needs index + overview + recent sources
- relationship: "是什么原因导致", "和什么有关", "影响哪些系统", "关联" — needs graph expansion
- deep_analysis: "综合分析", "全面评估", multi-part complex questions — needs broad retrieval + graph"""


def classify_intent(question: str) -> dict:
    """Classify query intent using fast LLM. Returns {intent, reason, keywords, suggested_search}."""
    index_content = read_file(INDEX_FILE)
    index_excerpt = index_content[:2000] if index_content else "(wiki is empty)"

    prompt = INTENT_CLASSIFY_PROMPT.format(
        question=question,
        index_excerpt=index_excerpt,
    )

    raw = call_llm(prompt, "LLM_MODEL_FAST", "anthropic/claude-3-5-haiku-latest", max_tokens=256)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        return {
            "intent": result.get("intent", "fact_lookup"),
            "reason": result.get("reason", ""),
            "keywords": result.get("keywords", []),
            "suggested_search": result.get("suggested_search", question),
        }
    except (json.JSONDecodeError, ValueError):
        return {"intent": "fact_lookup", "reason": "parse fallback", "keywords": [], "suggested_search": question}


# ── Page retrieval ─────────────────────────────────────────────────────

def find_relevant_pages(question: str, index_content: str) -> list[Path]:
    """Extract linked pages from index that seem relevant via keyword matching."""
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', index_content)
    question_lower = question.lower()
    relevant = []

    for title, href in md_links:
        title_lower = title.lower()
        has_cjk = any('一' <= ch <= '鿿' for ch in title)
        if has_cjk:
            matched = any(
                title_lower[j:j+2] in question_lower
                for j in range(len(title_lower) - 1)
                if any('一' <= c <= '鿿' for c in title_lower[j:j+2])
            )
        else:
            matched = any(word in question_lower for word in title_lower.split() if len(word) > 2)

        if matched:
            p = WIKI_DIR / href
            if p.exists() and p not in relevant:
                relevant.append(p)

    return relevant


def expand_by_graph(matched_pages: list[Path], min_confidence: float = 0.7, max_expand: int = 5) -> list[dict]:
    """Expand matched pages by graph neighbors. Returns [{path, relation, confidence}, ...]."""
    graph_json = GRAPH_DIR / "graph.json"
    if not graph_json.exists():
        return []

    try:
        graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    page_ids = set()
    for p in matched_pages:
        pid = p.relative_to(WIKI_DIR).as_posix().replace('.md', '')
        page_ids.add(pid)

    expanded = []
    seen = set(page_ids)

    for edge in graph_data.get("edges", []):
        # Support both edge formats: (source,target) and (from,to)
        src = edge.get("source", edge.get("from", ""))
        tgt = edge.get("target", edge.get("to", ""))
        weight = edge.get("weight", edge.get("confidence", 0))

        if weight < min_confidence:
            continue

        if src in page_ids and tgt not in seen:
            target_path = WIKI_DIR / f"{tgt}.md"
            if target_path.exists():
                expanded.append({"path": str(target_path.relative_to(REPO_ROOT)), "relation": edge.get("type", "unknown"), "confidence": weight})
                seen.add(tgt)
        elif tgt in page_ids and src not in seen:
            source_path = WIKI_DIR / f"{src}.md"
            if source_path.exists():
                expanded.append({"path": str(source_path.relative_to(REPO_ROOT)), "relation": edge.get("type", "unknown"), "confidence": weight})
                seen.add(src)

    return expanded[:max_expand]


def llm_select_pages(question: str, index_content: str) -> list[Path]:
    """Fallback: use LLM to select relevant pages from index."""
    prompt = (
        f"Given this wiki index:\n\n{index_content}\n\n"
        f"Which pages are most relevant to answering: \"{question}\"\n\n"
        f"Return ONLY a JSON array of relative file paths, e.g. [\"sources/foo.md\", \"concepts/Bar.md\"]. Maximum 10 pages."
    )
    raw = call_llm(prompt, "LLM_MODEL_FAST", "anthropic/claude-3-5-haiku-latest", max_tokens=512)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        paths = json.loads(raw)
        return [WIKI_DIR / p for p in paths if (WIKI_DIR / p).exists()]
    except (json.JSONDecodeError, TypeError):
        return []


# ── Save synthesis ─────────────────────────────────────────────────────

def save_synthesis(question: str, answer: str) -> str:
    """Save a query answer to wiki/syntheses/. Returns the relative path."""
    today = date.today().isoformat()
    slug = re.sub(r'[^\w一-鿿\-]', '', question[:60].replace(' ', '-'))
    save_path = f"syntheses/{slug}.md"
    full_path = WIKI_DIR / save_path

    frontmatter = (
        f"---\n"
        f"title: \"{question[:80]}\"\n"
        f"type: synthesis\n"
        f"tags: []\n"
        f"sources: []\n"
        f"created: {today}\n"
        f"last_updated: {today}\n"
        f"---\n\n"
    )
    safe_write(full_path, frontmatter + answer)

    # Update index
    index_content = read_file(INDEX_FILE)
    entry = f"- [{question[:60]}]({save_path}) — synthesis\n"
    if "## Syntheses" in index_content:
        index_content = index_content.replace("## Syntheses\n", f"## Syntheses\n{entry}\n")
        safe_write(INDEX_FILE, index_content)

    print(f"  Saved: {save_path}")
    return save_path


# ── Main query ─────────────────────────────────────────────────────────

def query(question: str, save: bool = False, save_as: str | None = None,
          skip_classify: bool = False):
    """Execute the full query pipeline: classify → retrieve → synthesize → optionally save."""
    today = date.today().isoformat()

    # Step 0: Read hot.md for context
    hot_content = read_file(HOT_FILE)
    if hot_content:
        print(f"  [hot.md: {len(hot_content.split())} words of recent context]")

    # Step 1: Read index
    index_content = read_file(INDEX_FILE)
    if not index_content:
        print("Wiki is empty. Ingest some sources first: python tools/ingest.py <source>")
        return

    # Step 2: Intent classification
    if skip_classify:
        intent_info = {"intent": "fact_lookup", "reason": "skipped", "keywords": [], "suggested_search": question}
    else:
        print("  classifying intent ...")
        intent_info = classify_intent(question)

    intent = intent_info["intent"]
    print(f"  intent: {intent} ({intent_info['reason']})")

    # Step 3: Route based on intent
    if intent == "chitchat":
        print("  (chitchat — no retrieval)")
        return

    # Retrieve matching pages
    relevant_pages = find_relevant_pages(intent_info["suggested_search"], index_content)

    # Fallback: LLM page selection
    if not relevant_pages or len(relevant_pages) <= 1:
        print("  LLM-assisted page selection ...")
        llm_pages = llm_select_pages(question, index_content)
        for p in llm_pages:
            if p not in relevant_pages:
                relevant_pages.append(p)

    # Always include overview for summary and deep_analysis
    if intent in ("summary", "deep_analysis"):
        overview = WIKI_DIR / "overview.md"
        if overview.exists() and overview not in relevant_pages:
            relevant_pages.insert(0, overview)

    # Cap based on intent
    page_caps = {"fact_lookup": 3, "summary": 5, "relationship": 10, "deep_analysis": 15}
    max_pages = page_caps.get(intent, 5)
    relevant_pages = relevant_pages[:max_pages]

    # Step 4: Graph expansion for relationship/deep_analysis
    graph_expanded = []
    if intent in ("relationship", "deep_analysis"):
        print(f"  expanding by graph (intent={intent}) ...")
        graph_expanded = expand_by_graph(relevant_pages)

    # Step 5: Read page content
    pages_context = ""
    for p in relevant_pages:
        rel = str(p.relative_to(REPO_ROOT))
        content = clip_page_content(p.read_text(encoding="utf-8"), 3000)
        pages_context += f"\n\n### {rel}\n{content}"

    if graph_expanded:
        pages_context += "\n\n## 图谱关联的页面 (间接相关)\n"
        for ge in graph_expanded:
            pages_context += f"\n- [[{Path(ge['path']).stem}]] — {ge['relation']} (confidence: {ge['confidence']:.2f})"

    if not pages_context.strip():
        pages_context = f"\n\n### wiki/index.md\n{index_content[:5000]}"

    # Step 6: Synthesize answer
    schema = read_file(SCHEMA_FILE)
    print(f"  synthesizing from {len(relevant_pages)} pages (+ {len(graph_expanded)} graph) ...")

    prompt = f"""You are querying a personal knowledge base. Use the wiki pages below to synthesize a thorough answer in Chinese. Cite sources using [[PageName]] wikilink syntax.

Schema:
{schema}

Wiki pages:
{pages_context}

Question: {question}

Write a well-structured markdown answer with headers, bullets, and [[wikilink]] citations. At the end, add a ## 来源 section listing the pages you drew from.
"""

    answer = call_llm(prompt, "LLM_MODEL", "anthropic/claude-3-5-sonnet-latest", max_tokens=4096)
    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)

    # Update hot.md
    keywords = intent_info.get("keywords", [])
    update_hot_md("query", {"source": question[:80], "entities": keywords, "concepts": []})

    # Append log
    log_msg = f"## [{today}] query | {question[:80]}\n\nIntent: {intent}. Answer from {len(relevant_pages)} pages."
    append_log(log_msg)

    # Step 7: Save
    saved_path = None
    if save_as:
        saved_path = save_synthesis(question, answer) if save_as == "" else save_as
        print(f"  indexed: {saved_path}")
        append_log(f"## [{today}] save | {saved_path}\n\nSaved answer to synthesis.")
    elif save:
        saved_path = save_synthesis(question, answer)
        append_log(f"## [{today}] save | {saved_path}\n\nSaved answer to synthesis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the LLM Wiki")
    parser.add_argument("question", help="Question to ask the wiki")
    parser.add_argument("--save", nargs="?", const="", default=None,
                        help="Save answer to wiki (optionally specify path)")
    parser.add_argument("--skip-classify", action="store_true",
                        help="Skip intent classification")
    args = parser.parse_args()

    query(args.question,
          save=args.save is not None,
          save_as=args.save if args.save != "" else None,
          skip_classify=args.skip_classify)

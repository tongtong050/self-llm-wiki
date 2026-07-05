# SessionStart Hook

On every session start and after PostCompact:

1. **Read hot.md** — load `09-AI总结/wiki/hot.md` for recent context (~500 words). This gives you the last operations, recent topics, and pending items count. Summarize in 1-2 sentences what's happened recently.

2. **Check ingest triggers** — scan `09-AI总结/.ingest-triggers/` for pending trigger files (`*.md`).
   If found:
   - Read each trigger file to get the source path
   - Execute the Ingest Workflow (see CLAUDE.md) for each source
   - Delete the trigger file on success
   - Print summary: "Processed N ingest triggers: X succeeded, Y failed"

3. **Clean up stale locks** — remove any `.lock` files under `09-AI总结/wiki/` older than 60 seconds.
   If any removed: "Cleaned up N stale lock files."

4. **Check health** (if no triggers were found) — offer: "Run health check? (reply 'yes' or 'health')"

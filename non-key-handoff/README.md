# non-key handoff

These five markdown files are the regenerated research-program inputs for the
three new repos (`non-key-attention`, `non-key-coupling`, `non-key-perplexity`).
They live here only because the originating Claude Code session had MCP write
access to `triology` but not to the new repos. They are **not** part of triology.

To use:

1. Create the three empty GitHub repos (`non-key-attention`, `non-key-coupling`,
   `non-key-perplexity`) — no README, no .gitignore, no license, no Copilot Jumpstart.
2. Start a fresh Claude Code session that has all three new repos selected as
   accessible.
3. Download these five files from the GitHub UI (each file → Raw → Save As) or
   `git clone -b claude/laughing-curie-PZibJ` and copy them out of `non-key-handoff/`.
4. In the new session, paste `setup_prompt.md`'s contents as the first message
   and attach the other four files. Type: `Proceed per setup_prompt.md attached.`
5. Expect three ASKs during scaffolding: ASK-A1 (LayoutLMv3-CORD search result),
   ASK-A2 (CPU core count), ASK-A3 (reference PDFs for Step 8 restyling).

Files:

- `setup_prompt.md` — scaffolding trigger
- `non_key_channel_research_plan.md` — mega plan (single source of truth)
- `non-key-attention.md` — Idea A cookbook
- `non-key-coupling.md` — Idea C cookbook
- `non-key-perplexity.md` — Idea D cookbook

After the new repos are scaffolded, this `non-key-handoff/` folder can be deleted
from triology with no impact.

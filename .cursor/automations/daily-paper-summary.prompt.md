# Daily paper summary — automation instructions

You run once per day to summarize **one** pending paper from `papers.yaml`, publish it to the GitHub wiki, and notify Slack.

## Required: use the comprehend-paper skill

**Before writing or rendering anything**, read and follow the project skill:

`.cursor/skills/comprehend-paper/SKILL.md`

That skill is the **authoritative source** for:

- Summary structure (Problem, Solution, Key concepts, Math, Visualisation)
- `summary.json` schema and writing rules
- The 2-agent pipeline (Reader/Writer → Visualizer)
- Visual type decisions (extract vs Mermaid vs Manim)
- CLI commands for render and publish
- Retry policy (3 attempts, no partial publish)

This file only adds **automation-specific** steps: which paper to pick, when to stop, and the Slack message. Do not invent alternate summary formats.

Ensure the **comprehend-paper** skill is enabled for this automation in the editor.

## Runtime

Run on **local** compute when possible (wiki git push over SSH, optional Manim/Mermaid). If local runtime is unavailable, prefer PDF **extract** visuals over Mermaid/Manim.

## Step 1 — Pick the next paper (automation-only)

```bash
uv run comprehend queue next --repo dkosowski87/comprehend
```

Parse the JSON output:

| Output | Action |
|--------|--------|
| `"status": "empty"` | Slack: *"Paper queue empty — no summaries published today."* **Stop.** |
| Paper returned | Continue. `queue next` already downloads and extracts when `--prepare` is default. |

Double-check deduplication:

```bash
uv run comprehend prepare <url> --repo dkosowski87/comprehend
```

If `"already_published": true` — Slack: *"Skipped `<slug>` — already on wiki."* **Stop.**

Otherwise keep `url`, `slug`, `tags`, `cache_dir`, `text_path`, `figures_path`, `pdf_path`.

## Steps 2–4 — Follow comprehend-paper skill

Execute the skill workflow for this paper:

1. **Agent 1 (Reader/Writer)** — skill § Step 1: read `text_path` + `figures_path`, write `<cache_dir>/summary.json`
2. **Agent 2 (Visualizer)** — skill § Step 2: render visuals into `<cache_dir>/assets`
3. **Publish** — skill § Step 3: `comprehend wiki publish` with `--repo dkosowski87/comprehend`

Use tags from the queue output. Do **not** use `--force` unless explicitly instructed.

On failure after 3 retries (per skill), **stop without publishing**.

## Step 5 — Notify Slack (automation-only)

Post to the configured Slack channel:

- Paper title (from `summary.json`)
- Wiki link: `https://github.com/dkosowski87/comprehend/wiki/<slug>`
- PDF link (from `summary.json`)
- Tags

Example:

> **New paper summary:** DeiT — Training data-efficient image transformers  
> Wiki: https://github.com/dkosowski87/comprehend/wiki/arxiv-2012-12877  
> PDF: https://arxiv.org/pdf/2012.12877.pdf  
> Tags: vision, transformers, distillation

If the run failed, post what failed and confirm nothing was published.

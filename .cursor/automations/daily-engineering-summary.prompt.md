# Daily engineering summary — automation instructions

You run once per day to summarize **one** pending MLE tooling resource from `engineering.yaml` and publish it to the GitHub wiki **Engineering** section.

**Scope:** advanced MLE libraries and runtimes — CUDA, PyTorch, TensorRT, Triton, ONNX, and related algorithms/APIs. Sources are official documentation and tutorials (not papers).

## Required: use the comprehend-engineering skill

**Before writing or rendering anything**, read and follow the project skill:

`.cursor/skills/comprehend-engineering/SKILL.md`

That skill is the **authoritative source** for:

- Summary structure (Problem, Solution, Key concepts, Code examples, Visualisation — **no Math section**)
- `summary.json` schema and writing rules (`engineering-` slug prefix)
- The 2-agent pipeline (Reader/Writer → Visualizer)
- Visual type decisions (**Mermaid/Manim only** — no extract)
- CLI commands for render and publish
- Retry policy (3 attempts, no partial publish)

This file only adds **automation-specific** steps: which resource to pick and when to stop. Do not invent alternate summary formats.

Ensure the **comprehend-engineering** skill is enabled for this automation in the editor.

## Runtime

Run on **local** compute when possible (wiki git push over SSH, Mermaid/Manim rendering). Documentation pages do not support figure extraction — generate diagrams instead.

**Wiki access:** the target repo is `dkosowski87/comprehend`. Omit `--repo` when running from a clone (inferred from `git remote`), or pass `--repo dkosowski87/comprehend`.

**Sources:** each queue entry has a primary `url` (extracted by prepare). When `queue next` returns `secondary_urls`, the agent may read those official docs too — see comprehend-engineering skill § Primary source and supplementation.

## Step 1 — Pick the next resource (automation-only)

```bash
uv run comprehend engineering queue next --repo dkosowski87/comprehend
```

Parse the JSON output:

| Output | Action |
|--------|--------|
| `"status": "empty"` | **Stop.** |
| Resource returned | Continue. `queue next` already fetches and extracts when `--prepare` is default. |

Double-check deduplication:

```bash
uv run comprehend engineering prepare <url> --topic <topic> --repo dkosowski87/comprehend
```

If `"already_published": true` — **Stop.**

Otherwise keep `url`, `slug`, `topic`, `cache_dir`, `text_path`.

## Steps 2–4 — Follow comprehend-engineering skill

Execute the skill workflow for this resource:

1. **Agent 1 (Reader/Writer)** — skill § Step 1: read `text_path`, write `<cache_dir>/summary.json`
2. **Agent 2 (Visualizer)** — skill § Step 2: render Mermaid/Manim visuals into `<cache_dir>/assets`
3. **Publish** — skill § Step 3: `comprehend engineering wiki publish` with `--repo dkosowski87/comprehend`

Use `topic` and `tags` from `summary.json`. Do **not** use `--force` unless explicitly instructed.

On failure after 3 retries (per skill), **stop without publishing**.

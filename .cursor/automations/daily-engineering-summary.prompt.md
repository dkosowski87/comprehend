# Daily engineering summary — automation instructions

You run once per day to summarize **one** pending MLE tooling resource from `engineering.yaml`, publish it to the GitHub wiki **Engineering** section, and notify Slack.

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

This file only adds **automation-specific** steps: which resource to pick, when to stop, and the Slack message. Do not invent alternate summary formats.

Ensure the **comprehend-engineering** skill is enabled for this automation in the editor.

## Communication boundary

This automation requires **exactly one** Slack message per run.

You are the **orchestrating agent**. Reader/Writer and Visualizer are internal pipeline steps — delegate to them **without** granting Slack or other notification tools. Their completion reports come back to you only.

**You** post to Slack only in **Step 5** below, or on **early exit** in Step 1 (empty queue, already published). Do not post while Steps 2–4 run.

## Runtime

Run on **local** compute when possible (wiki git push over SSH, Mermaid/Manim rendering). Documentation pages do not support figure extraction — generate diagrams instead.

**Wiki access:** the target repo is `dkosowski87/comprehend`. Omit `--repo` when running from a clone (inferred from `git remote`), or pass `--repo dkosowski87/comprehend`.

## Step 1 — Pick the next resource (automation-only)

```bash
uv run comprehend engineering queue next --repo dkosowski87/comprehend
```

Parse the JSON output:

| Output | Action |
|--------|--------|
| `"status": "empty"` | Slack: *"Engineering queue empty — no summaries published today."* **Stop.** |
| Resource returned | Continue. `queue next` already fetches and extracts when `--prepare` is default. |

Double-check deduplication:

```bash
uv run comprehend engineering prepare <url> --topic <topic> --repo dkosowski87/comprehend
```

If `"already_published": true` — Slack: *"Skipped `<slug>` — already on wiki."* **Stop.**

Otherwise keep `url`, `slug`, `topic`, `cache_dir`, `text_path`.

## Steps 2–4 — Follow comprehend-engineering skill

Execute the skill workflow for this resource:

1. **Agent 1 (Reader/Writer)** — skill § Step 1: read `text_path`, write `<cache_dir>/summary.json`
2. **Agent 2 (Visualizer)** — skill § Step 2: render Mermaid/Manim visuals into `<cache_dir>/assets`
3. **Publish** — skill § Step 3: `comprehend engineering wiki publish` with `--repo dkosowski87/comprehend`

Use `topic` and `tags` from `summary.json`. Do **not** use `--force` unless explicitly instructed.

On failure after 3 retries (per skill), **stop without publishing**.

## Step 5 — Notify Slack (automation-only)

Post to the configured Slack channel:

- Summary title (from `summary.json`)
- Wiki link: `https://github.com/dkosowski87/comprehend/wiki/<slug>`
- Source link (from `summary.json`)
- Topic and tags

Example:

> **New engineering summary:** PyTorch CUDA Semantics  
> Wiki: https://github.com/dkosowski87/comprehend/wiki/engineering-pytorch-cuda-semantics  
> Source: https://pytorch.org/docs/stable/notes/cuda.html  
> Topic: `pytorch` — Tags: `cuda`, `pytorch`

If the run failed, post what failed and confirm nothing was published.

---
name: comprehend-concept
description: >-
  Explain ML concepts referenced in paper summaries: web research, short wiki
  page with up to two visuals, link first mention in the paper. Use with comprehend
  concept prepare/triage/publish. Pass the paper slug in the prompt when linking
  a concept to an existing paper summary.
---

# Comprehend — Concept explanations

Create a standalone wiki page for a concept used but not fully explained in a paper summary (e.g. **cyclic shift** in Swin Transformer). Then link the **first mention** of that concept in the paper wiki page.

Manual workflow only — not part of the daily paper automation.

## Concept kinds

| Kind | Examples | Typical source |
|------|----------|----------------|
| **Simple** | `cyclic_shift`, `euler_integration`, `k-means`, `gradient-clipping`, Kullback–Leibler divergence | Known algorithms, math, or CV/ML building blocks — explain via web research |
| **Paper-originated** | `ccff`, `conditional-flow-matching`, `PANet`, `ViT`, `diffusion` (when introduced elsewhere) | The paper **cites** another work that introduces the idea — consider summarizing that paper first |

Use **triage** (below) to decide; when uncertain, prefer the simple path unless bibliography evidence is strong.

## Prerequisites

1. Paper summary is **published** on the wiki (when linking a concept to that paper).
2. The paper is listed in `papers.yaml` (needed for PDF cache / triage).
3. **Do not** declare concepts under `papers.yaml`. Pass the paper wiki **slug** in the user prompt and CLI (`--paper arxiv-2103-14030`).

Example user prompt:

```
/comprehend-concept

Explain cyclic_shift and link it from the Swin paper (arxiv-2103-14030).
Run prepare, triage, write concept.json, render, and publish.
```

## Step 0 — Prepare

```bash
uv run comprehend concept prepare \
  --paper arxiv-2103-14030 \
  --concept cyclic_shift \
  --term "cyclic shift" \
  --term "shifted window"
```

| Output field | Meaning |
|--------------|---------|
| `concept_already_published` | Concept wiki page exists — skip writing page, only patch paper links |
| `paper_already_links_concept` | Paper already links to concept — nothing to do |
| `paper_summary_path` | Read for how the paper uses the term |
| `terms` | Link-search terms for patching the paper wiki |
| `cache_dir` | Write `concept.json` and `assets/` here |

If `paper_already_links_concept` is true, **stop**.

`--term` is optional; if omitted, terms fall back to `keywords` in `concept.json` at publish time, then the concept id with `_` → spaces.

## Step 0b — Triage (origin paper check)

Run **after** prepare, **before** writing `concept.json`:

```bash
uv run comprehend concept triage \
  --paper arxiv-2304-08069 \
  --concept ccff \
  --term "cross-scale feature fusion" \
  --term "CCFF"
```

Reads the cached PDF **References** section and matches concept terms.

| `kind` | Meaning | Agent action |
|--------|---------|--------------|
| `simple` | No bibliography hit for this concept | Continue with standard concept page (Step 1) |
| `uncertain` | No References section in cache | Treat as simple unless you know otherwise |
| `paper_originated` | Bibliography entry likely introduces the idea | See queue fields below |

### When `kind` is `paper_originated`

**If `queue.in_queue` is true** — tell the user:

- Which **slug** / **title** is already in `papers.yaml`
- **status** `pending` → they can run the paper summary workflow first
- **status** `published` → they can read that wiki summary for depth
- They may still write a shorter concept page now, or wait until the origin paper is summarized

**If `ask_user_add_to_queue` is true** — tell the user the origin paper is **not** in `papers.yaml`, show `suggested_queue_entry` (URL, slug, title excerpt), and **ask** whether to add it.

- **Do not** add to the queue without explicit user approval.
- If the user agrees:

```bash
uv run comprehend queue add https://arxiv.org/abs/1406.4789 \
  --slug arxiv-1406-0789 \
  --title "Feature Pyramid Networks for Object Detection"
```

Then remind them they can summarize that paper (`/comprehend-paper` or `queue next`) before or after the concept page.

**If `suggested_queue_entry.url` is null** — no arXiv URL was parsed; ask the user for the origin paper URL before adding to the queue.

`proceed_with_concept_page` is always `true` — triage informs the workflow; it does not block publishing a concept page.

## Step 1 — Research and write `concept.json`

Read the paper summary (`paper_summary_path`) for context. **Search the web** for the concept — there is no dedicated source PDF.

For **paper-originated** concepts, prefer the origin paper (if summarized on the wiki) plus web sources; keep the concept page **general**, not a second paper summary.

Write `<cache_dir>/concept.json`:

```json
{
  "name": "Cyclic shift",
  "concept_id": "cyclic_shift",
  "slug": "concept-cyclic-shift",
  "related_papers": [
    {"slug": "arxiv-2103-14030", "title": "Swin Transformer: ..."}
  ],
  "what_it_is": ["2-4 bullets defining the concept"],
  "how_it_works": ["2-4 bullets on mechanism/intuition"],
  "keywords": ["cyclic shift", "shifted window", "roll operation"],
  "math": [
    {
      "id": "m1",
      "label": "short label",
      "latex": "E = mc^2",
      "variables": [
        {"symbol": "E", "meaning": "total energy"},
        {"symbol": "m", "meaning": "rest mass"}
      ]
    }
  ],
  "tags": ["transformers", "representation-learning"],
  "visuals": [
    {
      "id": "visual",
      "caption": "...",
      "type": "manim",
      "description": "...",
      "manim_scene_path": "...",
      "manim_scene_class": "..."
    }
  ]
}
```

### Writing rules

- **English only**
- **No paper-specific context section** — do not add "Why it appears in Swin Transformer". Keep explanations general.
- **Max 1 visual** — use id `"visual"` (not paper-style ids like `5a`)
- **No inline LaTeX** in bullets — GitHub wiki does not render `\(...\)`. Put equations in a **`math`** array and reference them with `**m1**`, `**m2**`, … (ids `m1`, `m2`, …). They become jump links to a **Math** section with `$$...$$` blocks, same as paper summaries. Add a `variables` legend for non-obvious symbols in each equation.
- **Tags** in `concept.json`: infer 1–5 from the concept and related papers (`uv run comprehend tags`, max 5). Tags from a related paper's summary are a reasonable starting point.
- **Keywords**: 3–10 concept-specific terms, auto-bolded in **What it is** and **How it works** during assembly. Also used as link-search terms when patching the paper wiki (unless `--term` overrides at publish).
- Sections: **What it is**, **How it works**, optional **Math**, optional **Visualisation**
- Include the triggering paper in `related_papers` (slug from the user prompt / `--paper`)
- Use `slug` from prepare output (`concept-*` prefix)

### Visual choice

| Type | When to use |
|------|-------------|
| **manim** | Default for non-diagram content — spatial layouts, grids, shifts, math-heavy illustrations |
| **mermaid** | Diagrams and charts only — flowcharts, block diagrams, decision trees |
| **extract** | Rare — only if reusing a figure from the paper PDF |

**Prefer Manim over Mermaid** unless the visual is clearly a diagram or chart.

Manim → static PNG only (`manim render -s`).

## Step 2 — Render visual

```bash
uv run comprehend concept render <cache_dir>/concept.json \
  --assets-dir <cache_dir>/assets
```

Retry up to **3 times** on render failures.

## Step 3 — Publish

```bash
uv run comprehend concept publish <cache_dir>/concept.json \
  --paper arxiv-2103-14030 \
  --assets-dir <cache_dir>/assets
```

Behavior:

- **New concept** — writes `concept-*.md`, updates `Concepts.md` index, patches first mention in paper wiki
- **Concept already on wiki** — skips concept page, **only patches** paper links
- **`--force`** — overwrite existing concept page
- **`--term`** — optional override for link-search terms at publish time

## Wiki layout

| Page | Example |
|------|---------|
| Concept | `concept-cyclic-shift.md` |
| Index | `Concepts.md` |
| Paper (patched) | `arxiv-2103-14030.md` |

Concept URL: `https://github.com/<owner>/<repo>/wiki/concept-cyclic-shift`

## Retry policy

Up to **3 retries** for network/render/git failures. Do not publish partial concept pages.

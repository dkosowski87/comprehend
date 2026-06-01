---
name: comprehend-concept
description: >-
  Explain ML concepts referenced in paper summaries: web research, short wiki
  page with one visual, link first mention in the paper. Use with comprehend
  concept prepare/publish or when papers.yaml lists concepts for a paper.
---

# Comprehend — Concept explanations

Create a standalone wiki page for a concept used but not fully explained in a paper summary (e.g. **cyclic shift** in Swin Transformer). Then link the **first mention** of that concept in the paper wiki page.

Manual workflow only — not part of the daily paper automation.

## Prerequisites

1. Paper summary is **published** on the wiki.
2. Concept is declared in `papers.yaml` under that paper:

```yaml
papers:
  - url: https://arxiv.org/abs/2103.14030
    tags: [vision, transformers]
    concepts:
      - cyclic_shift
      # or with custom link terms:
      - slug: cyclic_shift
        terms: ["cyclic shift", "shifted window"]
```

## Step 0 — Prepare

```bash
uv run comprehend concept prepare \
  --paper arxiv-2103-14030 \
  --concept cyclic_shift
```

| Output field | Meaning |
|--------------|---------|
| `concept_already_published` | Concept wiki page exists — skip writing page, only patch paper links |
| `paper_already_links_concept` | Paper already links to concept — nothing to do |
| `paper_summary_path` | Read for how the paper uses the term |
| `cache_dir` | Write `concept.json` and `assets/` here |

If `paper_already_links_concept` is true, **stop**.

## Step 1 — Research and write `concept.json`

Read the paper summary (`paper_summary_path`) for context. **Search the web** for the concept — there is no dedicated source PDF.

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
  "math": [
    {"id": "m1", "label": "short label", "latex": "E = mc^2"}
  ],
  "tags": ["vision", "transformers"],
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
- **No inline LaTeX** in bullets — GitHub wiki does not render `\(...\)`. Put equations in a **`math`** array and reference them with `**m1**`, `**m2**`, … (ids `m1`, `m2`, …). They become jump links to a **Math** section with `$$...$$` blocks, same as paper summaries.
- Sections: **What it is**, **How it works**, optional **Math**, optional **Visualisation**
- Include the triggering paper in `related_papers`
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

Link terms come from `papers.yaml` (default: concept id with `_` → spaces).

## Wiki layout

| Page | Example |
|------|---------|
| Concept | `concept-cyclic-shift.md` |
| Index | `Concepts.md` |
| Paper (patched) | `arxiv-2103-14030.md` |

Concept URL: `https://github.com/<owner>/<repo>/wiki/concept-cyclic-shift`

## Retry policy

Up to **3 retries** for network/render/git failures. Do not publish partial concept pages.

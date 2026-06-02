---
name: comprehend-paper
description: >-
  Summarize ML papers from PDF/arXiv URLs into structured GitHub wiki pages
  with visuals. Use when processing papers.yaml, running comprehend queue,
  writing paper summaries, or creating Manim/Mermaid visuals for papers.
---

# Comprehend — ML Paper Summaries

Turn an arXiv or PDF URL into a structured wiki summary with up to 4 visuals, published to this repository's GitHub wiki.

## Workflow overview

Use a **2-agent pipeline** orchestrated by the main agent:

1. **Prepare** — run CLI, check deduplication
2. **Agent 1 (Reader/Writer)** — read PDF text, write `summary.json`
3. **Agent 2 (Visualizer)** — render up to 4 PNG visuals
4. **Publish** — assemble markdown and push to wiki

Retry solvable errors up to **3 times** (network, Manim/mmdc failures). After 3 failures, stop **without publishing**.

## Step 0 — Prepare and deduplicate

```bash
uv run comprehend prepare <url>
```

If `"already_published": true`, **stop immediately**.

For queue-driven runs:

```bash
uv run comprehend queue next
uv run comprehend queue status
```

Save outputs under `.comprehend/papers/<slug>/`:
- `paper.pdf`, `text.txt`, `figures.json`
- `summary.json` (Agent 1 output)
- `assets/` (Agent 2 output)

## Step 1 — Agent 1: Reader/Writer

Read `.comprehend/papers/<slug>/text.txt` and inspect `figures.json` for extractable figures.

Write `.comprehend/papers/<slug>/summary.json` matching this schema:

```json
{
  "title": "Paper title",
  "pdf_url": "https://arxiv.org/pdf/....pdf",
  "tags": ["tag1", "tag2"],
  "slug": "arxiv-2012-12877",
  "problem": ["bullet 1", "bullet 2"],
  "solution": ["bullet with cross-refs like 4a, 5a"],
  "key_concepts": ["theoretical explanations tied to this paper's contributions"],
  "math": [
    {"id": "4a", "label": "soft distillation", "latex": "..."}
  ],
  "visuals": [
    {
      "id": "5a",
      "caption": "Architecture overview",
      "type": "extract",
      "description": "...",
      "refs": ["3a"],
      "page": 4,
      "xref": 42
    }
  ]
}
```

### Summary rules

**Language:** English only.

**Sections:**

1. **Problem** — what limitation or gap the paper addresses (2–4 bullets).
2. **Solution** — how the paper solves it. Use cross-reference ids (`**4a**`, `(5a)`) where helpful; these become jump links in the wiki output.
3. **Key concepts** — theoretical explanations aligned with *this paper's* contributions. Not a general ML primer. Include intuition (e.g. why attention helps long-range dependencies) when the paper relies on it.
4. **Math** — only equations central to understanding. LaTeX without `$` delimiters (added during assembly).
5. **Visualisation** — specs only (Agent 2 renders). **Maximum 4 visuals.**

**Do not** include a key-results or benchmarks section.

**Slug:** use the slug from `comprehend prepare` (typically `arxiv-<id-with-dashes>`).

**Tags:** from `papers.yaml` when queue-driven; otherwise infer 2–4 topical tags.

## Step 2 — Agent 2: Visualizer

Read `summary.json` and `figures.json`. Render each visual (max 4):

| type | when to use | how |
|------|-------------|-----|
| `extract` | paper figure is clear and needs no simplification | set `page`, `xref` or `clip` |
| `mermaid` | flowcharts, token/data flow, architecture simplified | write `.mmd` file, set `mermaid_source` in JSON or render separately |
| `manim` | math-heavy layouts, matrices, coordinate diagrams | write scene `.py`, set `manim_scene_path` and `manim_scene_class` |

**Decision rule:** extract when quality is good; generate when simplification or annotation is needed.

Render all visuals:

```bash
uv run comprehend render summary .comprehend/papers/<slug>/summary.json \
  --pdf-path .comprehend/papers/<slug>/paper.pdf \
  --assets-dir .comprehend/papers/<slug>/assets
```

Individual tools when iterating:

```bash
uv run comprehend render mermaid diagram.mmd --output assets/<slug>-5a.png
uv run comprehend render manim scene.py --scene-class MyScene --output assets/<slug>-5a.png
uv run comprehend pdf crop paper.pdf --page 4 --xref 42 --output assets/<slug>-5a.png
```

Manim renders **static PNG only** (never video). For multi-step ideas, use multiple static frames as separate visuals (still max 4 total).

## Step 3 — Publish

```bash
uv run comprehend assemble .comprehend/papers/<slug>/summary.json \
  --output .comprehend/papers/<slug>/page.md

uv run comprehend wiki publish .comprehend/papers/<slug>/summary.json \
  --assets-dir .comprehend/papers/<slug>/assets
```

Publishing skips if the wiki page already exists (default). Never force-republish in v1.

## Wiki markdown template

Assembled pages follow this structure:

```markdown
# {Title}

**PDF:** [{pdf_url}]({pdf_url})
**Tags:** `tag1`, `tag2`

## 1. Problem
- ...

## 2. Solution
- ...

## 3. Key concepts
- ...

## 4. Math

<a id="4a"></a>

**4a** soft distillation:
$$...$$

## 5. Visualisation

<a id="5a"></a>

### 5a — {caption}
![5a](assets/{slug}-5a.png)
```

## Retry policy

Retry up to **3 times** when:
- PDF download fails (network)
- Manim or mmdc render fails (fix scene/diagram and retry)
- Wiki git push fails (transient)

Do **not** publish partial summaries. On final failure, report the error and leave the wiki unchanged.

## Queue automation

Daily or batch processing:

```bash
uv run comprehend queue run      # prepare all pending, list papers needing summaries
uv run comprehend queue next       # next single paper with artifacts
uv run comprehend queue status     # pending vs published
```

Process each pending paper through the full 2-agent pipeline.

## Dependencies

Core (always): `uv sync`

Optional visuals:
- Manim: `uv sync --extra manim` (requires system LaTeX, FFmpeg, Cairo)
- Mermaid: `npm install -g @mermaid-js/mermaid-cli`

GitHub wiki must be enabled on the repository. Publishing uses SSH git access to `owner/repo.wiki.git`.

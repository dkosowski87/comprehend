---
name: comprehend-paper
description: >-
  Summarize ML papers from PDF/arXiv URLs into structured GitHub wiki pages
  with visuals. Use when processing papers.yaml, running comprehend queue,
  writing paper summaries, or creating Manim/Mermaid visuals for papers.
---

# Comprehend — ML Paper Summaries

Turn an arXiv or PDF URL into a structured wiki summary with paper figures and generated visuals, published to this repository's GitHub wiki.

## Workflow overview

Use a **2-agent pipeline** orchestrated by the main agent:

1. **Prepare** — run CLI, check deduplication
2. **Agent 1 (Reader/Writer)** — read PDF text, triage figures, write `summary.json`
3. **Agent 2 (Visualizer)** — render all visuals in `summary.json`
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

Read `.comprehend/papers/<slug>/text.txt` and inspect `figures.json` → `figure_regions` (each entry has `page`, `number`, `clip`, and `caption`).

### Figure triage (do this before writing visuals)

Review **every** caption in `figure_regions`. For each figure, read its caption and decide whether it helps explain the **problem**, **solution**, **key concepts**, or **math**. Include all figures that pass the include rules below. There is **no visual count limit**.

**Include** when the caption or figure content shows:

| Category | Examples |
|----------|----------|
| **Process visualisation** | Data flow, training/inference pipeline, rendering procedure (e.g. NeRF Figure 2: scene representation + differentiable rendering) |
| **Model architecture** | Network diagrams, module layouts, encoder/decoder structure (e.g. Swin Transformer Figure 3, RT-DETR Figure 4) |
| **Methodology plots** | Diagrams that explain *how* the method works — loss formulations visualised, attention patterns as architecture, schematic comparisons of approaches |

**Exclude** — even if visually appealing:

| Category | Examples |
|----------|----------|
| **Qualitative results** | Example generated images, segmentation mask overlays, before/after comparisons on sample inputs |
| **Quantitative results** | Benchmark tables rendered as figures, mAP/accuracy bar charts, scatter plots of speed vs. accuracy |
| **Ablations** | Component removal studies, hyperparameter sweep plots, "w/ vs w/o X" result grids |
| **Dataset samples** | Random training images, annotation examples, teaser photos |

When unsure, ask: *"Does this figure teach the reader how the method works, or does it show that it works well?"* Include the former; skip the latter.

Cross-reference included figures from **problem**, **solution**, **key concepts**, and **math** using ids like `**5a**` or `(5b)`.

Write `.comprehend/papers/<slug>/summary.json` matching this schema:

```json
{
  "title": "Paper title",
  "pdf_url": "https://arxiv.org/pdf/....pdf",
  "tags": ["transformers", "distillation"],
  "slug": "arxiv-2012-12877",
  "keywords": ["DeiT", "distillation token", "attention distillation"],
  "problem": ["bullet 1", "bullet 2"],
  "solution": ["bullet with cross-refs like 4a, 5a"],
  "key_concepts": ["theoretical explanations tied to this paper's contributions"],
  "math": [
    {
      "id": "4a",
      "label": "soft distillation",
      "latex": "...",
      "variables": [
        {"symbol": "\\mathcal{L}", "meaning": "distillation loss"},
        {"symbol": "p_t", "meaning": "teacher softmax probabilities"}
      ]
    }
  ],
  "visuals": [
    {
      "id": "5a",
      "caption": "NeRF scene representation and rendering",
      "type": "extract",
      "description": "5D input, volume rendering, and rendering loss",
      "refs": ["2a", "3a"],
      "page": 3,
      "figure_number": 2
    },
    {
      "id": "5b",
      "caption": "Swin Transformer architecture",
      "type": "extract",
      "description": "Hierarchical stages and shifted-window blocks",
      "refs": ["2a"],
      "page": 4,
      "figure_number": 3
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
4. **Math** — only equations central to understanding. LaTeX without `$` delimiters (added during assembly). For each equation, add a `variables` legend listing non-obvious symbols and what they represent in *this paper's* notation. Use GitHub-wiki-compatible macros only: `\boldsymbol{}` for bold vectors/matrices (not `\bm{}`), `\mathrm{}` for operator/module names (not `\operatorname{}`), `\mathbf{}` only for upright bold symbols such as indicator functions (`\mathbf{1}`). Hyphenated names belong inside `\mathrm{}`, e.g. `\mathrm{Q\text{-}FC}`. Brace nested superscripts inside `^{...}` (e.g. `^{\mathcal{S}^{\ast}}`, not `^{\mathcal{S}^*}`); assembly rewrites common cases but prefer the braced form.

```json
"math": [
  {
    "id": "4a",
    "label": "volume rendering",
    "latex": "C(\\boldsymbol{r}) = \\int T(t)\\,\\sigma(\\boldsymbol{r}(t))\\,\\boldsymbol{c}(\\boldsymbol{r}(t), \\boldsymbol{d})\\,dt",
    "variables": [
      {"symbol": "\\boldsymbol{r}", "meaning": "3D spatial location"},
      {"symbol": "\\boldsymbol{d}", "meaning": "viewing direction"},
      {"symbol": "\\sigma", "meaning": "volume density at a point"},
      {"symbol": "T(t)", "meaning": "accumulated transmittance along the ray"},
      {"symbol": "\\boldsymbol{c}", "meaning": "emitted RGB color"}
    ]
  },
  {
    "id": "4b",
    "label": "quantized FC projection",
    "latex": "\\boldsymbol{q}=\\mathrm{Q\\text{-}FC}(\\boldsymbol{O}),\\quad \\boldsymbol{k},\\boldsymbol{v}=\\mathrm{Q\\text{-}FC}(\\boldsymbol{E})",
    "variables": [
      {"symbol": "\\boldsymbol{q}", "meaning": "quantized query vector"},
      {"symbol": "\\mathrm{Q\\text{-}FC}", "meaning": "quantized fully-connected layer"}
    ]
  }
]
```

Include variables that a reader cannot infer from the label alone. Skip universal constants (`e`, `π`) and obvious indices unless the paper assigns them a specific role. Use LaTeX in `symbol` without `$` delimiters.
5. **Visualisation** — one entry per included figure. Use sequential ids: `5a`, `5b`, `5c`, … Assign ids in figure order. No count limit — include every figure that passes the triage rules above.

**Do not** include a key-results or benchmarks section.

**Slug:** use the slug from `comprehend prepare` (typically `arxiv-<id-with-dashes>`).

**Tags:** infer 1–5 tags from the paper content when writing `summary.json`. Tags are **not** stored in `papers.yaml`. Choose only from the allowed vocabulary — run `uv run comprehend tags` to list valid slugs. Pick the most specific tags that describe the paper's methods and task (e.g. `neural-rendering`, `object-detection`, `contrastive-learning`). Do not invent new tag slugs.

**Keywords:** add a `keywords` array with 5–15 paper-specific terms (method name, core modules, losses, datasets when central to the method). These are auto-bolded in **problem**, **solution**, and **key concepts** during assembly. Examples: `"RT-DETR"`, `"shifted-window attention"`, `"volume rendering"`, `"distillation token"`.

- Prefer `keywords` for recurring terms; use inline `**...**` in bullets for one-off emphasis.
- Reserve `**4a**` / `(5a)` only for cross-references to math or visuals — do not list ref ids in `keywords`.
- Do not bold every noun; emphasize terms a reader needs to track across sections.

## Step 2 — Agent 2: Visualizer

Read `summary.json` and `figures.json`. Render **every** visual listed in the summary:

| type | when to use | how |
|------|-------------|-----|
| `extract` | paper figure is clear and needs no simplification | set `page` and `figure_number` (preferred), or `xref` |
| `mermaid` | flowcharts, token/data flow, architecture simplified | write `.mmd` file, set `mermaid_source` in JSON or render separately |
| `manim` | math-heavy layouts, matrices, coordinate diagrams | write scene `.py`, set `manim_scene_path` and `manim_scene_class` |

**Decision rule:** `extract` when the paper figure is clear and passes triage; `mermaid` or `manim` only when simplification or annotation is needed and no suitable paper figure exists.

For `extract` visuals, prefer `figure_number` from `figures.json` → `figure_regions`. Paper figures are usually composites of many embedded images and vector paths; extracting a single `xref` tile crops the figure. When only `xref` is available, rendering still resolves the full composite region automatically.

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
uv run comprehend pdf crop paper.pdf --page 4 --figure 4 --output assets/<slug>-5a.png
```

Manim renders **static PNG only** (never video). For multi-step ideas, use multiple static frames as separate visuals.

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

Where:
- $\mathcal{L}$ — distillation loss
- $p_t$ — teacher softmax probabilities

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

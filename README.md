# comprehend

Turn ML paper PDFs into structured, visual summaries and publish them to a GitHub wiki.

**comprehend** is an agent-native toolkit: a Python CLI handles PDF download, figure extraction, visual rendering, and wiki publishing, while a [Cursor skill](.cursor/skills/comprehend-paper/SKILL.md) guides agents through writing the summary content.

## What you get

Each summary follows a fixed template designed for quick understanding:

1. **Problem** — what gap the paper addresses  
2. **Solution** — how the paper solves it (with cross-refs like **4a**, **5a**)  
3. **Key concepts** — theoretical explanations tied to the paper's contributions  
4. **Math** — central equations in LaTeX  
5. **Visualisation** — paper figures and generated diagrams that explain the method (no count limit)

Cross-references in the text become jump links to equations and visuals on the wiki page.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment management
- Git with SSH access to your GitHub wiki (`git@github.com:owner/repo.wiki.git`)
- GitHub wiki enabled on the target repository

Optional (for generated visuals):

- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) — `npm install -g @mermaid-js/mermaid-cli` (requires Chrome/Puppeteer)
- Manim — `uv sync --extra manim` (requires LaTeX, FFmpeg, Cairo)

## Installation

```bash
git clone git@github.com:dkosowski87/comprehend.git
cd comprehend
uv sync
```

With Manim support:

```bash
uv sync --extra manim
```

## Quick start

### 1. Prepare a paper

Accepts arXiv abstract URLs or direct PDF links:

```bash
uv run comprehend prepare https://arxiv.org/abs/2012.12877
```

This downloads the PDF, extracts text and figure metadata, and checks whether the summary already exists on the wiki. Output is cached under `.comprehend/papers/<slug>/`.

If `"already_published": true`, stop — the page is already on the wiki.

### 2. Write the summary

Use the [comprehend-paper skill](.cursor/skills/comprehend-paper/SKILL.md) in Cursor (recommended), or write `.comprehend/papers/<slug>/summary.json` by hand. See [Summary schema](#summary-schema) below.

### 3. Render visuals

```bash
uv run comprehend render summary .comprehend/papers/<slug>/summary.json \
  --pdf-path .comprehend/papers/<slug>/paper.pdf \
  --assets-dir .comprehend/papers/<slug>/assets
```

### 4. Publish to GitHub wiki

```bash
uv run comprehend wiki publish .comprehend/papers/<slug>/summary.json \
  --assets-dir .comprehend/papers/<slug>/assets \
  --repo owner/repo
```

If `--repo` is omitted, comprehend infers it from the local git remote.

To overwrite an existing wiki page:

```bash
uv run comprehend wiki publish ... --force
```

## Paper queue

Maintain a list of papers in `papers.yaml`:

```yaml
papers:
  - url: https://arxiv.org/abs/2304.08069
    slug: arxiv-2304-08069
    title: DETRs Beat YOLOs on Real-time Object Detection
```

Each entry includes an explicit **`slug`** (wiki page id) and **`title`** (display name). **Tags** are inferred when the summary is written and stored in `summary.json` — see `uv run comprehend tags` for the allowed vocabulary (max 5).

Queue commands:

```bash
uv run comprehend queue status    # pending vs published
uv run comprehend queue next      # next pending paper (downloads + extracts)
uv run comprehend queue run       # prepare all pending papers
```

Papers already on the wiki are skipped automatically.

### Import from paperswithcode.co

Browse CVPR/ICCV proceedings on [paperswithcode.co](https://paperswithcode.co/conferences) and import papers into `papers.yaml`:

```bash
# List conferences
uv run comprehend pwc conferences

# Browse CVPR 2026 oral papers
uv run comprehend pwc papers cvpr-2026 --presentation oral

# Append new oral papers to papers.yaml (skips duplicates)
uv run comprehend pwc import cvpr-2026 --presentation oral

# Preview without writing
uv run comprehend pwc import cvpr-2026 --presentation oral --dry-run
```

Presentation filters: `all`, `oral`, `spotlight`, `outstanding`.

## CLI reference

| Command | Description |
|---------|-------------|
| `comprehend tags` | List allowed topic tags for `summary.json` (max 5) |
| `comprehend prepare <url>` | Download PDF, extract text, check wiki dedup |
| `comprehend assemble <summary.json> --output page.md` | Build wiki markdown from JSON |
| `comprehend wiki publish <summary.json> --assets-dir <dir>` | Push page + assets to wiki |
| `comprehend wiki exists <slug>` | Check if a wiki page exists |
| `comprehend pdf download <url>` | Download PDF only |
| `comprehend pdf extract <path>` | Extract text from a local PDF |
| `comprehend pdf crop <path> --page N --output out.png` | Render a PDF page or figure to PNG |
| `comprehend render mermaid <file.mmd> --output out.png` | Render a Mermaid diagram |
| `comprehend render manim <scene.py> --scene-class Name --output out.png` | Render a Manim scene to PNG |
| `comprehend render summary <summary.json> --assets-dir <dir>` | Render all visuals in a summary |
| `comprehend queue add <url>` | Append a paper URL to papers.yaml |
| `comprehend pwc conferences` | List conferences on paperswithcode.co |
| `comprehend pwc papers <slug>` | List papers for a conference (`--presentation oral`) |
| `comprehend pwc import <slug>` | Import conference papers into papers.yaml |

Run `uv run comprehend <command> --help` for full options.

## Summary schema

Agent-written `summary.json` follows this structure:

```json
{
  "title": "Paper title",
  "pdf_url": "https://arxiv.org/pdf/....pdf",
  "tags": ["transformers", "object-detection"],
  "slug": "arxiv-2012-12877",
  "keywords": ["DeiT", "distillation token", "attention distillation"],
  "problem": ["..."],
  "solution": ["Use **5a** for architecture, loss **4a**."],
  "key_concepts": ["..."],
  "math": [
    {
      "id": "4a",
      "label": "soft distillation",
      "latex": "\\mathcal{L} = ...",
      "variables": [
        {"symbol": "\\mathcal{L}", "meaning": "distillation loss"}
      ]
    }
  ],
  "visuals": [
    {
      "id": "5a",
      "caption": "NeRF rendering pipeline",
      "type": "extract",
      "description": "...",
      "page": 3,
      "figure_number": 2
    },
    {
      "id": "5b",
      "caption": "Model architecture",
      "type": "extract",
      "description": "...",
      "page": 4,
      "figure_number": 3
    }
  ]
}
```

Visual types:

| Type | When to use |
|------|-------------|
| `extract` | Paper figure is clear — set `page` and `figure_number` (preferred), or `xref` |
| `mermaid` | Flowcharts, token/data flow — set `mermaid_source` |
| `manim` | Math-heavy diagrams — set `manim_scene_path` and `manim_scene_class` |

**Figure selection:** include process visualisations, architecture diagrams, and methodology plots that connect to the problem, solution, key concepts, or math. Skip qualitative results, benchmark plots, ablations, and dataset samples. See the [comprehend-paper skill](.cursor/skills/comprehend-paper/SKILL.md) for full triage rules. There is no visual count limit.

Cross-references like `**4a**` or `(5a)` in section bullets are automatically turned into jump links when matching math/visual ids exist. Terms in `keywords` are auto-bolded in section bullets during assembly.

**Tags** in `summary.json` must come from the fixed CV vocabulary (`uv run comprehend tags`); at most 5 per summary.

## Agent workflow (Cursor)

The project includes a Cursor skill at `.cursor/skills/comprehend-paper/SKILL.md` that orchestrates a 2-agent pipeline:

1. **Reader/Writer** — reads the PDF text, triages figures, writes `summary.json`  
2. **Visualizer** — renders all PNGs via extract / Mermaid / Manim  
3. **Publish** — pushes to the GitHub wiki  

The skill can be used manually in Cursor or wired into a **Cursor Automation** (see below).

## Daily automation (Cursor)

A scheduled automation can process one paper per day from `papers.yaml` and post the wiki link to Slack.

**Prompt:** copy from [`.cursor/automations/daily-paper-summary.prompt.md`](.cursor/automations/daily-paper-summary.prompt.md)

| Setting | Value |
|---------|-------|
| Schedule | Daily at 8:00 (`0 8 * * *`) — adjust in the Automations editor |
| Repository | `dkosowski87/comprehend`, branch `main` |
| Tools | Post to Slack |
| Runtime | **Local** (recommended — wiki SSH, optional Manim/Mermaid) |
| Skill | Enable **comprehend-paper** for the agent |

**Slack:** pick the destination channel in the Automations editor (channel or DM).

**Wiki link format:** `https://github.com/dkosowski87/comprehend/wiki/<slug>`

If the queue is empty or the paper is already published, the automation posts a short Slack status and exits.

## Wiki setup

1. Enable wikis: **Repository → Settings → Features → Wikis**
2. Create an initial wiki page (this initializes the wiki git repo)
3. Ensure SSH access works:

   ```bash
   git ls-remote git@github.com:owner/repo.wiki.git
   ```

Wiki pages are stored at `https://github.com/owner/repo/wiki`. An index of all summaries is maintained in `Home.md`. Concept pages use the `concept-*` prefix and are listed in `Concepts.md`.

## Concept explanations (manual)

For concepts used in a paper but not fully explained (e.g. **cyclic shift** in Swin Transformer), pass the paper wiki **slug** and **concept id** in the prompt — do **not** declare concepts in `papers.yaml`. The paper must still be listed in `papers.yaml` (for PDF cache and triage).

### Prerequisites

1. **Paper summary published** — the wiki page `arxiv-2103-14030.md` must exist (run the comprehend-paper workflow first).
2. **Paper listed** in `papers.yaml` (URL, slug, title).

### Running the agent (Cursor)

Enable or invoke the **comprehend-concept** skill, then prompt with the slug and concept id:

```
/comprehend-concept

Explain cyclic_shift and link it from the Swin paper (arxiv-2103-14030).
Run prepare, triage, write concept.json, render, and publish.
```

Shorter prompt (when the skill is already attached):

> Explain **cyclic_shift** for the Swin paper (`arxiv-2103-14030`).

Optional link terms: pass `--term "cyclic shift"` on prepare/publish, or set `keywords` in `concept.json` (auto-bolded in the concept page and used as link-search terms at publish).

### CLI steps (agent runs these)

```bash
# 1. Validate paths and create cache dir
uv run comprehend concept prepare \
  --paper arxiv-2103-14030 \
  --concept cyclic_shift \
  --term "cyclic shift" \
  --term "shifted window"

# 1b. Optional: check if the concept comes from a cited paper (PANet, CCFF, …)
uv run comprehend concept triage \
  --paper arxiv-2304-08069 \
  --concept ccff \
  --term "cross-scale feature fusion" \
  --term "CCFF"

# 2. Agent: web search + read paper wiki/summary → write concept.json
#    → .comprehend/concepts/cyclic-shift/concept.json

# 3. Render one visual
uv run comprehend concept render .comprehend/concepts/cyclic-shift/concept.json \
  --assets-dir .comprehend/concepts/cyclic-shift/assets

# 4. Publish concept page and link first mention in paper wiki
uv run comprehend concept publish .comprehend/concepts/cyclic-shift/concept.json \
  --paper arxiv-2103-14030 \
  --assets-dir .comprehend/concepts/cyclic-shift/assets
```

`concept render` and `concept publish` require `concept.json` to exist — the agent must write it in step 2.

Concept pages use the same **Math** section pattern as paper summaries: put LaTeX in a `math` array (`m1`, `m2`, …) and reference equations in bullets with `**m1**` — do not use inline `\(...\)` in prose (GitHub wiki does not render it).

### Check `prepare` output before starting

| Field | Meaning |
|-------|---------|
| `concept_already_published: false` | Proceed with a new concept page |
| `paper_already_links_concept: true` | Already linked — nothing to do |
| Error: paper wiki must exist | Publish the paper summary first |
| `paper_summary_path: null` | OK — agent can read the paper wiki page instead |

**Triage** (`concept triage`) classifies concepts as `simple` vs `paper_originated` using the cached PDF bibliography. If the origin paper is not in `papers.yaml`, the agent should ask before running `queue add`. See the **comprehend-concept** skill.

### Behavior

- Links the **first mention** of the term in the paper wiki page
- If the concept page already exists (from another paper), **only patches links** — does not overwrite the concept page
- Use `--force` on `concept publish` to overwrite an existing concept page
- Concept wiki URL: `https://github.com/<owner>/<repo>/wiki/concept-cyclic-shift`

Skill: [`.cursor/skills/comprehend-concept/SKILL.md`](.cursor/skills/comprehend-concept/SKILL.md)

## Development

```bash
uv sync --extra dev
uv run pytest
```

## Project layout

```
comprehend/
├── pdf/          # download, text/figure extraction
├── summary/      # schema, markdown assembly, cross-ref linkify
├── render/       # extract, mermaid, manim → PNG
├── publish/      # GitHub wiki clone, push, dedup
├── prepare.py    # download + extract workflow
├── queue.py      # papers.yaml loading
├── pwc/          # paperswithcode.co API client + queue import
├── concept/      # concept schema, link patching, prepare
└── cli.py        # click CLI
papers.yaml       # paper queue
.cursor/skills/comprehend-paper/SKILL.md
.cursor/skills/comprehend-concept/SKILL.md
.cursor/automations/daily-paper-summary.prompt.md
```

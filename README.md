# comprehend

Turn ML paper PDFs into structured, visual summaries and publish them to a GitHub wiki.

**comprehend** is an agent-native toolkit: a Python CLI handles PDF download, figure extraction, visual rendering, and wiki publishing, while a [Cursor skill](.cursor/skills/comprehend-paper/SKILL.md) guides agents through writing the summary content.

## What you get

Each summary follows a fixed template designed for quick understanding:

1. **Problem** — what gap the paper addresses  
2. **Solution** — how the paper solves it (with cross-refs like **4a**, **5a**)  
3. **Key concepts** — theoretical explanations tied to the paper's contributions  
4. **Math** — central equations in LaTeX  
5. **Visualisation** — 1–2 figures (extracted from the PDF or generated)

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
  - url: https://arxiv.org/abs/2012.12877
    tags: [vision, transformers, distillation]
```

Queue commands:

```bash
uv run comprehend queue status    # pending vs published
uv run comprehend queue next      # next pending paper (downloads + extracts)
uv run comprehend queue run       # prepare all pending papers
```

Papers already on the wiki are skipped automatically.

## CLI reference

| Command | Description |
|---------|-------------|
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

Run `uv run comprehend <command> --help` for full options.

## Summary schema

Agent-written `summary.json` follows this structure:

```json
{
  "title": "Paper title",
  "pdf_url": "https://arxiv.org/pdf/....pdf",
  "tags": ["tag1", "tag2"],
  "slug": "arxiv-2012-12877",
  "problem": ["..."],
  "solution": ["Use **5a** for architecture, loss **4a**."],
  "key_concepts": ["..."],
  "math": [
    {"id": "4a", "label": "soft distillation", "latex": "\\mathcal{L} = ..."}
  ],
  "visuals": [
    {
      "id": "5a",
      "caption": "Architecture overview",
      "type": "extract",
      "description": "...",
      "page": 7
    }
  ]
}
```

Visual types:

| Type | When to use |
|------|-------------|
| `extract` | Paper figure is clear — set `page`, optional `xref` or `clip` |
| `mermaid` | Flowcharts, token/data flow — set `mermaid_source` |
| `manim` | Math-heavy diagrams — set `manim_scene_path` and `manim_scene_class` |

Maximum **2 visuals** per summary.

Cross-references like `**4a**` or `(5a)` in section bullets are automatically turned into jump links when matching math/visual ids exist.

## Agent workflow (Cursor)

The project includes a Cursor skill at `.cursor/skills/comprehend-paper/SKILL.md` that orchestrates a 2-agent pipeline:

1. **Reader/Writer** — reads the PDF text, writes `summary.json`  
2. **Visualizer** — renders 1–2 PNGs via extract / Mermaid / Manim  
3. **Publish** — pushes to the GitHub wiki  

The skill can be used manually in Cursor or wired into a [Cursor Automation](https://docs.cursor.com) that runs `comprehend queue next` on a schedule.

## Wiki setup

1. Enable wikis: **Repository → Settings → Features → Wikis**
2. Create an initial wiki page (this initializes the wiki git repo)
3. Ensure SSH access works:

   ```bash
   git ls-remote git@github.com:owner/repo.wiki.git
   ```

Wiki pages are stored at `https://github.com/owner/repo/wiki`. An index of all summaries is maintained in `Home.md`.

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
└── cli.py        # click CLI
papers.yaml       # paper queue
.cursor/skills/comprehend-paper/SKILL.md
```

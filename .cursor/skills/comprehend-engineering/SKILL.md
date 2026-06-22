---
name: comprehend-engineering
description: >-
  Summarize MLE library documentation and tutorials into structured GitHub wiki
  pages with code snippets and generated diagrams. Use when processing
  engineering.yaml, running comprehend engineering queue, or writing engineering
  summaries for CUDA, PyTorch, TensorRT, Triton, ONNX, and related tools.
---

# Comprehend — Engineering Summaries

Turn a documentation or tutorial URL into a concise wiki summary with short code examples and generated diagrams, published to the **Engineering** section of this repository's GitHub wiki.

## Workflow overview

Use a **2-agent pipeline** orchestrated by the main agent:

1. **Prepare** — run CLI, check deduplication
2. **Agent 1 (Reader/Writer)** — read extracted docs text, write `summary.json`
3. **Agent 2 (Visualizer)** — render Mermaid/Manim visuals in `summary.json`
4. **Publish** — assemble markdown and push to wiki (`Engineering.md` index)

Retry solvable errors up to **3 times** (network, mmdc/Manim failures). After 3 failures, stop **without publishing**.

## Step 0 — Prepare and deduplicate

```bash
uv run comprehend engineering prepare <url> --topic <topic>
```

If `"already_published": true`, **stop immediately**.

For queue-driven runs:

```bash
uv run comprehend engineering queue next
uv run comprehend engineering queue status
```

Save outputs under `.comprehend/engineering/<slug-without-prefix>/`:
- `source.html`, `text.txt`
- `summary.json` (Agent 1 output)
- `assets/` (Agent 2 output)

## Step 1 — Agent 1: Reader/Writer

Read `.comprehend/engineering/<dir>/text.txt` (extracted documentation body).

### Writing style

Engineering summaries are **shorter than paper summaries**. Prefer one clear sentence per bullet when that is enough. Do not pad sections to match paper length.

**Sections:**

1. **Problem** — what gap, pain point, or question this doc addresses (1–3 bullets).
2. **Solution** — how the tool/API addresses it (2–4 bullets). Use cross-reference ids (`**4a**`, `(3a)`) where helpful.
3. **Key concepts** — terminology and mental models from the doc (2–5 bullets). Explain APIs, memory models, compilation stages, etc. in plain language.
4. **Code examples** — **1–2** short snippets (max ~20–30 lines each). Show realistic usage of functions, decorators, or APIs from the doc. Pseudocode is acceptable when it clarifies the idea better than boilerplate.
5. **Visualisation** — **1–2** diagrams explaining system interaction, code paths, API routing, memory hierarchy, or compilation flow.

**Do not** include a Math section.

**Do not** extract figures from documentation — generate diagrams instead.

### Visual triage

Default to **1 diagram**; add a second only when it teaches a distinct idea (e.g. runtime flow **and** memory layout).

| type | when to use |
|------|-------------|
| `mermaid` | flowcharts, API call sequences, module graphs, deployment pipelines |
| `manim` | layered diagrams, memory layouts, tensor shapes when spatial layout matters |

**Never** use `extract` for engineering summaries.

Write `.comprehend/engineering/<dir>/summary.json`:

```json
{
  "title": "PyTorch CUDA Semantics",
  "source_url": "https://pytorch.org/docs/stable/notes/cuda.html",
  "topic": "pytorch",
  "tags": ["pytorch", "cuda"],
  "slug": "engineering-pytorch-cuda-semantics",
  "keywords": ["CUDA stream", "device", "non-blocking", "pin_memory"],
  "problem": [
    "CPU and GPU execution are asynchronous; naive timing and copies hide real bottlenecks."
  ],
  "solution": [
    "PyTorch exposes **device** placement, **streams**, and explicit **synchronize** points so host code can overlap transfers and kernels (see **4a**)."
  ],
  "key_concepts": [
    "**CUDA stream** — ordered queue of GPU work issued from the host.",
    "**non-blocking** copies require pinned host memory to overlap safely with compute."
  ],
  "code_examples": [
    {
      "id": "3a",
      "title": "Move a tensor to GPU and synchronize",
      "language": "python",
      "code": "import torch\n\ndevice = torch.device(\"cuda\")\nx = torch.randn(1024, device=device)\ntorch.cuda.synchronize()"
    }
  ],
  "visuals": [
    {
      "id": "4a",
      "caption": "Host issues kernels and copies on a CUDA stream",
      "type": "mermaid",
      "description": "CPU thread enqueues copy and matmul; GPU executes asynchronously",
      "refs": ["3a"],
      "mermaid_source": "sequenceDiagram\n  participant CPU\n  participant GPU\n  CPU->>GPU: copy_(host to device)\n  CPU->>GPU: matmul kernel\n  CPU->>GPU: synchronize()"
    }
  ]
}
```

### Summary rules

**Language:** English only.

**Slug:** use the slug from `comprehend engineering prepare` or `queue next` (prefix `engineering-`).

**Topic:** primary topic from `engineering.yaml` — one of: `cuda`, `pytorch`, `tensorrt`, `triton`, `onnx`, `algorithms`. Must match the queue entry.

**Tags:** infer 1–5 tags from the allowed topic vocabulary when writing `summary.json`. Run `uv run comprehend engineering topics` to list valid slugs. Include the primary `topic` in `tags`. Do not invent new tag slugs.

**Keywords:** add 5–12 tool-specific terms (API names, classes, flags). Auto-bolded in Problem/Solution/Key concepts during assembly.

**Code examples:** ids `3a`, `3b` (section 4 in wiki). Keep snippets focused — imports + the one idea, not full applications.

**Visuals:** ids `4a`, `4b` (section 5 in wiki). Set `mermaid_source` inline or write a `.mmd` file and reference it when iterating.

## Step 2 — Agent 2: Visualizer

Read `summary.json`. Render **every** visual:

```bash
uv run comprehend engineering render .comprehend/engineering/<dir>/summary.json \
  --assets-dir .comprehend/engineering/<dir>/assets
```

Individual tools when iterating:

```bash
uv run comprehend render mermaid diagram.mmd --output assets/<slug>-4a.png
uv run comprehend render manim scene.py --scene-class MyScene --output assets/<slug>-4a.png
```

Manim renders **static PNG only** (never video).

## Step 3 — Publish

```bash
uv run comprehend engineering assemble .comprehend/engineering/<dir>/summary.json \
  --output .comprehend/engineering/<dir>/page.md

uv run comprehend engineering wiki publish .comprehend/engineering/<dir>/summary.json \
  --assets-dir .comprehend/engineering/<dir>/assets
```

Publishing skips if the wiki page already exists (default). Never force-republish unless instructed.

Published pages are indexed in **`Engineering.md`** (not `Papers.md`).

## Wiki markdown template

```markdown
# {Title}

**Source:** [{source_url}]({source_url})
**Topic:** `{topic}`
**Tags:** `tag1`, `tag2`

## 1. Problem
- ...

## 2. Solution
- ...

## 3. Key concepts
- ...

## 4. Code examples

<a id="3a"></a>

**3a** {title}:
```python
...
```

## 5. Visualisation

<a id="4a"></a>

### 4a — {caption}
![4a](assets/{slug}-4a.png)
```

## Retry policy

Retry up to **3 times** when:
- Documentation download fails (network)
- Manim or mmdc render fails (fix scene/diagram and retry)
- Wiki git push fails (transient)

Do **not** publish partial summaries. On final failure, report the error and leave the wiki unchanged.

## Queue automation

```bash
uv run comprehend engineering queue run
uv run comprehend engineering queue next
uv run comprehend engineering queue status
```

Process each pending resource through the full 2-agent pipeline.

## Dependencies

Core: `uv sync`

Optional visuals:
- Manim: `uv sync --extra manim`
- Mermaid: `npm install -g @mermaid-js/mermaid-cli`

GitHub wiki must be enabled on the repository.

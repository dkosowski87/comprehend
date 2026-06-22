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

If `queue next` returned `secondary_urls`, read those pages too (fetch in browser or via shell) before writing. They supplement — do not replace — the primary source.

### Primary source and supplementation

Every summary has a **primary URL** from `engineering.yaml` (`source_url` in `summary.json`). The prepare step extracts text from that URL only.

You may **supplement** with broader knowledge when it improves high-level understanding, especially for:

- Architecture / interaction diagrams (e.g. how streams, copy engines, and SMs relate)
- **When to use** guidance for inference platforms (datacenter GPU vs Jetson vs CPU)
- Links between adjacent official docs (cuBLAS under GEMM, TensorRT under CUDA graphs)

**Rules:**

1. **Anchor Problem/Solution in the primary doc** — read `text.txt` first; do not invent features absent from NVIDIA/PyTorch/vendor docs.
2. **`secondary_urls`** from the queue (when present) are approved extra reading — prefer them over ad-hoc search.
3. **Mark synthesis** — suffix bullets that are not directly from the primary page with *(synthesis)* or cite a secondary URL in the bullet.
4. **Official sources only** for factual claims (nvidia.com, pytorch.org, onnx.ai, triton-lang.org, apple.com, etc.). No blog posts unless listed in the queue.
5. **Diagrams** may combine ideas from multiple official sources; caption should reflect the mental model, not verbatim doc text.
6. If the primary page is too narrow, propose a better `url` in the queue — do not rely on synthesis for core definitions.

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
  "title": "CUDA Streams and Concurrent Execution",
  "source_url": "https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#asynchronous-concurrent-execution",
  "topic": "cuda",
  "tags": ["cuda"],
  "slug": "engineering-cuda-streams",
  "keywords": ["CUDA stream", "cudaStream_t", "default stream", "concurrent kernels"],
  "problem": [
    "Sequential kernel launches underutilize the GPU when copies and compute could overlap."
  ],
  "solution": [
    "CUDA **streams** queue host operations and device work so independent sequences run concurrently (see **4a**)."
  ],
  "key_concepts": [
    "**CUDA stream** — FIFO queue of device work issued from a host thread.",
    "Operations on different streams may overlap if resources allow *(synthesis)*.",
    "The default stream has legacy synchronization semantics; per-thread default stream avoids some implicit sync."
  ],
  "code_examples": [
    {
      "id": "3a",
      "title": "Create streams and enqueue async memcpy",
      "language": "cpp",
      "code": "cudaStream_t s1, s2;\ncudaStreamCreate(&s1);\ncudaStreamCreate(&s2);\ncudaMemcpyAsync(d_a, h_a, nbytes, cudaMemcpyHostToDevice, s1);\ncudaMemcpyAsync(d_b, h_b, nbytes, cudaMemcpyHostToDevice, s2);"
    }
  ],
  "visuals": [
    {
      "id": "4a",
      "caption": "Two streams overlapping H2D copies and kernels",
      "type": "mermaid",
      "description": "Stream s1 and s2 interleave copy and compute on the GPU timeline",
      "refs": ["3a"],
      "mermaid_source": "sequenceDiagram\n  participant H as Host\n  participant S1 as Stream 1\n  participant S2 as Stream 2\n  participant G as GPU\n  H->>S1: memcpyAsync\n  H->>S2: memcpyAsync\n  S1->>G: kernel A\n  S2->>G: kernel B"
    }
  ]
}
```

### Summary rules

**Language:** English only.

**Slug:** use the slug from `comprehend engineering prepare` or `queue next` (prefix `engineering-`).

**Topic:** primary topic from `engineering.yaml` — one of: `cuda`, `nvidia`, `apple`, `memory`, `camera`, `tensorrt`, `triton`, `algorithms`, `jetson`, `onnx`, `pytorch`. Must match the queue entry.

**Tags:** infer 1–5 tags from the allowed topic vocabulary (`uv run comprehend engineering topics`). Include the primary `topic`. You may add a **related** topic tag when the page clearly spans areas (e.g. `memory` for pinned host memory, `pytorch` + `cuda` for torch CUDA semantics). Do not invent tag slugs.

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

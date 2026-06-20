# Research Gap Agent

LangGraph pipeline that takes a research topic in natural language and tries
to find open research questions about it. It searches arXiv, OpenAlex, and
Semantic Scholar (open-access papers only), extracts insights from each
paper with an LLM, builds a citation/co-occurrence graph in parallel, and
finally combines both signals into a report.

## Pipeline

```
[topic]
   |
   v
query_rewriter ---+--> search -> ranker -> paper_extractor -> insight_extractor -> gap_identifier --+
                  |                                                                                    |
                  +--> graph_analyzer ---------------------------------------------------------> aggregator -> [report]
```

## How to run

### 1. Install

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

Copy the env template and fill in at least one API key:

```bash
cp .env.example .env
```

The default `config.yaml` uses NVIDIA for every LLM step, so the only
key you really need is `NVIDIA_API_KEY`. You can get one for free at
https://build.nvidia.com.

If you want to use OpenAI / Anthropic / Google / Groq instead, edit
`config.yaml` and put the matching key in `.env`. There is one block per
pipeline role (`query_rewriter`, `paper_extractor`, `gap_identifier`,
`aggregator`) plus a `default` block used as fallback.

For the reranker step, pick your provider in `config.yaml`:

| Provider | Type | Setup |
|---|---|---|
| `jina` (default) | API | Set `JINA_API_KEY` in `.env` — free tier at https://jina.ai/reranker/ |
| `langsearch` | API | Set `LANGSEARCH_API_KEY` in `.env` — generous daily free limit |
| `cross-encoder` | Local CPU | No API key needed — downloads `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80 MB) on first use |
| `bge` | Local GPU | No API key needed — downloads `BAAI/bge-reranker-v2-m3` (~2.3 GB) on first use. Falls back to CPU if no GPU available. Requires `pip install FlagEmbedding` |

You can also configure a fallback provider in case the primary fails:

```yaml
# config.yaml
reranker:
  provider_name: jina
  fallback: langsearch
```

The local rerankers require `sentence-transformers` (already in `requirements.txt`).
The GPU reranker also requires `FlagEmbedding` (added to `requirements.txt`).

For the document extraction step (PDF to markdown), pick your provider in `config.yaml`.
`pymupdf` is fast and runs locally on CPU, `marker` is a SOTA extractor but requires GPU,
`jina` is a middle-ground option with a free API key at https://jina.ai/reader/.

By default, when extracting arXiv papers the node first tries to fetch the HTML version
of the paper to cut down costs and avoid the PDF download quota. You can disable this
with `use_arxiv_html: false` in `config.yaml`.

### 3. Run

```bash
python -m research_gap_agent "Self-supervised learning for medical imaging"
```

Useful flags:

```bash
# verbose logs (per-source results, dedup stats, etc.)
python -m research_gap_agent -v "your topic"

# very verbose (debug-level)
python -m research_gap_agent -vv "your topic"

# write the report to a file instead of stdout
python -m research_gap_agent "your topic" --output report.md

# JSON output (good for piping into other tools)
python -m research_gap_agent --json "your topic" > report.json
```

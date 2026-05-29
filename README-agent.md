# Research Gap Agent

LangGraph pipeline that takes a research topic in natural language and tries
to find open research questions about it. It searches arXiv, OpenAlex, and
Semantic Scholar (open-access papers only), extracts insights from each
paper with an LLM, builds a citation/co-occurrence graph in parallel, and
finally combines both signals into a report.

The original BERTopic + FAISS POC (`build_index.py`, `query_system.py`,
`README.md`) is still in the repo and was not touched.

## Pipeline

```
[topic]
   |
   v
query_rewriter ---+--> search -> ranker -> paper_extractor -> gap_identifier --+
                  |                                                            |
                  +--> graph_analyzer ----------------------------------------> aggregator -> [report]
```

## How to run

### 1. Install

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements-agent.txt
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

For the reranker step, fill out `JINA_API_KEY`. You can get one for free at https://jina.ai/reranker/.
You can also fill out `LANGSEARCH_API_KEY`, that serves as a fallback to when you run out of Jina tokens, and provides
a more generous, daily, limit.

For the document extraction step (PDF to html), pick your provider in `config.yaml`. `pymupdf` is fast and runs locally on CPU, `marker` is a SOTA 
extractor, but requires GPU processing, `jina` is a middle-ground extractor, and provides a free api-key with generous limits at https://jina.ai/reader/. 
By default, when extracting papers from Arxiv, the node first tries to extract the HTML version of the paper to
cut down costs, checking if no errors ocurred in the PDF -> HTML conversion by Arxiv. You can disable this
with `use_arxiv_html: false` 

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

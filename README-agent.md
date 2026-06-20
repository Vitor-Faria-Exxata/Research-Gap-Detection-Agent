# Research Gap Agent

LangGraph pipeline that takes a research topic in natural language and tries
to find open research questions about it. It searches arXiv, OpenAlex, and
Semantic Scholar (open-access papers only), converts available documents,
builds a citation/co-occurrence graph in parallel, and identifies candidate
research gaps from structured article insights.

The current `paper_extractor` keeps converted `Paper` objects with `full_text`
in `extracted_documents` and separately initializes `extracted` with the
minimum `ExtractedInsights` metadata contract. Its analytical lists are
initialized empty; semantic extraction from `full_text` remains future work.

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

## Manual smoke tests for `gap_identifier`

Do not use the interactive Python REPL for these checks. Paste each block
directly into the shell so Python executes the whole snippet at once.

### 1. Empty structured insights

This validates the no-input branch. It must return
`no_extracted_insights`, `cutoff_date: null`, and zero gaps.

```bash
python - <<'PY'
from research_gap_agent.state import GraphState
from research_gap_agent.nodes.gap_identifier import gap_identifier_node

state = GraphState(
    initial_topic="Long-term reliability of AI agents",
    extracted=[],
)

result = gap_identifier_node(state)
print(result["gap_identification"].model_dump_json(indent=2))
PY
```

### 2. Structured positive path with stubbed LLM

This validates the main `gap_identifier` path without depending on any real
LLM provider. It builds two extracted insights, replaces `get_llm()` with a
local stub, runs the node once, and prints the structured result.

```bash
python - <<'PY'
from datetime import date

import research_gap_agent.nodes.gap_identifier as gap_identifier_module
from research_gap_agent.schemas import (
    CounterEvidence,
    ExtractedInsights,
    GapEvidence,
    GapIdentificationResult,
    IdentifiedGap,
)
from research_gap_agent.state import GraphState


class FakeStructuredLLM:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return GapIdentificationResult(
            cutoff_date=date(2025, 6, 1),
            gaps=[
                IdentifiedGap(
                    research_question=(
                        "How reliable are AI agents in long-running deployments?"
                    ),
                    description=(
                        "The extracted corpus covers short-term evaluation and"
                        " production monitoring, but still leaves long-duration"
                        " behavior weakly supported."
                    ),
                    evidence_strength=84,
                    evidence=[
                        GapEvidence(
                            paper_id="paper-1",
                            evidence_type="stated_limitations",
                            description="No longitudinal follow-up was reported.",
                        ),
                        GapEvidence(
                            paper_id="paper-2",
                            evidence_type="recurring_not_addressed",
                            description=(
                                "Cross-site longitudinal replication remains absent."
                            ),
                        ),
                    ],
                    rationale=(
                        "Multiple papers leave the same long-term deployment scope"
                        " unresolved."
                    ),
                    counter_evidence=[
                        CounterEvidence(
                            paper_id="paper-2",
                            description=(
                                "One study includes production monitoring, but not"
                                " long-duration replication."
                            ),
                        )
                    ],
                )
            ],
        )


gap_identifier_module.get_llm = lambda role: FakeStructuredLLM()

state = GraphState(
    initial_topic="Long-term reliability of AI agents",
    extracted=[
        ExtractedInsights(
            paper_id="paper-1",
            title="Paper One",
            published_date=date(2025, 1, 10),
            questions_answered=["Short-term agent evaluation"],
            methodologies=["Controlled benchmark"],
            not_addressed=["Long-term deployment"],
            stated_limitations=["No longitudinal follow-up"],
        ),
        ExtractedInsights(
            paper_id="paper-2",
            title="Paper Two",
            published_date=date(2025, 6, 1),
            questions_answered=["Production monitoring of agents"],
            methodologies=["Field study"],
            not_addressed=["Cross-site longitudinal replication"],
            stated_limitations=["Single-site sample"],
        ),
    ],
)

result = gap_identifier_module.gap_identifier_node(state)
print(result["gap_identification"].model_dump_json(indent=2))
PY
```

Expected result:

- `cutoff_date` must be `2025-06-01`
- one gap must be returned
- `paper_id` references must stay inside `paper-1` and `paper-2`
- no validation exception should be raised

### 3. Final report rendering

This validates `aggregator` + CLI rendering using the structured gap output.

```bash
python - <<'PY'
from datetime import date

from research_gap_agent.cli import render_report
from research_gap_agent.nodes.aggregator import aggregator_node
from research_gap_agent.schemas import (
    GapEvidence,
    GapIdentificationResult,
    GraphInsight,
    IdentifiedGap,
)
from research_gap_agent.state import GraphState

state = GraphState(
    initial_topic="Long-term reliability of AI agents",
    extracted=[],
    ranked_papers=[],
    graph_insight=GraphInsight(
        summary="Two evaluation themes remain disconnected."
    ),
    gap_identification=GapIdentificationResult(
        cutoff_date=date(2025, 6, 1),
        gaps=[
            IdentifiedGap(
                research_question=(
                    "How reliable are AI agents in long-running deployments?"
                ),
                description=(
                    "Long-duration behavior is still weakly supported in the"
                    " current textual corpus."
                ),
                evidence_strength=84,
                evidence=[
                    GapEvidence(
                        paper_id="paper-1",
                        evidence_type="stated_limitations",
                        description="No longitudinal follow-up was reported.",
                    )
                ],
                rationale=(
                    "The available evidence keeps pointing to short-horizon"
                    " evaluation."
                ),
            )
        ],
    ),
)

report = aggregator_node(state)["final_report"]
print(render_report(report))
PY
```

Expected result:

- the output must contain `## Candidate Research Gaps`
- the output must show `84/100`
- the output must show `_Cutoff date: 2025-06-01_`

### 4. Regression suite

After the smoke tests above, run the automated checks:

```bash
pytest tests/test_gap_identifier_pipeline_integration.py -q
pytest -q
```

# Gap Identifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the LLM-oriented `gap_identifier` contract, its post-LLM integrity validation, and the minimum downstream adaptations required by `docs/prd/gap-identifier.md`.

**Architecture:** Shared Pydantic models define structured paper insights, candidate gaps, warnings, and the enclosing result. The node assembles one corpus-level prompt, makes exactly one structured-output LLM call, then applies a pure referential-integrity validator before storing the result in `GraphState.gap_identification`. The aggregator and CLI consume the validated object without adding graph fusion or ranking.

**Tech Stack:** Python 3.13, Pydantic 2, LangChain structured output, LangGraph state, pytest, `unittest.mock`.

---

### Task 1: Shared Contracts, State, and Test Isolation

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_gap_identifier_schemas.py`
- Create: `tests/test_state_contract.py`
- Modify: `research_gap_agent/__init__.py`
- Modify: `research_gap_agent/nodes/__init__.py`
- Modify: `research_gap_agent/schemas.py`
- Modify: `research_gap_agent/state.py`

- [x] **Step 1: Write failing schema and state tests**

Cover:

```python
def test_extracted_insights_requires_title_and_published_date(): ...
def test_identified_gap_accepts_only_documented_evidence_types(): ...
def test_identified_gap_rejects_scores_outside_70_to_100(): ...
def test_gap_identification_allows_null_cutoff_date(): ...
def test_state_preserves_extracted_and_gap_identification(): ...
```

Use a fixture equivalent to:

```python
ExtractedInsights(
    paper_id="paper-1",
    title="Paper One",
    published_date=date(2025, 1, 2),
    questions_answered=[],
    methodologies=[],
    not_addressed=["Longitudinal evaluation"],
    stated_limitations=[],
)
```

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
/private/tmp/research-gap-agent-venv/bin/python -m pytest \
  tests/test_gap_identifier_schemas.py tests/test_state_contract.py -q
```

Expected: collection or assertion failures because the new contracts and state field do not exist.

- [x] **Step 3: Implement minimal contracts**

Add:

```python
EvidenceType = Literal[
    "stated_limitations",
    "recurring_not_addressed",
    "contrast",
]

class GapWarning(BaseModel):
    code: str
    message: str

class CounterEvidence(BaseModel):
    paper_id: str
    description: str

class GapEvidence(BaseModel):
    paper_id: str
    evidence_type: EvidenceType
    description: str

class IdentifiedGap(BaseModel):
    research_question: str
    description: str
    evidence_strength: int = Field(..., ge=70, le=100)
    evidence: list[GapEvidence] = Field(default_factory=list)
    rationale: str
    counter_evidence: list[CounterEvidence] = Field(default_factory=list)

class GapIdentificationResult(BaseModel):
    cutoff_date: date | None
    warnings: list[GapWarning] = Field(default_factory=list)
    gaps: list[IdentifiedGap] = Field(default_factory=list)
```

Extend `ExtractedInsights` with required `title` and `published_date`. Replace `GraphState.content_gaps` with optional `gap_identification`.

Make package and node exports lazy with module `__getattr__` so importing schemas and focused nodes does not eagerly require optional graph-analysis dependencies.

- [x] **Step 4: Add the development runner**

Create:

```text
-r requirements-agent.txt
pytest
```

- [x] **Step 5: Run tests and verify GREEN**

Run the focused tests, then:

```bash
/private/tmp/research-gap-agent-venv/bin/python -m pytest -q
```

### Task 2: Prompt Assembly, Referential Validation, and Node

**Files:**
- Create: `research_gap_agent/prompts/gap_identifier.py`
- Create: `tests/test_gap_identifier_prompt.py`
- Create: `tests/test_gap_identifier_validation.py`
- Create: `tests/test_gap_identifier_node.py`
- Modify: `research_gap_agent/nodes/gap_identifier.py`

- [x] **Step 1: Write failing prompt tests**

Verify the returned messages contain:

```python
assert topic in rendered
assert "paper-1" in rendered and "paper-2" in rendered
assert "stated_limitations" in rendered
assert "recurring_not_addressed" in rendered
assert "contrast" in rendered
assert "evidence_strength >= 70" in rendered
assert "graph evidence" in rendered.lower()
assert "full_text" not in rendered
```

- [x] **Step 2: Write failing validator tests**

Cover:

```python
def test_keeps_valid_gap_unchanged(): ...
def test_discards_only_gap_without_evidence_and_warns(): ...
def test_discards_only_gap_with_unknown_evidence_reference_and_warns(): ...
def test_removes_only_unknown_counter_evidence_and_warns(): ...
```

The validator signature is:

```python
def validate_gap_identification(
    result: GapIdentificationResult,
    extracted_insights: list[ExtractedInsights],
) -> GapIdentificationResult:
    ...
```

It must not recalculate `cutoff_date` or `evidence_strength`.
It must ignore model-authored warnings, generate validation warnings
deterministically, and reject a null `cutoff_date` when insights are present.

- [x] **Step 3: Write failing node tests**

Cover:

```python
def test_empty_input_skips_llm_and_returns_structured_warning(): ...
def test_non_empty_input_makes_exactly_one_structured_llm_call(): ...
def test_all_insights_are_sent_in_the_same_request(): ...
def test_validated_result_is_written_to_gap_identification(): ...
def test_non_empty_input_rejects_null_cutoff_date(): ...
```

Use a fake chain that records `with_structured_output()` and `invoke()` calls and returns deterministic Pydantic output.

- [x] **Step 4: Run focused tests and verify RED**

Run:

```bash
/private/tmp/research-gap-agent-venv/bin/python -m pytest \
  tests/test_gap_identifier_prompt.py \
  tests/test_gap_identifier_validation.py \
  tests/test_gap_identifier_node.py -q
```

- [x] **Step 5: Implement prompt and node**

Expose:

```python
def build_gap_identifier_messages(
    topic: str,
    extracted_insights: list[ExtractedInsights],
) -> list[tuple[str, str]]:
    ...
```

Serialize every insight with `model_dump(mode="json")` into one human message. Put domain, evidence, scoring, cutoff-date, JSON-only, and no-graph rules in the system message.

For empty input return:

```python
GapIdentificationResult(
    cutoff_date=None,
    warnings=[GapWarning(
        code="no_extracted_insights",
        message="No structured article insights were available for gap identification.",
    )],
    gaps=[],
)
```

For non-empty input:

```python
llm = get_llm("gap_identifier").with_structured_output(
    GapIdentificationResult
)
raw_result = llm.invoke(messages)
validated = validate_gap_identification(raw_result, state.extracted)
return {"gap_identification": validated}
```

The prompt requires the LLM to return `warnings: []`. The validator discards
model-authored warnings, creates processing warnings deterministically, and
requires non-null `cutoff_date` whenever `state.extracted` is non-empty.

- [x] **Step 6: Run focused and full tests and verify GREEN**

### Task 3: Aggregator and Final Renderer Compatibility

**Files:**
- Create: `tests/test_aggregator.py`
- Create: `tests/test_cli.py`
- Modify: `research_gap_agent/schemas.py`
- Modify: `research_gap_agent/nodes/aggregator.py`
- Modify: `research_gap_agent/cli.py`

- [x] **Step 1: Write failing aggregator tests**

Verify that `FinalReport` receives:

```python
assert report.gaps == gap_result.gaps
assert report.cutoff_date == gap_result.cutoff_date
assert report.warnings == gap_result.warnings
```

Also cover a valid empty `GapIdentificationResult`.

- [x] **Step 2: Write failing renderer tests**

Verify Markdown includes research question, description, score, rationale, each structured evidence item, derived support IDs, counterevidence, cutoff date, and warnings. Verify the empty-gap case does not access obsolete `evidence: str` or `supporting_paper_ids`.

- [x] **Step 3: Run focused tests and verify RED**

- [x] **Step 4: Adapt the report contract and consumers**

Extend:

```python
class FinalReport(BaseModel):
    topic: str
    cutoff_date: date | None
    warnings: list[GapWarning]
    gaps: list[IdentifiedGap]
    summary: str
    methodology_note: str
    sources_used: list[SourceName]
    papers_considered: int
```

The aggregator copies `gaps`, `cutoff_date`, and `warnings` from `state.gap_identification`. It does not merge graph niches or call an LLM.

- [x] **Step 5: Run focused and full tests and verify GREEN**

### Task 4: Integration Verification and Documentation Consistency

**Files:**
- Modify only if required by verified failures: `research_gap_agent/graph.py`, `README-agent.md`

- [x] **Step 1: Run the complete unit suite**

```bash
/private/tmp/research-gap-agent-venv/bin/python -m pytest -q
```

- [x] **Step 2: Run compile/import checks**

```bash
/private/tmp/research-gap-agent-venv/bin/python -m compileall -q research_gap_agent tests
/private/tmp/research-gap-agent-venv/bin/python -c \
  "from research_gap_agent.schemas import GapIdentificationResult; from research_gap_agent.nodes.gap_identifier import gap_identifier_node"
```

- [x] **Step 3: Review PRD coverage**

Confirm:

- exactly zero calls for empty input;
- exactly one call for non-empty input;
- all insights are in one request;
- no code-side score or cutoff recalculation;
- non-empty input requires a non-null `cutoff_date`;
- LLM warnings are ignored and processing warnings are generated
  deterministically;
- missing/invalid evidence removes only the affected gap;
- invalid counterevidence removes only that item;
- `extracted` remains in state beside `gap_identification`;
- aggregator and renderer consume the new structured contract;
- no graph fusion, network test, GitHub publication, commit, or push was added.

- [x] **Step 4: Run independent spec and quality reviews**

Dispatch separate reviewers against `docs/prd/gap-identifier.md` and the final diff. Fix all critical and important findings, then rerun the full verification commands.

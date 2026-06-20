# PRD: Aggregator orientado por LLM com `FinalReport` estruturado

## Problem Statement

O `aggregator` atual ainda funciona como um montador deterministico. Ele copia
as lacunas produzidas pelo `gap_identifier`, usa o resumo do grafo como texto
de apoio e não faz fusao semantica real entre lacunas textuais e sinais do
grafo.

Isso deixa o ultimo passo do pipeline incompleto. O bloco que deveria
consolidar a resposta final nao exprime a origem de cada lacuna, nao preserva o
grafo usado na fusao e nao produz um `FinalReport` estruturado por LLM. Sem
esse passo, o agente ainda nao entrega uma saida final coerente com a nova
arquitetura baseada em contratos.

## Solution

Transformar o `aggregator` em um no orientado por LLM que recebe as lacunas
candidatas do `gap_identifier` e as hipoteses ranqueadas do grafo, monta um
prompt completo com contexto de dominio e devolve diretamente um
`FinalReport` estruturado.

Na primeira versao, o agregador deve tratar `graph_insight.raw["ranked_hypotheses"]`
como o unico sinal do grafo no prompt. O resumo textual do grafo, os pares
desconectados e outras metricas agregadas nao entram na fusao inicial.

O bloco precisa preservar lacunas textuais validas quando nao houver match
com o grafo, marcar lacunas fundidas como `textual_and_graph` quando houver
match valido e manter `textual_only` quando nao houver correspondencia.

Se a entrada textual vier vazia, o `aggregator` ainda deve chamar a LLM com o
contexto do grafo e devolver um `FinalReport` funcional. Se as hipoteses
ranqueadas do grafo vierem vazias ou invalidas, o bloco deve devolver um
`FinalReport` vazio com aviso estruturado, sem quebrar o pipeline.

## User Stories

1. As a researcher, I want the final report to merge textual candidate gaps
   with graph niches, so that I can inspect research directions in one place.
2. As a researcher, I want each final gap to declare whether it came from text
   only or from text plus graph, so that I can trust the provenance of the
   result.
3. As a researcher, I want graph-backed gaps to preserve the exact graph
   hypothesis used, so that I can audit the fusion decision later.
4. As a researcher, I want text-only gaps to remain in the final report when no
   graph match exists, so that valid candidates are not lost.
5. As a researcher, I want the final report to remain candidate-oriented, so
   that the system does not overclaim novelty.
6. As a researcher, I want the final report to be generated even when the
   textual stage returns no candidates, so that the pipeline still produces a
   consistent artifact.
7. As a researcher, I want the final report to remain empty but explicit when
   the graph signal is missing, so that the pipeline degrades predictably.
8. As a pipeline operator, I want the aggregator to consume only ranked graph
   hypotheses from the graph branch, so that the fusion input stays narrow and
   predictable.
9. As a pipeline operator, I want the aggregator to ignore graph summary prose
   and aggregated graph metrics, so that the LLM prompt is not polluted with
   unsupported context.
10. As a pipeline operator, I want warnings from the textual stage to be
    preserved in the final report, so that earlier validation issues are not
    hidden.
11. As a pipeline operator, I want the aggregator to add its own warnings
    without overwriting existing ones, so that the report reflects the full
    execution history.
12. As a developer, I want the aggregator to return a structured `FinalReport`
    directly from the LLM, so that no second conversion layer is needed.
13. As a developer, I want `FinalReport.gaps` to keep using `IdentifiedGap`,
    so that the contract stays compatible with the rest of the codebase.
14. As a developer, I want the fusion fields on `IdentifiedGap` to be
    validated structurally, so that invalid origin combinations are rejected
    early.
15. As a developer, I want the aggregator prompt to be isolated in a dedicated
    module, so that prompt changes can be tested without running the full graph.
16. As a developer, I want the report renderer to understand the fused gap
    shape, so that the CLI does not break when the structured output changes.
17. As a maintainer, I want the aggregator to remain the single fan-in node
    for the text and graph branches, so that the graph topology stays simple.
18. As a maintainer, I want the aggregator to fail closed on malformed graph
    input but still produce a usable empty report when possible, so that the
    pipeline remains operational.

## Implementation Decisions

- The scope of this PRD is only the `aggregator` contract and the minimum
  supporting changes required to make it functional end to end.
- The aggregator will be implemented as a single structured-output LLM call
  that returns a complete `FinalReport`.
- The aggregator input will use the current `gap_identifier` output plus
  `graph_insight.raw["ranked_hypotheses"]` as the only graph-side input for
  fusion.
- The aggregator will not use `graph_insight.summary`, `disconnected_pairs`,
  or other aggregated graph metrics in the initial implementation.
- The aggregator will keep `FinalReport.gaps` as `list[IdentifiedGap]` and
  will not introduce a separate final-gap model.
- `IdentifiedGap` will be extended with `origin`, `matched_graph_hypothesis`,
  and `graph_refinement`.
- `origin` will be required on every final gap.
- `textual_only` gaps will have `matched_graph_hypothesis = null` and
  `graph_refinement = null`.
- `textual_and_graph` gaps will have both fusion fields populated.
- `matched_graph_hypothesis` will preserve the full ranked hypothesis dict
  used during fusion.
- The aggregator will preserve and aggregate warnings from the textual stage
  instead of overwriting them.
- The aggregator will continue to emit a usable `FinalReport` even when the
  textual gap list is empty.
- If the graph hypotheses are empty or malformed, the aggregator will return
  an empty `FinalReport` with warning rather than breaking the pipeline.
- The aggregator will not reconcile or recompute the final report after the
  LLM returns; structural validation is the only post-call gate.
- The prompt contract for the aggregator should live in a dedicated prompt
  module so it can be tested independently.
- The graph fan-in wiring stays unchanged: `aggregator` remains the final
  merge point after `gap_identifier` and `graph_analyzer`.
- The CLI report renderer must be updated to display the new fused gap fields
  and continue rendering empty-report and warning-only cases cleanly.

## Testing Decisions

- Good tests should verify behavior through public outputs: the prompt
  payload, the structured `FinalReport`, and the rendered report text.
- The aggregator prompt builder should be tested in isolation to confirm it
  includes the textual candidate gaps, the ranked graph hypotheses, the topic,
  and the warning context.
- The aggregator node should be tested with a fake structured-output LLM to
  confirm it returns a validated `FinalReport` and does not require a second
  conversion step.
- The aggregator node should be tested for the empty textual input path to
  confirm it still calls the LLM and returns a valid report.
- The aggregator node should be tested for missing or invalid graph hypotheses
  to confirm it returns an empty report with warning.
- `IdentifiedGap` and `FinalReport` validation should be tested for the
  required `origin` coherence rules.
- The CLI report renderer should be tested against fused gaps, text-only gaps,
  and empty final reports.
- Existing structured-output prompt tests used by the text stage are the main
  prior art for the new aggregator prompt tests.

## Out of Scope

- Changing the `gap_identifier` prompt or validation rules.
- Changing the graph analyzer algorithm or its ranking strategy.
- Changing the paper extraction contract.
- Creating a separate `FinalCandidateGap` model.
- Adding graph-only gaps.
- Implementing a second fusion pass or multi-agent aggregator.
- Publishing extra graph metrics into the aggregator prompt beyond
  `ranked_hypotheses`.
- Reworking the graph topology beyond the current fan-in into `aggregator`.

## Further Notes

- This PRD intentionally isolates the aggregator contract from the textual gap
  identification block.
- The implementation should keep the current pipeline stable while replacing
  the final deterministic copy with a structured LLM-driven report.
- The current code already gives the aggregator access to both branches
  through LangGraph fan-in, so the main work is prompt construction, schema
  evolution, validation, and rendering.

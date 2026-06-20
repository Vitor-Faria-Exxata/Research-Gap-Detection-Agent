# PRD: Gap Identifier orientado por LLM

## Problem Statement

O pipeline possui um no `gap_identifier`, mas ele ainda ignora os
`ExtractedInsights` recebidos e retorna uma lista vazia. O contrato atual de
saida, `content_gaps: list[IdentifiedGap]`, tambem e insuficiente: nao representa
a data de corte do corpus, avisos de processamento, evidencias rastreaveis,
contraevidencias ou a forca da evidencia textual.

O bloco anterior ainda precisa evoluir para produzir os dados estruturados
esperados. O contrato desejado para cada artigo inclui identificacao, titulo,
data de publicacao, perguntas respondidas, metodologias, escopos nao abordados e
limitacoes declaradas.

Sem um contrato estruturado entre `paper_extractor`, `gap_identifier` e
`aggregator`, a analise nao e auditavel. A LLM poderia citar artigos
inexistentes, devolver lacunas sem evidencia ou misturar sinais textuais com
sinais do grafo. O `aggregator` tambem nao conseguiria consumir de forma segura
a data de corte, os avisos e as lacunas candidatas.

## Solution

Implementar o `gap_identifier` como um no orientado por LLM que recebe todos os
`ExtractedInsights` do corpus e realiza exatamente uma chamada de LLM na versao
inicial.

A chamada usa a skill `research-gap-identifier` como contrato de prompt e usa
resposta estruturada validada por modelos Pydantic. A propria LLM:

- calcula a data de corte como a maior data de publicacao recebida;
- compara evidencias e contraevidencias entre todos os artigos;
- postula perguntas de pesquisa ainda nao exploradas;
- calcula a forca da evidencia textual;
- retorna somente candidatas com forca de evidencia igual ou superior a 70.

O codigo nao recalcula o score. Ele valida o formato, as faixas numericas e as
referencias aos artigos recebidos. Lacunas sem evidencia ou com evidencia que
referencia artigo inexistente sao removidas individualmente. Contraevidencias
com referencia invalida sao removidas sem eliminar automaticamente a lacuna.

Quando nao houver `ExtractedInsights`, o no nao chama a LLM. Ele retorna um
resultado vazio com aviso estruturado.

A saida completa e armazenada em `gap_identification` e consumida pelo
`aggregator`. Os `ExtractedInsights` originais permanecem preservados
separadamente no estado.

## User Stories

1. Como pesquisador, quero receber perguntas de pesquisa candidatas, para que eu possa investigar direcoes aparentemente ainda nao exploradas no corpus.
2. Como pesquisador, quero que cada resultado seja apresentado como candidato, para que o sistema nao declare uma lacuna cientifica como fato definitivo.
3. Como pesquisador, quero saber a data de corte da analise, para que eu entenda ate quando a afirmacao de atualidade e valida.
4. Como pesquisador, quero que a data de corte venha do artigo mais recente do corpus, para que ela nao seja confundida com a data de execucao do agente.
5. Como pesquisador, quero que cada lacuna seja formulada como pergunta de pesquisa, para que o resultado seja operacionalizavel.
6. Como pesquisador, quero uma descricao curta de cada candidata, para que eu compreenda seu escopo.
7. Como pesquisador, quero uma justificativa separada da descricao, para que eu entenda por que a pergunta foi classificada como candidata.
8. Como pesquisador, quero uma pontuacao de forca de evidencia textual, para que eu possa comparar a robustez das candidatas.
9. Como pesquisador, quero que a pontuacao represente a qualidade do suporte no corpus, para que ela nao seja confundida com confianca subjetiva da LLM.
10. Como pesquisador, quero receber apenas candidatas com forca de evidencia textual de pelo menos 70, para que resultados fracos sejam excluidos.
11. Como pesquisador, quero que cada evidencia identifique seu artigo de origem, para que eu possa auditar a conclusao.
12. Como pesquisador, quero que cada evidencia declare seu tipo, para que eu diferencie limitacao declarada, omissao recorrente e contraste inferido.
13. Como pesquisador, quero que descricoes de evidencia sejam parafrases fieis, para que sejam legiveis sem fingir citacoes literais.
14. Como pesquisador, quero ver contraevidencias relevantes, para que as limitacoes da candidata fiquem explicitas.
15. Como pesquisador, quero que cada contraevidencia identifique o artigo relacionado, para que eu possa rastrear respostas parciais ou contradicoes.
16. Como pesquisador, quero que uma pergunta ja claramente respondida no corpus seja descartada, para que o sistema nao apresente lacunas obsoletas.
17. Como pesquisador, quero que respostas parciais reduzam a forca da candidata sem necessariamente elimina-la, para que nuances do corpus sejam preservadas.
18. Como operador do pipeline, quero enviar todos os insights em uma unica analise, para que a LLM compare artigos e detecte recorrencias.
19. Como operador do pipeline, quero evitar a chamada de LLM quando nao houver insights, para que nao haja custo sem possibilidade de analise.
20. Como operador do pipeline, quero receber avisos com codigos estaveis, para que falhas parciais sejam tratadas sem interpretar mensagens livres.
21. Como operador do pipeline, quero preservar os insights originais no estado, para que a auditoria nao dependa de a LLM repeti-los.
22. Como operador do pipeline, quero que uma lacuna sem evidencia seja removida individualmente, para que outras candidatas validas sejam preservadas.
23. Como operador do pipeline, quero que uma lacuna com evidencia referenciando artigo inexistente seja removida, para que o resultado nao contenha suporte inventado.
24. Como operador do pipeline, quero que uma contraevidencia com artigo inexistente seja removida sem descartar automaticamente a lacuna, para que um erro localizado nao invalide toda a analise.
25. Como operador do pipeline, quero que IDs de artigos sejam preservados exatamente, para que referencias possam ser resolvidas no estado.
26. Como desenvolvedor do `aggregator`, quero receber um unico `GapIdentificationResult`, para que eu acesse data de corte, avisos e lacunas pelo mesmo contrato.
27. Como desenvolvedor do `aggregator`, quero obter os artigos de suporte por `evidence[].paper_id`, para que nao exista uma segunda lista sujeita a divergencia.
28. Como desenvolvedor, quero usar resposta estruturada da LLM, para que nao seja necessario interpretar JSON manualmente.
29. Como desenvolvedor, quero que a configuracao de modelo continue associada ao papel `gap_identifier`, para que o provedor possa ser alterado sem mudar o no.
30. Como desenvolvedor, quero que a skill concentre regras de dominio e instrucao do prompt, para que o no permaneca focado em orquestracao e validacao.
31. Como desenvolvedor, quero testar a montagem do prompt separadamente, para que mudancas de instrucao nao exijam uma chamada real de LLM.
32. Como desenvolvedor, quero testar a validacao pos-LLM separadamente, para que referencias invalidas sejam cobertas deterministicamente.
33. Como desenvolvedor, quero que o no realize exatamente uma chamada de LLM quando houver entrada valida, para que a versao inicial tenha custo e comportamento previsiveis.
34. Como desenvolvedor, quero que sinais do grafo sejam proibidos neste bloco, para que a responsabilidade textual permaneça separada da agregacao final.
35. Como mantenedor, quero que a evolucao futura para multiplas chamadas preserve os mesmos contratos, para que o `aggregator` nao dependa da estrategia interna.

## Implementation Decisions

- O escopo deste PRD e o `gap_identifier` e seu contrato de integracao com o
  bloco anterior e com o `aggregator`.
- O `paper_extractor` deve produzir `ExtractedInsights` estruturados antes de o
  fluxo completo funcionar. A interpretacao de `full_text` nao pertence ao
  `gap_identifier`.
- `ExtractedInsights` passa a incluir `paper_id`, `title`, `published_date`,
  `questions_answered`, `methodologies`, `not_addressed` e
  `stated_limitations`.
- As quatro listas analiticas de um `ExtractedInsights` podem estar vazias. Uma
  lista vazia significa ausencia de sinal extraido para aquele campo.
- A versao inicial usa exatamente uma chamada de LLM com todos os
  `ExtractedInsights`.
- A skill `research-gap-identifier` fornece as regras de dominio, evidencia,
  score e formato de resposta usadas na montagem do prompt.
- O no usa a configuracao de LLM associada ao papel `gap_identifier`.
- A chamada usa structured output do provedor LangChain, seguindo o padrao ja
  usado no projeto para respostas Pydantic.
- A LLM calcula `cutoff_date`. O codigo nao recebe essa data do bloco anterior e
  nao a recalcula.
- A LLM calcula `evidence_strength`. O codigo nao aplica uma formula alternativa
  nem altera o score.
- `evidence_strength` representa forca da evidencia textual no corpus, nao
  confianca subjetiva da LLM.
- Uma candidata retornada deve ter score entre 70 e 100. O limite inferior
  representa o limiar de qualificacao do resultado, e o limite superior evita
  valores fora da escala.
- A LLM pode usar somente tres tipos de evidencia: `stated_limitations`,
  `recurring_not_addressed` e `contrast`.
- Evidencia do grafo e proibida neste bloco.
- A saida usa o seguinte contrato de dominio:

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
    evidence_strength: int
    evidence: list[GapEvidence]
    rationale: str
    counter_evidence: list[CounterEvidence]

class GapIdentificationResult(BaseModel):
    cutoff_date: date | None
    warnings: list[GapWarning]
    gaps: list[IdentifiedGap]
```

- O nome tecnico `IdentifiedGap` e mantido. Semanticamente, ele representa uma
  lacuna candidata atual relativa ao corpus.
- `GapEvidence.description` e `CounterEvidence.description` sao parafrases
  fieis dos dados estruturados. Nao sao citacoes literais.
- `IdentifiedGap` nao possui `evidence_types`; os tipos sao derivados dos itens
  de evidencia.
- `IdentifiedGap` nao possui `supporting_paper_ids`; os artigos de suporte sao
  derivados dos itens de evidencia.
- Toda lacuna precisa de pelo menos um item de evidencia.
- Todo `paper_id` de evidencia e contraevidencia deve existir nos
  `ExtractedInsights` recebidos e deve ser preservado exatamente.
- O codigo de validacao pos-LLM encapsula as regras de integridade referencial
  em uma interface testavel, separada da chamada do modelo.
- Uma lacuna sem evidencia e removida e gera `missing_evidence`.
- Uma lacuna com evidencia que referencia artigo inexistente e removida e gera
  `invalid_evidence_reference`.
- Uma contraevidencia que referencia artigo inexistente e removida e gera
  `invalid_counter_evidence_reference`, sem remover automaticamente a lacuna.
- Quando nao houver entrada, o no nao chama a LLM e retorna `cutoff_date: null`,
  `gaps: []` e o aviso `no_extracted_insights`.
- O no armazena o resultado validado em `gap_identification`.
- `gap_identification` substitui `content_gaps` no estado compartilhado.
- O `aggregator` passa a consumir `gap_identification.gaps`,
  `gap_identification.cutoff_date` e `gap_identification.warnings`.
- Os `ExtractedInsights` originais permanecem no estado e nao sao repetidos na
  resposta da LLM.
- O `aggregator` deve ser adaptado apenas o suficiente para consumir o novo
  contrato. A fusao semantica com o grafo nao e implementada por este PRD.
- O renderizador final que ainda assume evidencia textual simples deve ser
  adaptado para o novo formato estruturado, evitando quebra do fluxo existente.
- A evolucao para varias chamadas, ferramentas ou subagentes fica condicionada
  a problemas medidos de contexto ou qualidade e nao altera os contratos
  definidos aqui.

## Testing Decisions

- Os testes devem verificar comportamento observavel e contratos, nao detalhes
  internos de prompt, ordem de funcoes auxiliares ou implementacao do provedor.
- Sera adotado um runner convencional de testes Python, pois os testes atuais
  do projeto sao scripts manuais e nao oferecem regressao automatizada.
- Os schemas compartilhados terao testes de validacao de campos obrigatorios,
  enum de evidencia, limites do score e data de corte nula.
- O montador de prompt tera teste que confirma a inclusao do topico, de todos os
  insights e das regras essenciais da skill, sem exigir chamada externa.
- O validador pos-LLM tera testes isolados para lacuna valida, evidencia ausente,
  evidencia com artigo inexistente e contraevidencia com artigo inexistente.
- O teste de referencia invalida deve confirmar que apenas a candidata afetada
  e removida.
- O teste de contraevidencia invalida deve confirmar que apenas o item e
  removido e que a lacuna permanece.
- O no tera teste de entrada vazia confirmando que nenhuma LLM e chamada e que o
  aviso `no_extracted_insights` e retornado.
- O no tera teste com entrada valida confirmando exatamente uma chamada de LLM.
- O no tera teste confirmando que todos os insights recebidos participam da
  mesma requisicao.
- O no tera teste confirmando que a resposta validada e armazenada em
  `gap_identification`.
- O estado tera teste confirmando que preserva simultaneamente
  `extracted` e `gap_identification`.
- O `aggregator` tera teste de compatibilidade confirmando que le as lacunas, a
  data de corte e os avisos do novo objeto.
- O renderizador final tera teste cobrindo evidencia estruturada e uma lista
  vazia de lacunas.
- Chamadas reais de rede e de LLM nao fazem parte dos testes unitarios. O modelo
  estruturado deve ser substituido por um fake que devolva contratos
  deterministas.
- Um teste de integracao opcional pode usar o provedor configurado, mas deve ser
  separado da suite padrao e exigir credenciais explicitas.
- O padrao de structured output do `query_rewriter` serve como prior art para a
  chamada da LLM. Os scripts existentes do extrator e do grafo servem apenas
  como referencia de dados, nao como modelo suficiente de teste automatizado.

## Out of Scope

- Implementar a extracao por LLM das quatro categorias a partir de `full_text`.
- Corrigir os conversores de PDF ou HTML.
- Implementar a fusao semantica entre lacunas textuais e nichos do grafo.
- Definir o contrato final completo de `GraphNiche`.
- Criar resultados `graph_only`.
- Implementar ranking final do `aggregator`.
- Evoluir o `gap_identifier` para multiplos agentes, multiplas chamadas ou uso
  de ferramentas.
- Calibrar empiricamente o limiar de 70.
- Criar uma metrica separada de confianca subjetiva da LLM.
- Buscar literatura adicional para confirmar lacunas fora do corpus recebido.
- Publicar este PRD no GitHub ou em qualquer issue tracker.

## Further Notes

- A divergencia do extrator foi corrigida: `paper_extractor` preserva os
  documentos convertidos, incluindo `full_text`, em `extracted_documents` e
  grava separadamente em `extracted` um `ExtractedInsights` minimo por
  documento.
- O `ExtractedInsights` minimo atual inclui `paper_id`, `title` e
  `published_date`, com as quatro listas analiticas vazias. Ele ainda nao
  interpreta semanticamente o `full_text`; essa extracao futura continua fora
  do escopo deste PRD.
- O contrato antigo de `IdentifiedGap`, com evidencia como texto simples e
  referencias duplicadas, foi substituido pelo formato estruturado
  deliberadamente incompativel definido neste PRD.
- A CLI e o `FinalReport` foram adaptados de forma coordenada para o novo
  `IdentifiedGap`, incluindo evidencias estruturadas, data de corte e avisos.
- O `aggregator` atual copia as lacunas textuais validadas, a data de corte e os
  avisos para o relatorio. Essa implementacao provisoria preserva o novo
  contrato antes da futura fusao com o grafo.
- Este PRD foi mantido apenas no repositorio local e nao deve ser publicado
  automaticamente.

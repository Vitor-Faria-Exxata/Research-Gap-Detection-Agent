import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_skill_documents_the_qualified_output_contract():
    skill = _read("skills/research-gap-identifier/SKILL.md")

    assert re.search(r"conceptual rubric.*0\s*(?:to|\.\.)\s*100", skill, re.I)
    assert re.search(
        r"structured (?:response|output).{0,160}70\s*(?:to|\.\.)\s*100",
        skill,
        re.I | re.S,
    )
    assert not re.search(r'"evidence_strength"\s*:\s*0\b', skill)
    assert re.search(r'"evidence_strength"\s*:\s*(?:7\d|[89]\d|100)\b', skill)
    assert '"warnings": []' in skill
    assert re.search(
        r"node.{0,80}(?:generates|produces).{0,80}warnings deterministically",
        skill,
        re.I | re.S,
    )
    assert re.search(
        r"extracted_insights.{0,80}non-empty.{0,80}cutoff_date.{0,80}non-null",
        skill,
        re.I | re.S,
    )


def test_context_documents_separate_extraction_contracts():
    context = _read("CONTEXT.md")

    assert "`extracted_documents`" in context
    assert "`extracted`" in context
    assert re.search(
        r"full_text.{0,80}`extracted_documents`.{0,160}separadamente"
        r".{0,160}`extracted`",
        context,
        re.I | re.S,
    )
    assert re.search(
        r"contrato minimo atual de `extracted`.{0,180}listas analiticas vazias",
        context,
        re.I | re.S,
    )
    assert "nao interpreta semanticamente o `full_text`" in context
    assert re.search(r"calculo conceitual.*0\s*(?:a|\.\.)\s*100", context, re.I)
    assert re.search(r"saida qualificada.*70\s*(?:a|\.\.)\s*100", context, re.I)


def test_prd_records_the_minimum_extractor_contract():
    prd = _read("docs/prd/gap-identifier.md")

    assert "`extracted_documents`" in prd
    assert "`extracted`" in prd
    assert re.search(
        r"full_text.{0,80}`extracted_documents`.{0,160}separadamente"
        r".{0,80}`extracted`.{0,80}`ExtractedInsights`",
        prd,
        re.I | re.S,
    )
    assert re.search(
        r"`ExtractedInsights` minimo atual.{0,180}listas analiticas vazias",
        prd,
        re.I | re.S,
    )
    assert "devolve artigos com `full_text`" not in prd


def test_readme_describes_the_current_minimum_extractor_contract():
    readme = _read("README-agent.md")

    assert "extracts insights from each paper with an LLM" not in readme
    assert "`extracted_documents`" in readme
    assert "`extracted`" in readme
    assert re.search(
        r"analytical lists are\s+initialized empty",
        readme,
        re.I,
    )


def test_vitor_blocks_matches_the_qualified_gap_contract():
    design = _read("docs/vitor_blocks.md")

    assert re.search(
        r"calculo conceitual.{0,120}0\s*(?:a|\.\.)\s*100",
        design,
        re.I | re.S,
    )
    assert re.search(
        r"saida estruturada.{0,120}70\s*(?:a|\.\.)\s*100",
        design,
        re.I | re.S,
    )
    assert re.search(
        r"`cutoff_date` pertence ao\s+`GapIdentificationResult`",
        design,
    )
    assert "nao existe um campo separado `supporting_paper_ids`" in design

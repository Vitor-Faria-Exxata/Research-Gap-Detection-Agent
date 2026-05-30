from dataclasses import dataclass


@dataclass
class ScientificEntity:
    text: str
    entity_type: str
    sentence: str
    paper_id: str
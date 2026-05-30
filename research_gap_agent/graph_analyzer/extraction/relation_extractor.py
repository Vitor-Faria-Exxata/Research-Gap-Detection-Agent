RELATION_PATTERNS = {
    "USES": [
        "use",
        "using",
        "uses"
    ],
    "IMPROVES": [
        "improves",
        "enhances"
    ],
    "APPLIES_TO": [
        "applied to",
        "for"
    ],
    "OPTIMIZES": [
        "optimize",
        "optimization"
    ]
}


def extract_relations(
    sentence,
    entities
):
    sentence_lower = sentence.lower()

    relations = []

    for rel, patterns in RELATION_PATTERNS.items():

        found = False

        for p in patterns:

            if p in sentence_lower:
                found = True
                break

        if not found:
            continue

        for i in range(len(entities)):

            for j in range(i + 1, len(entities)):

                a = entities[i]
                b = entities[j]

                if a["type"] == b["type"]:
                    continue

                relations.append({
                    "source": a["text"],
                    "target": b["text"],
                    "relation": rel
                })

    return relations
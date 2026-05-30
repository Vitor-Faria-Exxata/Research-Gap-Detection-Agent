PATTERNS = [
    "future work",
    "remains challenging",
    "not explored",
    "open problem",
    "further research"
]


def extract_future_work_sentences(text):
    sentences = text.split(".")

    results = []

    for s in sentences:

        s_lower = s.lower()

        for p in PATTERNS:

            if p in s_lower:
                results.append(s.strip())

    return results
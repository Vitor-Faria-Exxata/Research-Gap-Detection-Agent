import requests


def reconstruct_abstract(inv_idx):
    if not inv_idx:
        return ""

    words = sorted(
        [(p, w)
         for w, pos in inv_idx.items()
         for p in pos]
    )

    return " ".join([w for _, w in words])


def search_papers(query, top_k):
    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per-page": top_k,
        "sort": "cited_by_count:desc"
    }

    r = requests.get(url, params=params)

    r.raise_for_status()

    papers = []

    for item in r.json()["results"]:

        abstract = reconstruct_abstract(
            item.get("abstract_inverted_index")
        )

        papers.append({
            "id": item["id"],
            "title": item.get("title", ""),
            "abstract": abstract,
            "text": f"{item.get('title', '')}. {abstract}"
        })

    return papers
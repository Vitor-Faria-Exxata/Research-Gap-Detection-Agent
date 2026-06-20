__all__ = ["build_graph", "GraphState"]


def __getattr__(name: str):
    if name == "build_graph":
        from research_gap_agent.graph import build_graph

        globals()[name] = build_graph
        return build_graph
    if name == "GraphState":
        from research_gap_agent.state import GraphState

        globals()[name] = GraphState
        return GraphState
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

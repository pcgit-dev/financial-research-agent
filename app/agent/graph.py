from __future__ import annotations
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import AgentNodes
from app.agent.state import AgentState, Route


def _route_selector(state: AgentState) -> Route:
    """Conditional edge: send the query down the chosen branch."""
    return state.get("route", "direct")


def build_graph(nodes: AgentNodes):
    """Assemble and compile the agent's state graph."""
    graph = StateGraph(AgentState)

    graph.add_node("classify", nodes.route)
    graph.add_node("search", nodes.search)
    graph.add_node("generate_with_context", nodes.generate_with_context)
    graph.add_node("generate_direct", nodes.generate_direct)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_selector,
        {"search": "search", "direct": "generate_direct"},
    )
    graph.add_edge("search", "generate_with_context")
    graph.add_edge("generate_with_context", END)
    graph.add_edge("generate_direct", END)

    return graph.compile()

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.roleplay.nodes.context_builder import make_context_builder_node
from backend.app.agents.roleplay.nodes.mock_nodes import (
    domain_persistence_mock_node,
    judge_mock_node,
    response_pack_mock_node,
    response_validator_mock_node,
    rule_engine_mock_node,
)
from backend.app.agents.roleplay.nodes.rag_gate import rag_gate_node
from backend.app.agents.roleplay.state import AgentState


def build_roleplay_turn_graph(session: AsyncSession):
    graph = StateGraph(AgentState)

    graph.add_node("context_builder", make_context_builder_node(session))
    graph.add_node("rag_gate", rag_gate_node)
    graph.add_node("judge_mock", judge_mock_node)
    graph.add_node("rule_engine_mock", rule_engine_mock_node)
    graph.add_node("response_pack_mock", response_pack_mock_node)
    graph.add_node("response_validator_mock", response_validator_mock_node)
    graph.add_node("domain_persistence_mock", domain_persistence_mock_node)

    graph.add_edge(START, "context_builder")
    graph.add_edge("context_builder", "rag_gate")
    graph.add_edge("rag_gate", "judge_mock")
    graph.add_edge("judge_mock", "rule_engine_mock")
    graph.add_edge("rule_engine_mock", "response_pack_mock")
    graph.add_edge("response_pack_mock", "response_validator_mock")
    graph.add_edge("response_validator_mock", "domain_persistence_mock")
    graph.add_edge("domain_persistence_mock", END)

    return graph.compile()

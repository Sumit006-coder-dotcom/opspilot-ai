from langgraph.graph import StateGraph
from workflows.engine import build_workflow, persistence_backend
from workflows.state import WorkflowState

def test_compiles_stategraph_and_has_checkpoint_backend():
    graph = build_workflow("ecommerce")
    assert isinstance(graph, StateGraph.__mro__[0]) or hasattr(graph, "invoke")
    assert persistence_backend() in {"sqlite", "memory_fallback"}


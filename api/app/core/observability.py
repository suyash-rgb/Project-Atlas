"""Langfuse observation helpers shared by the agent pipeline."""

from functools import wraps
from typing import Callable, Literal, ParamSpec, TypeVar

ObservationType = Literal[
    "generation",
    "span",
    "agent",
    "tool",
    "chain",
    "retriever",
    "embedding",
    "evaluator",
    "guardrail",
]

try:
    from langfuse import observe, propagate_attributes
except ImportError:
    observe = None
    propagate_attributes = None

P = ParamSpec("P")
R = TypeVar("R")


def observe_with_tags(
    *,
    name: str,
    tags: list[str],
    as_type: ObservationType = "tool",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Create a typed Langfuse observation and propagate its trace tags."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if observe is None or propagate_attributes is None:
            return func

        @wraps(func)
        def tagged(*args: P.args, **kwargs: P.kwargs) -> R:
            with propagate_attributes(tags=tags):
                return func(*args, **kwargs)

        return observe(
            name=name,
            as_type=as_type,
            capture_input=False,
            capture_output=False,
        )(tagged)

    return decorator

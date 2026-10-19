"""Langfuse observation helpers shared by the agent pipeline."""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator, Literal, ParamSpec, TypeVar

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
    from langfuse import get_client, observe, propagate_attributes
except ImportError:
    get_client = None
    observe = None
    propagate_attributes = None

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def trace_observation(
    *,
    name: str,
    as_type: ObservationType = "span",
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any | None]:
    """Create a nested observation without capturing request or response content."""
    if get_client is None:
        yield None
        return

    client = get_client()
    with client.start_as_current_observation(
        name=name,
        as_type=as_type,
        metadata=metadata,
    ) as observation:
        yield observation


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

from typing import Any, TypedDict


class JarvisState(TypedDict, total=False):

    messages: list[Any]

    user_request: str

    plan: list[str]

    tool_results: list[Any]

    memories: list[str]

    current_task: str

    iteration_count: int

    final_response: str

    confirmation_required: bool

    pending_action: str | None

    error_detected: bool

    completed: bool
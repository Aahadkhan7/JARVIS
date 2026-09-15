from typing import Literal

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from .agent import create_agent
from .config import GROQ_API_KEY, GROQ_MODEL, MAX_ITERATIONS
from .prompts import SYSTEM_PROMPT
from .schemas import AgentPlan
from .state import JarvisState
from .tools import TOOLS, TASKS_FILE


TOOLS_BY_NAME = {
    tool.name: tool
    for tool in TOOLS
}


def create_planner():
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0,
    )

    return llm.with_structured_output(AgentPlan)


def understand(state: JarvisState):
    return {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["user_request"]),
        ],
        "iteration_count": 0,
        "tool_results": [],
        "plan": [],
        "memories": [],
        "confirmation_required": False,
        "pending_action": None,
        "error_detected": False,
        "completed": False,
        "final_response": "",
    }


def plan(state: JarvisState):
    planner = create_planner()

    previous_results = state.get(
        "tool_results",
        []
    )

    previous_result_text = "\n".join(
        str(result)
        for result in previous_results
    )

    planning_prompt = SystemMessage(
        content=(
            "You are JARVIS planning the next action.\n\n"

            "Create a short practical ordered plan.\n\n"

            "Rules:\n"
            "- Understand the user's actual goal.\n"
            "- Review previous tool results.\n"
            "- Use successful results already available.\n"
            "- Do not repeat completed work.\n"
            "- If a tool failed, analyze the error.\n"
            "- Never repeat the exact same failed action.\n"
            "- Choose another valid approach when possible.\n"
            "- Never invent information.\n"
            "- Stop when the user's request is completed.\n\n"

            "Previous tool results:\n"
            f"{previous_result_text}"
        )
    )

    try:
        planning_result = planner.invoke(
            [
                planning_prompt
            ]
            + state["messages"]
        )

        current_plan = planning_result.steps

    except Exception:
        current_plan = [
            "Understand the request",
            "Use the required tools",
            "Review the tool results",
            "Complete the request",
        ]

    plan_text = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(
            current_plan,
            start=1
        )
    )

    execution_prompt = SystemMessage(
        content=(
            "Follow this plan carefully.\n\n"
            f"{plan_text}\n\n"

            "Execution rules:\n"
            "- Use tools when required.\n"
            "- Use previous tool results.\n"
            "- Do not repeat successful tool calls unnecessarily.\n"
            "- Do not repeat the exact same failed tool call.\n"
            "- If a tool failed, choose another valid approach.\n"
            "- Never invent information.\n"
            "- Never claim success without confirmation.\n"
            "- If the task is complete, answer the user.\n"
            "- If another tool is required, call it."
        )
    )

    messages = state["messages"] + [
        execution_prompt
    ]

    llm = create_agent()

    try:
        response = llm.invoke(messages)

    except Exception as error:
        return {
            "messages": messages,
            "plan": current_plan,
            "error_detected": True,
            "final_response": (
                f"JARVIS encountered an error: {error}"
            ),
        }

    tool_calls = getattr(
        response,
        "tool_calls",
        []
    )

    update = {
        "messages": messages + [response],
        "plan": current_plan,
        "iteration_count": (
            state.get("iteration_count", 0)
            + 1
        ),
        "error_detected": False,
    }

    if not tool_calls:
        update["final_response"] = (
            response.content
            or "I couldn't generate a response."
        )

        update["completed"] = True

    return update


def route_after_plan(
    state: JarvisState
) -> Literal["act", "respond"]:

    if state.get("error_detected"):
        return "respond"

    last_message = state["messages"][-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        []
    )

    if tool_calls:
        if (
            state.get("iteration_count", 0)
            < MAX_ITERATIONS
        ):
            return "act"

    return "respond"


def act(state: JarvisState):
    last_message = state["messages"][-1]

    tool_results = []

    for tool_call in getattr(
        last_message,
        "tool_calls",
        []
    ):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        selected_tool = TOOLS_BY_NAME.get(
            tool_name
        )

        if selected_tool is None:
            result = (
                f"TOOL_ERROR: Unknown tool: "
                f"{tool_name}"
            )

        else:
            try:
                result = selected_tool.invoke(
                    tool_args
                )

            except Exception as error:
                result = (
                    "TOOL_ERROR: Tool execution failed. "
                    f"Reason: {error}"
                )

        tool_results.append(result)

    return {
        "tool_results": tool_results
    }


def observe(state: JarvisState):
    last_message = state["messages"][-1]

    tool_messages = []

    confirmation_required = False
    pending_action = None
    error_detected = False

    for tool_call, result in zip(
        getattr(
            last_message,
            "tool_calls",
            []
        ),
        state.get(
            "tool_results",
            []
        ),
    ):
        result_text = str(result)

        if result_text.startswith(
            "CONFIRMATION_REQUIRED:"
        ):
            confirmation_required = True
            pending_action = tool_call["name"]

        if (
            result_text.startswith(
                "TOOL_ERROR:"
            )
            or result_text.startswith(
                "Tool error:"
            )
        ):
            error_detected = True

        tool_messages.append(
            ToolMessage(
                content=result_text,
                tool_call_id=tool_call["id"],
            )
        )

    return {
        "messages": (
            state["messages"]
            + tool_messages
        ),
        "confirmation_required": (
            confirmation_required
        ),
        "pending_action": pending_action,
        "error_detected": error_detected,
    }


def route_after_observe(
    state: JarvisState
) -> Literal["plan", "respond"]:

    if state.get("confirmation_required"):
        return "respond"

    if state.get("error_detected"):
        if (
            state.get("iteration_count", 0)
            < MAX_ITERATIONS
        ):
            return "plan"

        return "respond"

    if (
        state.get("iteration_count", 0)
        >= MAX_ITERATIONS
    ):
        return "respond"

    return "plan"


def respond(state: JarvisState):
    if state.get("confirmation_required"):
        action = state.get(
            "pending_action"
        )

        if action == "delete_all_tasks":
            return {
                "final_response": (
                    "I'm about to delete all "
                    "of your tasks. This action "
                    "is irreversible. Do you want "
                    "me to proceed?"
                ),
                "pending_action": action,
            }

        return {
            "final_response": (
                "This action requires your "
                "confirmation before I can proceed."
            ),
            "pending_action": action,
        }

    if state.get("error_detected"):
        return {
            "final_response": (
                state.get("final_response")
                or
                "I could not complete the request "
                "because a tool failed."
            )
        }

    return {
        "final_response": (
            state.get("final_response")
            or "I couldn't generate a response."
        ),
        "completed": True,
    }


def build_graph():
    graph = StateGraph(
        JarvisState
    )

    graph.add_node(
        "understand",
        understand
    )

    graph.add_node(
        "plan",
        plan
    )

    graph.add_node(
        "act",
        act
    )

    graph.add_node(
        "observe",
        observe
    )

    graph.add_node(
        "respond",
        respond
    )

    graph.set_entry_point(
        "understand"
    )

    graph.add_edge(
        "understand",
        "plan"
    )

    graph.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "act": "act",
            "respond": "respond",
        },
    )

    graph.add_edge(
        "act",
        "observe"
    )

    graph.add_conditional_edges(
        "observe",
        route_after_observe,
        {
            "plan": "plan",
            "respond": "respond",
        },
    )

    graph.add_edge(
        "respond",
        END
    )

    return graph.compile()


JARVIS_GRAPH = build_graph()


def run_jarvis(
    user_request: str
):
    result = JARVIS_GRAPH.invoke(
        {
            "user_request": user_request
        }
    )

    pending_action = result.get(
        "pending_action"
    )

    request_lower = (
        user_request.lower()
    )

    if (
        pending_action is None
        and (
            "delete all my tasks"
            in request_lower
            or "delete all tasks"
            in request_lower
            or "delete every task"
            in request_lower
        )
    ):
        pending_action = (
            "delete_all_tasks"
        )

    return (
        result.get(
            "final_response",
            "I couldn't generate a response."
        ),
        pending_action,
    )


def confirm_pending_action(
    action: str
):
    if action == "delete_all_tasks":

        if not TASKS_FILE.exists():
            return "No tasks found."

        with open(
            TASKS_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write("[]")

        return (
            "All tasks have been deleted."
        )

    return "Unknown confirmation action."
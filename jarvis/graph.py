import json

from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
)

from .agent import create_agent
from .prompts import SYSTEM_PROMPT
from .config import MAX_ITERATIONS
from .tools import TOOLS


CONFIRMATION_WORDS = {
    "yes",
    "y",
    "confirm",
    "confirmed",
}

CANCEL_WORDS = {
    "no",
    "n",
    "cancel",
    "cancelled",
}


def get_tool_by_name(tool_name):
    """
    Find a tool from the JARVIS tool list.
    """

    for tool in TOOLS:

        if getattr(tool, "name", None) == tool_name:

            return tool

    return None


def extract_confirmation(tool_message):
    """
    Check whether a tool requested confirmation.
    """

    content = getattr(
        tool_message,
        "content",
        ""
    )

    if not isinstance(
        content,
        str
    ):

        return None

    prefix = "CONFIRMATION_REQUIRED_JSON:"

    if not content.startswith(prefix):

        return None

    json_data = content[
        len(prefix):
    ].strip()

    try:

        return json.loads(
            json_data
        )

    except json.JSONDecodeError:

        return None


def run_jarvis(user_input: str):
    """
    Run JARVIS using the bound tools.

    Returns:
        response, pending_action
    """

    try:

        llm = create_agent()

        messages = [
            (
                "system",
                SYSTEM_PROMPT
            ),
            HumanMessage(
                content=user_input
            ),
        ]

        for _ in range(
            MAX_ITERATIONS
        ):

            response = llm.invoke(
                messages
            )

            messages.append(
                response
            )

            tool_calls = getattr(
                response,
                "tool_calls",
                []
            )

            if not tool_calls:

                content = getattr(
                    response,
                    "content",
                    ""
                )

                if not content:

                    return (
                        "Sorry sir, I could not generate a response.",
                        None
                    )

                return (
                    content,
                    None
                )

            for tool_call in tool_calls:

                tool_name = tool_call.get(
                    "name"
                )

                tool_args = tool_call.get(
                    "args",
                    {}
                )

                tool = get_tool_by_name(
                    tool_name
                )

                if tool is None:

                    tool_result = (
                        f"TOOL_ERROR: Tool "
                        f"'{tool_name}' was not found."
                    )

                else:

                    try:

                        tool_result = tool.invoke(
                            tool_args
                        )

                    except Exception as error:

                        tool_result = (
                            f"TOOL_ERROR: "
                            f"{error}"
                        )

                tool_message = ToolMessage(
                    content=str(
                        tool_result
                    ),
                    tool_call_id=tool_call.get(
                        "id"
                    ),
                )

                messages.append(
                    tool_message
                )

                pending_action = (
                    extract_confirmation(
                        tool_message
                    )
                )

                if pending_action:

                    occurrence_count = (
                        pending_action.get(
                            "occurrence_count",
                            1
                        )
                    )

                    if pending_action.get(
                        "replace_all",
                        False
                    ):

                        response_text = (
                            "Confirmation required before "
                            f"replacing {occurrence_count} "
                            "occurrences in the file."
                        )

                    else:

                        response_text = (
                            "Confirmation required before "
                            "editing the file."
                        )

                    return (
                        response_text,
                        pending_action
                    )

        return (
            "Sorry sir, I could not complete the request "
            "within the allowed steps.",
            None
        )

    except Exception as error:

        return (
            f"Sorry sir, something went wrong: {error}",
            None
        )


def confirm_pending_action(
    pending_action: dict
):
    """
    Execute a confirmed file edit.
    """

    if not pending_action:

        return (
            "No pending action found."
        )

    action_type = pending_action.get(
        "type"
    )

    if action_type != "file_edit":

        return (
            "Sorry sir, I could not identify "
            "the pending action."
        )

    file_path = pending_action.get(
        "file_path"
    )

    old_text = pending_action.get(
        "old_text"
    )

    new_text = pending_action.get(
        "new_text"
    )

    replace_all = pending_action.get(
        "replace_all",
        False
    )

    if not file_path:

        return (
            "TOOL_ERROR: File path is missing."
        )

    if old_text is None:

        return (
            "TOOL_ERROR: Original text is missing."
        )

    if new_text is None:

        return (
            "TOOL_ERROR: New text is missing."
        )

    try:

        from pathlib import Path

        target = Path(
            file_path
        ).expanduser()

        if not target.exists():

            return (
                f"TOOL_ERROR: File not found: "
                f"{target}"
            )

        if not target.is_file():

            return (
                f"TOOL_ERROR: Not a file: "
                f"{target}"
            )

        content = target.read_text(
            encoding="utf-8"
        )

        if old_text not in content:

            return (
                "TOOL_ERROR: The original text "
                "was not found in the file."
            )

        if replace_all:

            updated_content = content.replace(
                old_text,
                new_text
            )

        else:

            updated_content = content.replace(
                old_text,
                new_text,
                1
            )

        target.write_text(
            updated_content,
            encoding="utf-8"
        )

        if replace_all:

            occurrence_count = content.count(
                old_text
            )

            return (
                f"File edited successfully: "
                f"{target} "
                f"({occurrence_count} occurrences replaced)"
            )

        return (
            f"File edited successfully: "
            f"{target}"
        )

    except UnicodeDecodeError:

        return (
            "TOOL_ERROR: This file is not "
            "a readable UTF-8 text file."
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: File edit failed. "
            f"Reason: {error}"
        )
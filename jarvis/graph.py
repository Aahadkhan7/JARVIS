import json
import re
import time

from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.messages import ToolMessage

from .agent import create_agent
from .config import MAX_ITERATIONS, GROQ_MODEL

from .tools import (
    TOOLS,
    perform_create_file,
    perform_delete_all_tasks,
    perform_delete_file,
    perform_edit_file,
    perform_move_file,
    perform_rename_file,
    perform_update_calendar_event,
    perform_delete_calendar_event,
)


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

TASKS_PATH = DATA_DIR / "tasks.json"
CALENDAR_PATH = DATA_DIR / "calendar.json"


# ============================================================
# BASIC HELPERS
# ============================================================

def load_json(path, default):

    if not path.exists():
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return default


def save_json(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def normalize_text(text):

    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower()
    )


# ============================================================
# LLM ERROR HANDLER
# ============================================================

def format_llm_error(error):

    error_type = type(error).__name__
    error_text = str(error).strip()

    if not error_text:
        error_text = repr(error)

    lower_error = error_text.lower()

    if (
        "connection" in lower_error
        or "connect" in lower_error
        or "timeout" in lower_error
        or "timed out" in lower_error
    ):

        return (
            "JARVIS AI connection failed.\n\n"
            f"Model: {GROQ_MODEL}\n"
            f"Error type: {error_type}\n"
            f"Reason: {error_text}\n\n"
            "This usually means JARVIS could not reach "
            "the Groq API. Your local tools are still working."
        )

    if (
        "401" in lower_error
        or "unauthorized" in lower_error
        or "authentication" in lower_error
        or "api key" in lower_error
    ):

        return (
            "JARVIS AI authentication failed.\n\n"
            f"Model: {GROQ_MODEL}\n"
            f"Error type: {error_type}\n"
            f"Reason: {error_text}\n\n"
            "Check that GROQ_API_KEY exists in .env."
        )

    if (
        "429" in lower_error
        or "rate limit" in lower_error
        or "too many requests" in lower_error
    ):

        return (
            "JARVIS AI rate limit reached.\n\n"
            f"Model: {GROQ_MODEL}\n"
            f"Error type: {error_type}\n"
            f"Reason: {error_text}\n\n"
            "Wait a little and try again."
        )

    if (
        "400" in lower_error
        or "bad request" in lower_error
        or "invalid request" in lower_error
    ):

        return (
            "JARVIS sent an invalid request to Groq.\n\n"
            f"Model: {GROQ_MODEL}\n"
            f"Error type: {error_type}\n"
            f"Reason: {error_text}"
        )

    if (
        "500" in lower_error
        or "502" in lower_error
        or "503" in lower_error
        or "server error" in lower_error
        or "service unavailable" in lower_error
    ):

        return (
            "Groq server returned an error.\n\n"
            f"Model: {GROQ_MODEL}\n"
            f"Error type: {error_type}\n"
            f"Reason: {error_text}\n\n"
            "This may be temporary."
        )

    return (
        "JARVIS AI error.\n\n"
        f"Model: {GROQ_MODEL}\n"
        f"Error type: {error_type}\n"
        f"Reason: {error_text}"
    )


def invoke_agent_with_retry(
    agent,
    messages
):

    first_error = None

    try:

        return agent.invoke(
            messages
        )

    except Exception as error:

        first_error = error

    error_text = str(
        first_error
    ).lower()

    retryable = any(
        word in error_text
        for word in [
            "connection",
            "connect",
            "timeout",
            "timed out",
            "502",
            "503",
            "service unavailable",
            "temporarily unavailable",
        ]
    )

    if not retryable:

        raise first_error

    time.sleep(
        1.5
    )

    try:

        return agent.invoke(
            messages
        )

    except Exception as second_error:

        raise second_error


# ============================================================
# CONFIRMATION RESULT PARSER
# ============================================================

def parse_confirmation_result(result):

    if not isinstance(result, str):
        return None

    try:

        data = json.loads(result)

    except Exception:

        return None

    if not isinstance(data, dict):
        return None

    action_type = data.get("type")

    supported_types = {
        "delete_all_tasks",
        "task_delete",
        "file_create",
        "file_edit",
        "file_rename",
        "file_move",
        "file_delete",
        "calendar_update",
        "calendar_delete",
        "reminder_update",
        "reminder_delete",
        "calendar_selection",
        "duplicate_task_cleanup",
    }

    if action_type not in supported_types:
        return None

    return data


# ============================================================
# DATE HELPERS
# ============================================================

def get_today_date():

    return datetime.now().date()


def get_relative_date(word):

    word = normalize_text(
        word
    )

    today = get_today_date()

    if word == "today":
        return today

    if word == "tomorrow":
        return today + timedelta(days=1)

    if word == "yesterday":
        return today - timedelta(days=1)

    return None


def normalize_calendar_date(date_text):

    date_text = normalize_text(
        date_text
    )

    relative = get_relative_date(
        date_text
    )

    if relative:

        return relative.strftime(
            "%Y-%m-%d"
        )

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for date_format in date_formats:

        try:

            parsed = datetime.strptime(
                date_text,
                date_format
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return date_text


def normalize_time(time_text):

    time_text = normalize_text(
        time_text
    )

    if not time_text:
        return ""

    time_text = time_text.replace(
        ".",
        ""
    )

    formats = [
        "%I:%M %p",
        "%I %p",
        "%H:%M",
        "%H",
    ]

    for time_format in formats:

        try:

            parsed = datetime.strptime(
                time_text.upper(),
                time_format
            )

            return parsed.strftime(
                "%H:%M"
            )

        except ValueError:

            continue

    return time_text


# ============================================================
# CALENDAR UPDATE REQUEST
# ============================================================

def extract_calendar_update_request(
    user_input
):

    text = normalize_text(
        user_input
    )

    patterns = [

        re.compile(
            r"^change\s+my\s+(.+?)\s+event\s+to\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*"
            r"(am|pm)\s+"
            r"(today|tomorrow)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^move\s+my\s+(.+?)\s+event\s+to\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*"
            r"(am|pm)\s+"
            r"(today|tomorrow)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^change\s+(?:my\s+)?(.+?)\s+event\s+to\s+"
            r"(\d{1,2}):(\d{2})\s+"
            r"(today|tomorrow)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^move\s+(?:my\s+)?(.+?)\s+event\s+to\s+"
            r"(\d{1,2}):(\d{2})\s+"
            r"(today|tomorrow)$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if not match:
            continue

        groups = match.groups()

        title = groups[0].strip()

        if len(groups) == 5:

            hour = groups[1]
            minute = groups[2] or "00"
            meridiem = groups[3]
            target_day = groups[4]

            hour_number = int(hour)
            minute_number = int(minute)

            if hour_number < 1 or hour_number > 12:
                return None

            if minute_number < 0 or minute_number > 59:
                return None

            if meridiem.lower() == "pm":

                if hour_number != 12:
                    hour_number += 12

            else:

                if hour_number == 12:
                    hour_number = 0

        else:

            hour_number = int(groups[1])
            minute_number = int(groups[2])
            target_day = groups[3]

            if hour_number < 0 or hour_number > 23:
                return None

            if minute_number < 0 or minute_number > 59:
                return None

        target_date = get_relative_date(
            target_day
        )

        if not target_date:
            return None

        return {
            "title": title,
            "new_date": target_date.strftime(
                "%Y-%m-%d"
            ),
            "new_time": (
                f"{hour_number:02d}:"
                f"{minute_number:02d}"
            ),
        }

    return None


# ============================================================
# CALENDAR DELETE REQUEST
# ============================================================

def extract_calendar_delete_request(
    user_input
):

    text = normalize_text(
        user_input
    )

    patterns = [

        re.compile(
            r"^delete\s+(?:the\s+)?(?:my\s+)?"
            r"(?:calendar\s+)?event\s+(.+?)"
            r"(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?$",
            re.IGNORECASE
        ),

        re.compile(
            r"^remove\s+(?:the\s+)?(?:my\s+)?"
            r"(?:calendar\s+)?event\s+(.+?)"
            r"(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?$",
            re.IGNORECASE
        ),

        re.compile(
            r"^delete\s+(?:my\s+)?(.+?)\s+event"
            r"(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?$",
            re.IGNORECASE
        ),

        re.compile(
            r"^remove\s+(?:my\s+)?(.+?)\s+event"
            r"(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?$",
            re.IGNORECASE
        ),

        re.compile(
            r"^delete\s+(?:my\s+)?(.+?)"
            r"\s+on\s+(today|tomorrow|yesterday)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^remove\s+(?:my\s+)?(.+?)"
            r"\s+on\s+(today|tomorrow|yesterday)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^delete\s+(?:my\s+)?(.+?)$",
            re.IGNORECASE
        ),

        re.compile(
            r"^remove\s+(?:my\s+)?(.+?)$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if not match:
            continue

        groups = match.groups()
        title = groups[0].strip()
        date_value = groups[1] if len(groups) > 1 else None

        if not title:
            return None

        # Clean command wording accidentally captured as title.
        title = re.sub(
            r"^(?:the\s+)?(?:calendar\s+)?event\s+",
            "",
            title,
            flags=re.IGNORECASE
        ).strip()

        if not title:
            return None

        target_date = None

        if date_value:

            if re.match(
                r"^\d{4}-\d{2}-\d{2}$",
                date_value
            ):
                target_date = normalize_calendar_date(
                    date_value
                )

            else:
                relative_date = get_relative_date(
                    date_value
                )

                if not relative_date:
                    return None

                target_date = relative_date.strftime(
                    "%Y-%m-%d"
                )

        return {
            "title": title,
            "date": target_date,
        }

    return None


# ============================================================
# CALENDAR SEARCH
# ============================================================

def find_calendar_events_by_title(
    title
):

    events = load_json(
        CALENDAR_PATH,
        []
    )

    wanted_title = normalize_text(
        title
    )

    matches = []

    for index, event in enumerate(events):

        existing_title = normalize_text(
            event.get("title", "")
        )

        if existing_title == wanted_title:

            matches.append(
                {
                    "index": index,
                    "event": event
                }
            )

    return matches


def find_calendar_events_for_delete(
    request
):

    matches = find_calendar_events_by_title(
        request["title"]
    )

    if not request.get("date"):
        return matches

    filtered = []

    wanted_date = normalize_calendar_date(
        request["date"]
    )

    for match in matches:

        event_date = normalize_calendar_date(
            match["event"].get(
                "date",
                ""
            )
        )

        if event_date == wanted_date:

            filtered.append(match)

    return filtered


def format_calendar_event(
    number,
    event
):

    return (
        f"{number}. "
        f"{event.get('title', 'Untitled')} | "
        f"{event.get('date', 'Not set')} | "
        f"{event.get('time') or 'Not set'}"
    )


# ============================================================
# CALENDAR SELECTION
# ============================================================

def build_calendar_selection_action(
    request,
    matches,
    operation
):

    if operation == "delete":

        action = {
            "type": "calendar_delete",
            "index": None,
            "title": None,
            "date": None,
            "time": "",
        }

    else:

        action = {
            "type": "calendar_update",
            "index": None,
            "old_title": None,
            "old_date": None,
            "old_time": None,
            "new_title": None,
            "new_date": request["new_date"],
            "new_time": request["new_time"],
            "new_description": "",
        }

    return {
        "type": "calendar_selection",
        "operation": operation,
        "request_title": request["title"],
        "new_date": request.get(
            "new_date"
        ),
        "new_time": request.get(
            "new_time"
        ),
        "requested_date": request.get(
            "date"
        ),
        "events": matches,
        "action": action,
    }


def calendar_selection_message(
    request,
    matches
):

    operation = request.get(
        "operation",
        "update"
    )

    if operation == "delete":

        lines = [
            f"I found {len(matches)} "
            f"'{request['title']}' events.",
            "",
            "Please tell me which one you want to delete:",
        ]

    else:

        lines = [
            f"I found {len(matches)} "
            f"'{request['title']}' events.",
            "",
            "Please tell me which one you want to change:",
        ]

    for number, match in enumerate(
        matches,
        start=1
    ):

        lines.append(
            format_calendar_event(
                number,
                match["event"]
            )
        )

    if operation == "update":

        lines.append("")

        lines.append(
            f"Target: {request['new_date']} "
            f"at {request['new_time']}"
        )

    return "\n".join(lines)


# ============================================================
# DETERMINISTIC CALENDAR UPDATE
# ============================================================

def deterministic_calendar_update(
    user_input
):

    request = extract_calendar_update_request(
        user_input
    )

    if not request:
        return None

    matches = find_calendar_events_by_title(
        request["title"]
    )

    if not matches:

        return (
            "I could not find a calendar event named "
            f"'{request['title']}'."
        )

    if len(matches) > 1:

        selection_action = (
            build_calendar_selection_action(
                request,
                matches,
                "update"
            )
        )

        return json.dumps(
            selection_action
        )

    selected = matches[0]

    index = selected["index"]
    event = selected["event"]

    return json.dumps(
        {
            "type": "calendar_update",
            "index": index,
            "old_title": event.get(
                "title"
            ),
            "old_date": event.get(
                "date"
            ),
            "old_time": event.get(
                "time"
            ),
            "new_title": event.get(
                "title",
                request["title"]
            ),
            "new_date": request["new_date"],
            "new_time": request["new_time"],
            "new_description": (
                event.get("description")
                or ""
            ),
        }
    )


# ============================================================
# DETERMINISTIC CALENDAR DELETE
# ============================================================

def deterministic_calendar_delete(
    user_input
):

    request = extract_calendar_delete_request(
        user_input
    )

    if not request:
        return None

    matches = find_calendar_events_for_delete(
        request
    )

    if not matches:

        if request.get("date"):

            return (
                "I could not find a calendar event named "
                f"'{request['title']}' on "
                f"{request['date']}."
            )

        return (
            "I could not find a calendar event named "
            f"'{request['title']}'."
        )

    if len(matches) > 1:

        selection_action = (
            build_calendar_selection_action(
                request,
                matches,
                "delete"
            )
        )

        return json.dumps(
            selection_action
        )

    selected = matches[0]
    event = selected["event"]

    return json.dumps(
        {
            "type": "calendar_delete",
            "index": selected["index"],
            "title": event.get(
                "title"
            ),
            "date": event.get(
                "date"
            ),
            "time": event.get(
                "time"
            ) or "",
        }
    )


# ============================================================
# DETERMINISTIC TASK CREATION
# ============================================================

def extract_create_task_request(
    user_input
):

    text = user_input.strip()

    patterns = [

        re.compile(
            r"^\s*(?:create|add|make)\s+"
            r"(?:a\s+)?task\s+"
            r"(?:called|named)?\s*"
            r"(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*add\s+"
            r"(.+?)\s+"
            r"(?:to|in)\s+(?:my\s+)?tasks\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*create\s+"
            r"(.+?)\s+"
            r"(?:as\s+)?(?:a\s+)?task\s*$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if match:

            title = match.group(1).strip()

            if title:

                return {
                    "title": title,
                    "due_date": ""
                }

    return None


def find_duplicate_task(
    title
):

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):
        return None

    wanted = normalize_text(
        title
    )

    for task in tasks:

        if not isinstance(task, dict):
            continue

        existing_title = normalize_text(
            task.get(
                "title",
                ""
            )
        )

        if existing_title == wanted:

            return task

    return None


def deterministic_create_task(
    user_input
):

    request = extract_create_task_request(
        user_input
    )

    if not request:
        return None

    title = request["title"]

    duplicate = find_duplicate_task(
        title
    )

    if duplicate:

        existing_title = duplicate.get(
            "title",
            title
        )

        status = (
            "Completed"
            if duplicate.get(
                "completed",
                False
            )
            else "Pending"
        )

        return (
            "Duplicate task detected. "
            f"'{existing_title}' already exists "
            f"with status {status}. "
            "I did not create another copy."
        )

    from .tools import create_task

    try:

        result = create_task.invoke(
            {
                "title": title,
                "due_date": request.get(
                    "due_date"
                )
            }
        )

        return str(result)

    except Exception as error:

        return (
            "TOOL_ERROR: Could not create task. "
            f"Reason: {error}"
        )


# ============================================================
# SPECIFIC TASK DELETE
# ============================================================

def extract_task_delete_request(
    user_input
):

    text = user_input.strip()

    patterns = [

        re.compile(
            r"^\s*delete\s+(?:my\s+)?task\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*remove\s+(?:my\s+)?task\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*delete\s+(?:my\s+)?(.+?)\s+task\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*remove\s+(?:my\s+)?(.+?)\s+task\s*$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if match:

            title = match.group(1).strip()

            if title:

                return title

    return None


def deterministic_task_delete(
    user_input
):

    task_title = extract_task_delete_request(
        user_input
    )

    if not task_title:
        return None

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "I could not read your task list."
        )

    wanted = normalize_text(
        task_title
    )

    matches = []

    for index, task in enumerate(
        tasks
    ):

        if not isinstance(task, dict):
            continue

        title = str(
            task.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        if normalize_text(title) == wanted:

            matches.append(
                {
                    "index": index,
                    "task": task
                }
            )

    if not matches:

        return (
            f"I could not find a task named "
            f"'{task_title}'."
        )

    if len(matches) > 1:

        lines = [
            f"I found {len(matches)} tasks named "
            f"'{task_title}':",
            "",
        ]

        for number, match in enumerate(
            matches,
            start=1
        ):

            task = match["task"]

            status = (
                "Completed"
                if task.get(
                    "completed",
                    False
                )
                else "Pending"
            )

            due_date = (
                task.get("due_date")
                or "Not set"
            )

            lines.append(
                f"{number}. "
                f"{task.get('title', task_title)} | "
                f"{status} | "
                f"{due_date}"
            )

        lines.append("")

        lines.append(
            "Please use the exact task title "
            "or clean duplicate tasks first."
        )

        return "\n".join(lines)

    selected = matches[0]

    task = selected["task"]

    action = {
        "type": "task_delete",
        "index": selected["index"],
        "title": task.get(
            "title",
            task_title
        ),
        "completed": bool(
            task.get(
                "completed",
                False
            )
        ),
        "due_date": task.get(
            "due_date"
        ),
    }

    return json.dumps(
        action
    )


def perform_task_delete(
    action
):

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "TOOL_ERROR: Could not read your task list."
        )

    try:

        index = int(
            action.get(
                "index"
            )
        )

    except Exception:

        return (
            "TOOL_ERROR: Invalid task index."
        )

    if index < 0 or index >= len(tasks):

        return (
            "TOOL_ERROR: Task list changed. "
            "Please try the delete request again."
        )

    current_task = tasks[index]

    if not isinstance(current_task, dict):

        return (
            "TOOL_ERROR: Task list changed. "
            "Please try the delete request again."
        )

    expected_title = normalize_text(
        action.get(
            "title",
            ""
        )
    )

    current_title = normalize_text(
        current_task.get(
            "title",
            ""
        )
    )

    if current_title != expected_title:

        return (
            "TOOL_ERROR: Task list changed. "
            "Please try the delete request again."
        )

    deleted_title = current_task.get(
        "title",
        "Untitled"
    )

    try:

        tasks.pop(index)

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            TASKS_PATH,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                tasks,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        return (
            "TOOL_ERROR: Could not delete task. "
            f"Reason: {error}"
        )

    return (
        f"Task '{deleted_title}' deleted successfully."
    )


# ============================================================
# DUPLICATE TASK CLEANUP
# ============================================================

def is_duplicate_cleanup_request(
    user_input
):

    text = normalize_text(
        user_input
    )

    patterns = [
        "clean duplicate tasks",
        "remove duplicate tasks",
        "delete duplicate tasks",
        "cleanup duplicate tasks",
        "clean up duplicate tasks",
        "find duplicate tasks",
    ]

    return any(
        pattern == text
        for pattern in patterns
    )


def find_duplicate_task_groups():

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):
        return []

    groups = {}

    for index, task in enumerate(tasks):

        if not isinstance(task, dict):
            continue

        title = str(
            task.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        key = normalize_text(
            title
        )

        groups.setdefault(
            key,
            []
        ).append(
            {
                "index": index,
                "task": task
            }
        )

    duplicate_groups = []

    for matches in groups.values():

        if len(matches) > 1:

            duplicate_groups.append(
                matches
            )

    return duplicate_groups


def build_duplicate_cleanup_action():

    duplicate_groups = (
        find_duplicate_task_groups()
    )

    if not duplicate_groups:
        return None

    delete_indices = []
    duplicate_details = []

    for group in duplicate_groups:

        completed = [
            item
            for item in group
            if item["task"].get(
                "completed",
                False
            )
        ]

        if completed:

            keep = completed[0]

        else:

            keep = group[0]

        for item in group:

            if item["index"] == keep["index"]:
                continue

            delete_indices.append(
                item["index"]
            )

            duplicate_details.append(
                {
                    "title": item["task"].get(
                        "title",
                        "Untitled"
                    ),
                    "status": (
                        "Completed"
                        if item["task"].get(
                            "completed",
                            False
                        )
                        else "Pending"
                    ),
                    "keep": False,
                }
            )

        duplicate_details.append(
            {
                "title": keep["task"].get(
                    "title",
                    "Untitled"
                ),
                "status": (
                    "Completed"
                    if keep["task"].get(
                        "completed",
                        False
                    )
                    else "Pending"
                ),
                "keep": True,
            }
        )

    if not delete_indices:
        return None

    return {
        "type": "duplicate_task_cleanup",
        "delete_indices": delete_indices,
        "details": duplicate_details,
        "count": len(delete_indices),
    }


def duplicate_cleanup_message(
    action
):

    details = action.get(
        "details",
        []
    )

    lines = [
        "Duplicate tasks found:",
        ""
    ]

    grouped = {}

    for detail in details:

        key = normalize_text(
            detail.get(
                "title",
                ""
            )
        )

        grouped.setdefault(
            key,
            []
        ).append(detail)

    for group in grouped.values():

        for detail in group:

            title = detail.get(
                "title",
                "Untitled"
            )

            status = detail.get(
                "status",
                "Unknown"
            )

            if detail.get("keep"):

                lines.append(
                    f"- {title} ({status}) "
                    "→ KEEP"
                )

            else:

                lines.append(
                    f"- {title} ({status}) "
                    "→ DELETE"
                )

        lines.append("")

    lines.append(
        f"This will delete {action.get('count', 0)} "
        "duplicate task(s) and keep one copy "
        "of each task."
    )

    lines.append(
        "Reply yes to confirm or no to cancel."
    )

    return "\n".join(lines)


def perform_duplicate_task_cleanup(
    action
):

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "TOOL_ERROR: Could not read your task list."
        )

    delete_indices = set(
        action.get(
            "delete_indices",
            []
        )
    )

    if not delete_indices:

        return (
            "No duplicate tasks need to be deleted."
        )

    for index in delete_indices:

        if index < 0 or index >= len(tasks):

            return (
                "TOOL_ERROR: Task list changed. "
                "Please run duplicate cleanup again."
            )

        if not isinstance(tasks[index], dict):

            return (
                "TOOL_ERROR: Task list changed. "
                "Please run duplicate cleanup again."
            )

    new_tasks = []
    deleted_count = 0

    for index, task in enumerate(tasks):

        if index in delete_indices:

            deleted_count += 1
            continue

        new_tasks.append(task)

    try:

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            TASKS_PATH,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                new_tasks,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        return (
            "TOOL_ERROR: Could not clean duplicate "
            f"tasks. Reason: {error}"
        )

    return (
        f"Duplicate task cleanup completed. "
        f"Deleted {deleted_count} duplicate task(s)."
    )


def deterministic_duplicate_task_cleanup(
    user_input
):

    if not is_duplicate_cleanup_request(
        user_input
    ):

        return None

    action = build_duplicate_cleanup_action()

    if not action:

        return (
            "No duplicate tasks found."
        )

    return json.dumps(
        action
    )


# ============================================================
# DETERMINISTIC FILE ROUTING
# ============================================================

def deterministic_file_route(
    user_input
):

    text = user_input.strip()
    lower = text.lower()

    search_match = re.match(
        r"^\s*(?:search|find)\s+inside\s+files\s+for\s+"
        r"(.+?)\s*$",
        text,
        re.IGNORECASE
    )

    if search_match:

        from .tools import search_file_contents

        query = search_match.group(
            1
        ).strip()

        return search_file_contents.invoke(
            {
                "query": query
            }
        )

    find_match = re.match(
        r"^\s*(?:find|search\s+for)\s+"
        r"(?:my\s+)?file\s+(.+?)\s*$",
        text,
        re.IGNORECASE
    )

    if find_match:

        from .tools import search_files

        filename = find_match.group(
            1
        ).strip()

        return search_files.invoke(
            {
                "filename": filename
            }
        )

    folder_match = re.match(
        r"^\s*(?:find|search\s+for)\s+"
        r"(?:my\s+)?folder\s+(.+?)\s*$",
        text,
        re.IGNORECASE
    )

    if folder_match:

        from .tools import search_files

        folder_name = folder_match.group(
            1
        ).strip()

        return search_files.invoke(
            {
                "filename": folder_name
            }
        )

    if lower in {
        "show me my files",
        "show my files",
        "list my files",
        "list files",
        "show files",
    }:

        from .tools import list_files

        return list_files.invoke({})

    if lower in {
        "open jarvis folder",
        "open my jarvis folder",
        "open jarvis project folder",
    }:

        from .tools import open_jarvis_folder

        return open_jarvis_folder.invoke({})

    return None




# ============================================================
# CALENDAR INTELLIGENCE
# ============================================================

def is_calendar_intelligence_request(user_input):

    text = normalize_text(user_input)

    triggers = (
        "calendar summary",
        "calendar dashboard",
        "calendar intelligence",
        "calendar overview",
        "calendar status",
        "analyze my calendar",
        "analyse my calendar",
        "analyze calendar",
        "analyse calendar",
        "show calendar summary",
        "show my calendar summary",
        "show calendar dashboard",
        "show my calendar dashboard",
        "calendar analysis",
        "calendar report",
        "what's on my calendar",
        "whats on my calendar",
        "what is on my calendar",
        "what is in my calendar",
        "mere calendar ka summary",
        "mere calendar ka analysis",
        "calendar ka summary",
        "calendar ka analysis",
    )

    return text in triggers


def calendar_event_datetime(event):

    event_date_text = normalize_calendar_date(
        event.get("date", "")
    )

    if not event_date_text:
        return None

    try:
        event_date = datetime.strptime(
            event_date_text,
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        return None

    time_text = normalize_time(
        event.get("time") or ""
    )

    if time_text:
        try:
            hour, minute = map(
                int,
                time_text.split(":")
            )
            return datetime.combine(
                event_date,
                datetime.min.time()
            ).replace(
                hour=hour,
                minute=minute
            )
        except Exception:
            pass

    return datetime.combine(
        event_date,
        datetime.min.time()
    )


def get_calendar_intelligence_view():

    events = load_json(
        CALENDAR_PATH,
        []
    )

    now = datetime.now()
    today = now.date()

    valid_events = []

    for index, event in enumerate(events):

        event_dt = calendar_event_datetime(event)

        if not event_dt:
            continue

        valid_events.append(
            {
                "index": index,
                "event": event,
                "datetime": event_dt,
            }
        )

    valid_events.sort(
        key=lambda item: item["datetime"]
    )

    today_events = [
        item for item in valid_events
        if item["datetime"].date() == today
    ]

    upcoming = [
        item for item in valid_events
        if item["datetime"] >= now
    ]

    past = [
        item for item in valid_events
        if item["datetime"] < now
    ]

    # Detect events sharing the same date and time.
    grouped = {}

    for item in valid_events:

        event = item["event"]
        event_time = normalize_time(
            event.get("time") or ""
        )

        if not event_time:
            continue

        key = (
            item["datetime"].date().isoformat(),
            event_time,
        )

        grouped.setdefault(key, []).append(item)

    conflicts = []

    for key, group in grouped.items():

        if len(group) > 1:
            conflicts.append(
                {
                    "date": key[0],
                    "time": key[1],
                    "events": group,
                }
            )

    return {
        "total": len(events),
        "valid": len(valid_events),
        "today": today_events,
        "upcoming": upcoming,
        "past": past,
        "conflicts": conflicts,
        "next_event": upcoming[0] if upcoming else None,
    }



# ============================================================
# CALENDAR CONFLICT + SMART SCHEDULE
# ============================================================

def is_calendar_conflict_request(user_input):

    text = normalize_text(user_input)

    triggers = (
        "calendar conflicts",
        "calendar conflict",
        "schedule conflicts",
        "schedule conflict",
        "check calendar conflicts",
        "check schedule conflicts",
        "find calendar conflicts",
        "find schedule conflicts",
        "show calendar conflicts",
        "show schedule conflicts",
        "smart schedule",
        "schedule gaps",
        "free calendar slots",
        "free time in my calendar",
        "free slots in my calendar",
        "calendar gaps",
        "calendar ka conflict",
        "calendar ke conflicts",
        "schedule ka conflict",
        "schedule ke conflicts",
    )

    return text in triggers


def get_calendar_conflict_view():

    events = load_json(CALENDAR_PATH, [])
    timed_events = []

    for index, event in enumerate(events):

        event_dt = calendar_event_datetime(event)
        event_time = normalize_time(event.get("time") or "")

        if event_dt and event_time:
            timed_events.append({
                "index": index,
                "event": event,
                "datetime": event_dt,
                "time": event_time,
            })

    timed_events.sort(key=lambda item: item["datetime"])

    grouped = {}

    for item in timed_events:
        key = (
            item["datetime"].date().isoformat(),
            item["time"],
        )
        grouped.setdefault(key, []).append(item)

    conflicts = []

    for (date_text, time_text), group in grouped.items():

        if len(group) < 2:
            continue

        titles = [
            normalize_text(item["event"].get("title", ""))
            for item in group
        ]

        conflicts.append({
            "date": date_text,
            "time": time_text,
            "events": group,
            "duplicate": len(set(titles)) < len(titles),
        })

    gaps = []

    for previous, current in zip(timed_events, timed_events[1:]):

        if previous["datetime"].date() != current["datetime"].date():
            continue

        minutes = int(
            (current["datetime"] - previous["datetime"]).total_seconds() / 60
        )

        if minutes >= 30:
            gaps.append({
                "date": current["datetime"].date().isoformat(),
                "start": previous["time"],
                "end": current["time"],
                "minutes": minutes,
            })

    return {
        "conflicts": conflicts,
        "gaps": gaps,
    }


def deterministic_calendar_conflict_route(user_input):

    if not is_calendar_conflict_request(user_input):
        return None

    view = get_calendar_conflict_view()
    conflicts = view["conflicts"]
    gaps = view["gaps"]

    lines = [
        "CALENDAR CONFLICT CHECK",
        "",
        f"Conflicts found: {len(conflicts)}",
        "",
    ]

    if conflicts:

        lines.append("SCHEDULE CONFLICTS")

        for number, conflict in enumerate(conflicts[:10], start=1):

            label = (
                "Duplicate events"
                if conflict["duplicate"]
                else "Time conflict"
            )

            lines.append(
                f"{number}. {label} — "
                f"{conflict['date']} at {conflict['time']}"
            )

            for item in conflict["events"]:
                lines.append(
                    f"   - {item['event'].get('title', 'Untitled')}"
                )

            lines.append("")

    else:
        lines.append("No same-time calendar conflicts found.")
        lines.append("")

    if gaps:

        lines.append("AVAILABLE GAPS")

        for number, gap in enumerate(gaps[:5], start=1):

            hours = gap["minutes"] // 60
            minutes = gap["minutes"] % 60

            if hours:
                duration = (
                    f"{hours}h {minutes}m"
                    if minutes
                    else f"{hours}h"
                )
            else:
                duration = f"{minutes}m"

            lines.append(
                f"{number}. {gap['date']} | "
                f"{gap['start']} → {gap['end']} | {duration}"
            )

    return "\n".join(lines).rstrip()

def deterministic_calendar_intelligence(user_input):

    if not is_calendar_intelligence_request(user_input):
        return None

    view = get_calendar_intelligence_view()

    lines = [
        "CALENDAR INTELLIGENCE",
        "",
        f"Total events: {view['total']}",
        f"Today: {len(view['today'])}",
        f"Upcoming: {len(view['upcoming'])}",
        f"Past: {len(view['past'])}",
        f"Conflicts: {len(view['conflicts'])}",
        "",
    ]

    next_event = view["next_event"]

    if next_event:

        event = next_event["event"]

        lines.extend(
            [
                "NEXT EVENT",
                format_calendar_event(
                    1,
                    event
                ),
                "",
            ]
        )

    if view["today"]:

        lines.append("TODAY")

        for number, item in enumerate(
            view["today"][:5],
            start=1
        ):

            lines.append(
                format_calendar_event(
                    number,
                    item["event"]
                )
            )

        if len(view["today"]) > 5:
            lines.append(
                f"...and {len(view['today']) - 5} more today."
            )

        lines.append("")

    if view["upcoming"]:

        lines.append("UPCOMING")

        upcoming_items = [
            item for item in view["upcoming"]
            if item is not next_event
        ][:5]

        for number, item in enumerate(
            upcoming_items,
            start=1
        ):

            lines.append(
                format_calendar_event(
                    number,
                    item["event"]
                )
            )

        if len(view["upcoming"]) > 6:
            lines.append(
                f"...and {len(view['upcoming']) - 6} more upcoming."
            )

        lines.append("")

    if view["conflicts"]:

        lines.append("SCHEDULE CONFLICTS")

        for conflict in view["conflicts"][:5]:

            lines.append(
                f"{conflict['date']} at {conflict['time']}"
            )

            for item in conflict["events"]:

                lines.append(
                    f"- {item['event'].get('title', 'Untitled')}"
                )

        lines.append("")

    if not view["today"] and not view["upcoming"]:

        lines.append(
            "No current or upcoming calendar events found."
        )

    return "\n".join(lines).rstrip()


# ============================================================
# REMINDER ENGINE
# ============================================================

def parse_reminder_time(time_text):

    return normalize_time(time_text)


def extract_reminder_request(user_input):

    text = user_input.strip()

    patterns = [
        re.compile(
            r"^remind\s+me\s+to\s+(.+?)\s+at\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
            r"(?:\s+(today|tomorrow))?\s*$",
            re.IGNORECASE
        ),
        re.compile(
            r"^remind\s+me\s+to\s+(.+?)\s+at\s+"
            r"(\d{1,2}):(\d{2})"
            r"(?:\s+(today|tomorrow))?\s*$",
            re.IGNORECASE
        ),
        re.compile(
            r"^remind\s+me\s+(.+?)\s+at\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
            r"(?:\s+(today|tomorrow))?\s*$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if not match:
            continue

        groups = match.groups()
        message = groups[0].strip()

        if not message:
            return None

        if len(groups) == 5:
            hour = int(groups[1])
            minute = int(groups[2] or "00")
            meridiem = groups[3].lower()
            target_day = groups[4] or "today"

            if hour < 1 or hour > 12 or minute > 59:
                return None

            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

        else:
            hour = int(groups[1])
            minute = int(groups[2])
            target_day = groups[3] or "today"

            if hour < 0 or hour > 23 or minute > 59:
                return None

        target_date = get_relative_date(target_day)

        if not target_date:
            return None

        return {
            "message": message,
            "date": target_date.strftime("%Y-%m-%d"),
            "time": f"{hour:02d}:{minute:02d}",
        }

    return None


def is_reminder_list_request(user_input):

    text = normalize_text(user_input)

    return text in {
        "show reminders",
        "show my reminders",
        "list reminders",
        "list my reminders",
        "my reminders",
        "reminders",
        "show reminder list",
        "reminder list",
        "reminder dashboard",
        "reminder summary",
    }


def get_reminder_events():

    events = load_json(CALENDAR_PATH, [])

    if not isinstance(events, list):
        return []

    reminders = []

    for index, event in enumerate(events):

        if not isinstance(event, dict):
            continue

        title = str(event.get("title", "")).strip()

        if title.lower().startswith("[reminder]"):
            reminders.append({
                "index": index,
                "event": event,
            })

    return reminders


def get_reminder_view():

    reminders = get_reminder_events()

    if not reminders:
        return "You have no reminders right now."

    today = get_today_date()
    upcoming = []
    past = []

    for item in reminders:

        event = item["event"]
        date_text = str(event.get("date", "")).strip()
        parsed_date = None

        try:
            parsed_date = datetime.strptime(
                normalize_calendar_date(date_text),
                "%Y-%m-%d"
            ).date()
        except ValueError:
            pass

        row = {
            "title": event.get("title", "[Reminder]"),
            "date": date_text or "Not set",
            "time": event.get("time") or "Not set",
            "parsed_date": parsed_date,
        }

        if parsed_date is not None and parsed_date < today:
            past.append(row)
        else:
            upcoming.append(row)

    upcoming.sort(
        key=lambda x: (
            x["parsed_date"] or datetime.max.date(),
            x["time"] if x["time"] != "Not set" else "23:59",
        )
    )

    lines = [
        "JARVIS Reminder Center",
        "",
        f"Total reminders: {len(reminders)}",
        f"Upcoming: {len(upcoming)}",
        f"Past: {len(past)}",
        "",
    ]

    if upcoming:
        lines.append("UPCOMING REMINDERS")
        for item in upcoming:
            title = str(item["title"])
            if title.lower().startswith("[reminder]"):
                title = title[len("[reminder]"):].strip()
            lines.append(
                f"- {title} | {item['date']} | {item['time']}"
            )
        lines.append("")

    if past:
        lines.append("PAST REMINDERS")
        for item in past[:5]:
            title = str(item["title"])
            if title.lower().startswith("[reminder]"):
                title = title[len("[reminder]"):].strip()
            lines.append(
                f"- {title} | {item['date']} | {item['time']}"
            )
        if len(past) > 5:
            lines.append(f"- ...and {len(past) - 5} more")

    return "\n".join(lines)


def deterministic_reminder_route(user_input):

    if is_reminder_list_request(user_input):
        return get_reminder_view()

    request = extract_reminder_request(user_input)

    if not request:
        return None

    from .tools import create_calendar_event

    reminder_title = f"[Reminder] {request['message']}"

    try:
        result = create_calendar_event.invoke({
            "title": reminder_title,
            "date": request["date"],
            "time": request["time"],
            "description": "JARVIS reminder",
        })
        return str(result)
    except Exception as error:
        return (
            "TOOL_ERROR: Could not create reminder. "
            f"Reason: {error}"
        )



# ============================================================
# REMINDER UPDATE / DELETE
# ============================================================

def normalize_reminder_title(title):

    text = normalize_text(title)

    for prefix in ("my ", "the "):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    if text.endswith(" reminder"):
        text = text[:-len(" reminder")].strip()

    if text.startswith("[reminder]"):
        text = text[len("[reminder]"):].strip()

    return text


def find_reminders_by_request_title(title):

    target = normalize_reminder_title(title)
    matches = []

    if not target:
        return matches

    for item in get_reminder_events():

        event = item["event"]
        event_title = str(event.get("title", ""))
        normalized_event_title = normalize_reminder_title(event_title)

        # Support natural requests such as:
        # "Change my JavaScript reminder to 8 PM"
        # when the stored reminder is:
        # "[Reminder] study JavaScript".
        #
        # Exact match is preferred, but a meaningful title fragment
        # should also match the reminder text.
        if (
            normalized_event_title == target
            or target in normalized_event_title
            or normalized_event_title in target
        ):
            matches.append(item)

    return matches


def extract_reminder_delete_request(user_input):

    text = normalize_text(user_input)

    # Calendar-event deletion belongs to the calendar delete engine.
    if (
        "calendar event" in text
        or text.startswith("delete event " )
        or text.startswith("remove event " )
    ):
        return None

    match = re.match(
        r"^(?:delete|remove)\s+(?:my\s+)?(.+?)\s*$",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    title = match.group(1).strip()

    if title.lower().endswith(" reminder"):
        title = title[:-len(" reminder")].strip()

    if not title:
        return None

    return {"title": title}


def extract_reminder_update_request(user_input):

    text = user_input.strip()

    patterns = [
        re.compile(
            r"^(?:change|move|update)\s+(?:my\s+)?(.+?)\s+to\s+"
            r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
            r"(?:\s+(today|tomorrow))?\s*$",
            re.IGNORECASE
        ),
        re.compile(
            r"^(?:change|move|update)\s+(?:my\s+)?(.+?)\s+to\s+"
            r"(\d{1,2}):(\d{2})(?:\s+(today|tomorrow))?\s*$",
            re.IGNORECASE
        ),
    ]

    for pattern in patterns:

        match = pattern.match(text)

        if not match:
            continue

        groups = match.groups()
        title = groups[0].strip()

        if title.lower().endswith(" reminder"):
            title = title[:-len(" reminder")].strip()

        if not title:
            return None

        if pattern is patterns[0]:
            hour = int(groups[1])
            minute = int(groups[2] or "00")
            meridiem = groups[3].lower()
            target_day = groups[4]

            if hour < 1 or hour > 12 or minute > 59:
                return None

            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

        else:
            hour = int(groups[1])
            minute = int(groups[2])
            target_day = groups[3]

            if hour > 23 or minute > 59:
                return None

        return {
            "title": title,
            "new_time": f"{hour:02d}:{minute:02d}",
            "target_day": target_day,
        }

    return None


def deterministic_reminder_delete(user_input):

    request = extract_reminder_delete_request(user_input)

    if not request:
        return None

    # Do not treat ordinary calendar-event deletion as reminder deletion.
    normalized_input = normalize_text(user_input)

    if (
        "calendar event" in normalized_input
        or normalized_input.startswith("delete event " )
        or normalized_input.startswith("remove event " )
    ):
        return None

    matches = find_reminders_by_request_title(request["title"])

    if not matches:
        return (
            "I could not find a reminder named "
            f"'{request['title']}'."
        )

    if len(matches) > 1:
        lines = [
            f"I found {len(matches)} reminders matching '{request['title']}'.",
            "",
            "Please tell me which one you want to delete:",
        ]
        for number, item in enumerate(matches, start=1):
            event = item["event"]
            lines.append(
                format_calendar_event(number, event)
            )
        return "\n".join(lines)

    item = matches[0]
    event = item["event"]

    return json.dumps({
        "type": "reminder_delete",
        "index": item["index"],
        "title": event.get("title", "[Reminder]"),
        "date": event.get("date", "Not set"),
        "time": event.get("time") or "Not set",
    })


def deterministic_reminder_update(user_input):

    request = extract_reminder_update_request(user_input)

    if not request:
        return None

    matches = find_reminders_by_request_title(request["title"])

    if not matches:
        return (
            "I could not find a reminder named "
            f"'{request['title']}'."
        )

    if len(matches) > 1:
        return (
            f"I found {len(matches)} reminders matching '{request['title']}'.\n\n"
            "Please tell me which one you want to change."
        )

    item = matches[0]
    event = item["event"]
    new_date = event.get("date", "")

    if request.get("target_day"):
        target_date = get_relative_date(request["target_day"])
        if not target_date:
            return None
        new_date = target_date.strftime("%Y-%m-%d")

    return json.dumps({
        "type": "reminder_update",
        "index": item["index"],
        "old_title": event.get("title", "[Reminder]"),
        "old_date": event.get("date", "Not set"),
        "old_time": event.get("time") or "Not set",
        "new_title": event.get("title", "[Reminder]"),
        "new_date": new_date,
        "new_time": request["new_time"],
        "new_description": event.get("description") or "JARVIS reminder",
    })


def perform_reminder_update(action):

    events = load_json(CALENDAR_PATH, [])

    if not isinstance(events, list):
        return "TOOL_ERROR: Could not read your calendar."

    index = action.get("index")

    if not isinstance(index, int) or index < 0 or index >= len(events):
        return "TOOL_ERROR: Reminder changed or no longer exists."

    event = events[index]

    if not isinstance(event, dict):
        return "TOOL_ERROR: Reminder data is invalid."

    event["title"] = action.get("new_title", event.get("title"))
    event["date"] = action.get("new_date", event.get("date"))
    event["time"] = action.get("new_time", event.get("time"))
    event["description"] = action.get(
        "new_description",
        event.get("description") or "JARVIS reminder"
    )

    save_json(CALENDAR_PATH, events)

    return (
        "Reminder updated successfully: "
        f"{event.get('title')} on {event.get('date')} "
        f"at {event.get('time')}"
    )


def perform_reminder_delete(action):

    events = load_json(CALENDAR_PATH, [])

    if not isinstance(events, list):
        return "TOOL_ERROR: Could not read your calendar."

    index = action.get("index")

    if not isinstance(index, int) or index < 0 or index >= len(events):
        return "TOOL_ERROR: Reminder changed or no longer exists."

    event = events[index]

    if not isinstance(event, dict):
        return "TOOL_ERROR: Reminder data is invalid."

    title = str(event.get("title", ""))
    if not title.lower().startswith("[reminder]"):
        return "TOOL_ERROR: Selected calendar item is not a reminder."

    deleted_title = title[len("[reminder]"):].strip()
    events.pop(index)
    save_json(CALENDAR_PATH, events)

    return f"Reminder deleted successfully: {deleted_title}"


# ============================================================
# TASK INTELLIGENCE DASHBOARD
# ============================================================

def is_task_intelligence_request(user_input):

    text = normalize_text(user_input)

    requests = {
        "task dashboard",
        "show task dashboard",
        "show my task dashboard",
        "task summary",
        "show task summary",
        "show my task summary",
        "task intelligence",
        "show task intelligence",
        "analyze my tasks",
        "analyse my tasks",
        "analyze my task list",
        "analyse my task list",
        "task status summary",
        "my task status",
        "mere tasks ka summary",
        "mere tasks ka analysis",
        "mere tasks analyze karo",
        "tasks analyze karo",
    }

    return text in requests


def get_task_intelligence_view():

    tasks = load_json(TASKS_PATH, [])

    if not isinstance(tasks, list):
        return "I could not read your task list."

    today = get_today_date()
    total = 0
    completed = 0
    pending = 0
    overdue = []
    due_today = []
    upcoming = []
    no_due_date = []

    for task in tasks:

        if not isinstance(task, dict):
            continue

        title = str(task.get("title", "Untitled")).strip()
        if not title:
            continue

        total += 1

        if task.get("completed", False):
            completed += 1
            continue

        pending += 1
        due_text = task.get("due_date")
        due_date = parse_task_due_date(due_text)

        item = {
            "title": title,
            "due_text": str(due_text).strip() if due_text else "Not set",
            "due_date": due_date,
        }

        if due_date is None:
            no_due_date.append(item)
        elif due_date < today:
            overdue.append(item)
        elif due_date == today:
            due_today.append(item)
        else:
            upcoming.append(item)

    overdue.sort(key=lambda x: x["due_date"] or datetime.max.date())
    due_today.sort(key=lambda x: x["title"].lower())
    upcoming.sort(key=lambda x: x["due_date"] or datetime.max.date())
    no_due_date.sort(key=lambda x: x["title"].lower())

    if total == 0:
        return "You have no tasks right now."

    completion_rate = (completed / total) * 100

    lines = [
        "JARVIS Task Intelligence",
        "",
        f"Total tasks: {total}",
        f"Completed: {completed}",
        f"Pending: {pending}",
        f"Completion: {completion_rate:.0f}%",
        "",
    ]

    if overdue:
        lines.append(f"OVERDUE ({len(overdue)})")
        for item in overdue:
            lines.append(f"- {item['title']} | Due: {item['due_text']}")
        lines.append("")

    if due_today:
        lines.append(f"DUE TODAY ({len(due_today)})")
        for item in due_today:
            lines.append(f"- {item['title']}")
        lines.append("")

    if upcoming:
        lines.append(f"UPCOMING ({len(upcoming)})")
        for item in upcoming[:5]:
            lines.append(f"- {item['title']} | Due: {item['due_text']}")
        if len(upcoming) > 5:
            lines.append(f"- ...and {len(upcoming) - 5} more")
        lines.append("")

    if no_due_date:
        lines.append(f"NO DUE DATE ({len(no_due_date)})")
        for item in no_due_date[:5]:
            lines.append(f"- {item['title']}")
        if len(no_due_date) > 5:
            lines.append(f"- ...and {len(no_due_date) - 5} more")
        lines.append("")

    if overdue:
        focus = overdue[0]["title"]
    elif due_today:
        focus = due_today[0]["title"]
    elif upcoming:
        focus = upcoming[0]["title"]
    elif no_due_date:
        focus = no_due_date[0]["title"]
    else:
        focus = None

    if focus:
        lines.append(f"Next focus: {focus}")
    else:
        lines.append("All tasks are completed.")

    return "\n".join(lines)


def deterministic_task_intelligence(user_input):

    if not is_task_intelligence_request(user_input):
        return None

    return get_task_intelligence_view()


# ============================================================
# TASK LIST
# ============================================================

def is_task_list_request(
    user_input
):

    text = normalize_text(
        user_input
    )

    exact_requests = {

        "give me my tasks",
        "give me the tasks",
        "give me my task",
        "give me the task",
        "show me my tasks",
        "show me the tasks",
        "show my tasks",
        "show tasks",
        "list my tasks",
        "list the tasks",
        "list tasks",
        "what are my tasks",
        "what are the tasks",
        "my tasks",
        "my task list",
        "show task list",
        "show me task list",
        "give me task list",

        "mere tasks dikhao",
        "mere task dikhao",
        "mere tasks batao",
        "mere task batao",
        "meri tasks dikhao",
        "meri task list dikhao",
        "mere tasks kya hain",
        "mere task kya hain",
    }

    if text in exact_requests:
        return True

    return False


def get_task_list():

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "I could not read your task list."
        )

    if not tasks:

        return (
            "You have no tasks right now."
        )

    lines = [
        "Here are your current tasks:",
        "",
        "| Title | Status | Due date |",
        "|-------|--------|----------|",
    ]

    for task in tasks:

        if not isinstance(task, dict):
            continue

        title = str(
            task.get(
                "title",
                "Untitled"
            )
        ).strip()

        status = (
            "Completed"
            if task.get(
                "completed",
                False
            )
            else "Pending"
        )

        due_date = (
            task.get(
                "due_date"
            )
            or "Not set"
        )

        lines.append(
            f"| {title} | {status} | {due_date} |"
        )

    lines.append("")

    lines.append(
        "You can ask me to create, complete, "
        "update, or delete a task."
    )

    return "\n".join(lines)


def deterministic_task_list(
    user_input
):

    if not is_task_list_request(
        user_input
    ):

        return None

    return get_task_list()


# ============================================================
# TASK PRIORITY VIEW
# ============================================================

def is_task_priority_request(user_input):

    text = normalize_text(
        user_input
    )

    requests = {
        "show task priorities",
        "show my task priorities",
        "show task priority",
        "show my task priority",
        "task priorities",
        "task priority",
        "prioritize my tasks",
        "prioritise my tasks",
        "prioritize tasks",
        "prioritise tasks",
        "sort my tasks by priority",
        "sort tasks by priority",
        "mere tasks priority dikhao",
        "tasks priority dikhao",
        "mere tasks priority batao",
        "tasks priority batao",
    }

    return text in requests


def get_task_priority_view():

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "I could not read your task list."
        )

    today = get_today_date()
    overdue = []
    due_soon = []
    no_due_date = []
    completed = []

    for task in tasks:

        if not isinstance(task, dict):
            continue

        title = str(
            task.get("title", "Untitled")
        ).strip()

        if not title:
            continue

        if task.get("completed", False):
            completed.append(title)
            continue

        due_text = task.get("due_date")
        due_date = parse_task_due_date(
            due_text
        )

        item = {
            "title": title,
            "due_text": (
                str(due_text).strip()
                if due_text
                else "Not set"
            ),
        }

        if due_date is None:
            no_due_date.append(item)
            continue

        if due_date < today:
            overdue.append(item)
            continue

        if due_date <= today + timedelta(days=7):
            due_soon.append(item)
            continue

        no_due_date.append(item)

    overdue.sort(
        key=lambda item: parse_task_due_date(
            item["due_text"]
        ) or datetime.max.date()
    )

    due_soon.sort(
        key=lambda item: parse_task_due_date(
            item["due_text"]
        ) or datetime.max.date()
    )

    if not overdue and not due_soon and not no_due_date:

        return (
            "You have no pending tasks."
        )

    lines = [
        "Task priorities:",
        "",
        f"Today: {today.strftime('%Y-%m-%d')}",
        "",
    ]

    if overdue:

        lines.append("OVERDUE")

        for item in overdue:

            lines.append(
                f"- {item['title']} | Due: "
                f"{item['due_text']}"
            )

        lines.append("")

    if due_soon:

        lines.append("DUE SOON (within 7 days)")

        for item in due_soon:

            lines.append(
                f"- {item['title']} | Due: "
                f"{item['due_text']}"
            )

        lines.append("")

    if no_due_date:

        lines.append("NO DUE DATE / LOWER PRIORITY")

        for item in no_due_date:

            lines.append(
                f"- {item['title']} | Due: "
                f"{item['due_text']}"
            )

        lines.append("")

    if completed:

        lines.append(
            f"Completed tasks: {len(completed)}"
        )

        lines.append("")

    if overdue:
        start_with = overdue[0]["title"]
    elif due_soon:
        start_with = due_soon[0]["title"]
    else:
        start_with = no_due_date[0]["title"]

    lines.append(
        f"Start with: {start_with}"
    )

    return "\n".join(lines)


def deterministic_task_priority(user_input):

    if not is_task_priority_request(
        user_input
    ):

        return None

    return get_task_priority_view()


# ============================================================
# STUDY PLANNER
# ============================================================

def is_study_planner_request(
    user_input
):

    text = normalize_text(
        user_input
    )

    patterns = [

        "what should i study today",
        "what should i study",
        "what do i study today",
        "what do i need to study",
        "what should i learn today",
        "what should i learn",
        "study plan",
        "make a study plan",
        "make my study plan",
        "today study plan",
        "today's study plan",
        "today study",
        "aaj kya padhna chahiye",
        "aaj kya padhu",
        "aaj kya padhna hai",
        "mujhe aaj kya padhna chahiye",
        "mujhe aaj kya padhna hai",
        "aaj ka study plan",
        "aaj ka padhai plan",
        "pending study tasks",
        "pending study task",
    ]

    return any(
        pattern in text
        for pattern in patterns
    )


def is_exam_study_plan_request(user_input):

    text = normalize_text(user_input)

    has_exam = any(
        word in text
        for word in [
            "exam",
            "test",
            "paper",
            "examination",
        ]
    )

    has_plan = any(
        phrase in text
        for phrase in [
            "study plan",
            "study schedule",
            "what should i study",
            "what do i study",
            "make a plan",
            "plan for",
            "padhai plan",
        ]
    )

    return has_exam and has_plan


def parse_exam_date(user_input):

    text = normalize_text(user_input)
    today = get_today_date()

    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    match = re.search(
        r"(?:next\s+|this\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        text,
        re.IGNORECASE
    )

    if match:

        target = weekday_map[
            match.group(1).lower()
        ]

        days_ahead = (
            target - today.weekday()
        ) % 7

        # "next Friday" should mean the coming Friday,
        # except when today itself is Friday.
        if "next" in text and days_ahead == 0:
            days_ahead = 7

        if days_ahead == 0 and "next" not in text:
            days_ahead = 7

        return today + timedelta(
            days=days_ahead
        )

    date_match = re.search(
        r"(\d{4}-\d{1,2}-\d{1,2})",
        text
    )

    if date_match:

        try:
            return datetime.strptime(
                date_match.group(1),
                "%Y-%m-%d"
            ).date()
        except ValueError:
            return None

    return None


def extract_exam_subject(user_input):

    text = str(user_input).strip()

    patterns = [
        r"(?:my|i have|for)\s+(.+?)\s+exam",
        r"(.+?)\s+exam",
        r"(.+?)\s+test",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            subject = match.group(1).strip()

            subject = re.sub(
                r"^(?:a|an|the)\s+",
                "",
                subject,
                flags=re.IGNORECASE
            ).strip()

            if subject and len(subject) <= 60:
                return subject

    return "your exam"


def create_exam_study_plan(
    subject,
    exam_date,
    tasks
):

    today = get_today_date()

    if exam_date <= today:
        return (
            f"Your exam date is {exam_date.strftime('%Y-%m-%d')}, "
            "which is today or already passed. "
            "Give me a future exam date so I can create the plan."
        )

    available_days = (
        exam_date - today
    ).days

    topics = [
        "Basics and syntax",
        "Variables, data types and operators",
        "Conditionals and loops",
        "Functions and scope",
        "Arrays and strings",
        "Objects and methods",
        "DOM and events",
        "Practice questions and debugging",
        "Revision and mock test",
    ]

    study_days = max(
        1,
        available_days
    )

    selected_topics = topics[:min(study_days, len(topics))]

    if study_days > len(selected_topics):
        selected_topics += [
            "Revision and practice"
        ] * (
            study_days - len(selected_topics)
        )

    existing_titles = {
        str(task.get("title", "")).strip().lower()
        for task in tasks
        if isinstance(task, dict)
    }

    created = []

    for index, topic in enumerate(
        selected_topics
    ):

        study_date = today + timedelta(
            days=index
        )

        title = (
            f"{subject} - {topic}"
        )

        if title.lower() in existing_titles:
            continue

        tasks.append(
            {
                "title": title,
                "due_date": study_date.strftime(
                    "%Y-%m-%d"
                ),
                "completed": False,
            }
        )

        existing_titles.add(
            title.lower()
        )

        created.append(
            (
                study_date,
                title
            )
        )

    save_json(
        TASKS_PATH,
        tasks
    )

    lines = [
        f"Study plan for {subject}:",
        f"Exam: {exam_date.strftime('%Y-%m-%d')}",
        "",
    ]

    for number, (study_date, title) in enumerate(
        created,
        start=1
    ):
        lines.append(
            f"{number}. {study_date.strftime('%Y-%m-%d')} - {title}"
        )

    if not created:
        lines.append(
            "Your study-plan tasks already exist."
        )

    lines.extend([
        "",
        "Start with today's topic and complete the tasks in order."
    ])

    return "\n".join(lines)


def parse_task_due_date(
    due_date
):

    if not due_date:
        return None

    text = normalize_text(
        due_date
    )

    relative = get_relative_date(
        text
    )

    if relative:
        return relative

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for date_format in formats:

        try:

            return datetime.strptime(
                text,
                date_format
            ).date()

        except ValueError:

            continue

    return None


def is_start_study_request(user_input):

    text = normalize_text(user_input)

    triggers = (
        "start today's study",
        "start todays study",
        "start today study",
        "start my study",
        "start studying",
        "start today's topic",
        "start todays topic",
        "start today topic",
        "start study",
        "begin today's study",
        "begin todays study",
        "begin study",
        "study now",
        "start padhai",
        "padhai shuru",
        "aaj ki padhai shuru",
        "aaj padhna shuru",
    )

    return any(trigger in text for trigger in triggers)


def get_current_study_task():

    tasks = load_json(TASKS_PATH, [])

    if not isinstance(tasks, list):
        return None

    today = get_today_date()
    pending = []

    for task in tasks:

        if not isinstance(task, dict):
            continue

        if task.get("completed", False):
            continue

        title = str(task.get("title", "")).strip()

        if not title:
            continue

        due_text = task.get("due_date")
        due_date = parse_task_due_date(due_text)

        pending.append({
            "title": title,
            "due_date": due_date,
            "due_date_text": str(due_text).strip() if due_text else None,
        })

    if not pending:
        return None

    def sort_key(task):

        due_date = task["due_date"]

        if due_date is None:
            return (2, datetime.max.date())

        if due_date < today:
            return (0, due_date)

        return (1, due_date)

    pending.sort(key=sort_key)
    return pending[0]


def get_study_material(title):

    text = normalize_text(title)

    material = {
        "topic": title,
        "explanation": "",
        "examples": [],
        "practice": [],
    }

    if "variables" in text or "data types" in text or "operators" in text:
        material["explanation"] = (
            "JavaScript variables store values. Common data types are "
            "string, number, boolean, undefined, null and object. "
            "Operators are used to calculate or compare values."
        )
        material["examples"] = [
            "let age = 20;",
            "let name = \"Aahad\";",
            "let passed = true;",
            "let total = 10 + 5;",
        ]
        material["practice"] = [
            "Create a variable for your age.",
            "Store two numbers and print their sum.",
            "Create a boolean variable named isStudent.",
        ]

    elif "conditionals" in text or "loops" in text:
        material["explanation"] = (
            "Conditionals control decisions with if/else. Loops repeat "
            "code while a condition is true or for a fixed number of times."
        )
        material["examples"] = [
            "if (age >= 18) { console.log(\"Adult\"); }",
            "for (let i = 1; i <= 5; i++) { console.log(i); }",
        ]
        material["practice"] = [
            "Check whether a number is even or odd.",
            "Print numbers from 1 to 10 using a loop.",
            "Print only numbers greater than 5 from 1 to 10.",
        ]

    elif "functions" in text or "scope" in text:
        material["explanation"] = (
            "A function is a reusable block of code. Parameters receive "
            "input, and return sends a value back. Scope controls where a variable can be used."
        )
        material["examples"] = [
            "function add(a, b) { return a + b; }",
            "let result = add(5, 3);",
        ]
        material["practice"] = [
            "Create a function that returns the square of a number.",
            "Create a function that checks whether a number is positive.",
            "Create a function that accepts two numbers and returns the larger one.",
        ]

    elif "arrays" in text or "strings" in text:
        material["explanation"] = (
            "Arrays store multiple values in order. Strings store text. "
            "JavaScript provides methods such as push, pop, length and includes."
        )
        material["examples"] = [
            "let nums = [10, 20, 30];",
            "nums.push(40);",
            "let name = \"JavaScript\";",
            "console.log(name.length);",
        ]
        material["practice"] = [
            "Create an array of five numbers.",
            "Add one item using push().",
            "Find the length of a string.",
        ]

    elif "objects" in text or "methods" in text:
        material["explanation"] = (
            "Objects store data as key-value pairs. Methods are functions "
            "that can work with object data."
        )
        material["examples"] = [
            "let user = { name: \"Aahad\", age: 20 };",
            "console.log(user.name);",
        ]
        material["practice"] = [
            "Create a student object with name and age.",
            "Read one property from the object.",
            "Add a new property to the object.",
        ]

    elif "dom" in text or "events" in text:
        material["explanation"] = (
            "The DOM lets JavaScript access and change HTML elements. "
            "Events let your code react to actions such as clicks."
        )
        material["examples"] = [
            "document.querySelector(\"#btn\");",
            "button.addEventListener(\"click\", () => { console.log(\"Clicked\"); });",
        ]
        material["practice"] = [
            "Select a button with querySelector().",
            "Add a click event to the button.",
            "Change an element's text after the click.",
        ]

    elif "debugging" in text or "practice" in text or "revision" in text:
        material["explanation"] = (
            "Revision means recalling concepts without looking at notes. "
            "Debugging means finding and fixing errors by reading the error message, "
            "checking values and testing one change at a time."
        )
        material["examples"] = [
            "console.log(value);",
            "Check the browser console when JavaScript throws an error.",
        ]
        material["practice"] = [
            "Solve 3 small JavaScript problems without copying code.",
            "Debug one old project error.",
            "Explain one JavaScript topic in your own words.",
        ]

    else:
        material["explanation"] = (
            "Study this topic in small steps: understand the concept, "
            "write a small example, then solve practice questions without copying."
        )
        material["examples"] = [
            "Write one small example for the topic.",
            "Run it and inspect the output.",
        ]
        material["practice"] = [
            "Write one example yourself.",
            "Change the example and predict the output.",
            "Solve one small problem using the topic.",
        ]

    return material


def deterministic_start_study(user_input):

    if not is_start_study_request(user_input):
        return None

    task = get_current_study_task()

    if task is None:
        return (
            "There are no pending study tasks.\n\n"
            "Your current study tasks are completed."
        )

    material = get_study_material(task["title"])

    lines = [
        "JARVIS STUDY SESSION",
        "",
        f"Today's topic: {task['title']}",
        "",
        "QUICK EXPLANATION",
        material["explanation"],
        "",
        "EXAMPLES",
    ]

    for number, example in enumerate(material["examples"], start=1):
        lines.append(f"{number}. {example}")

    lines.extend([
        "",
        "PRACTICE",
    ])

    for number, question in enumerate(material["practice"], start=1):
        lines.append(f"{number}. {question}")

    lines.extend([
        "",
        "When you finish, say: Complete today's study task",
    ])

    return "\n".join(lines)


def get_smart_study_plan(user_input=None):

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "I could not read your task list."
        )

    today = get_today_date()

    pending_tasks = []

    for task in tasks:

        if not isinstance(task, dict):
            continue

        if task.get(
            "completed",
            False
        ):
            continue

        title = str(
            task.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        due_date_text = task.get(
            "due_date"
        )

        due_date = parse_task_due_date(
            due_date_text
        )

        pending_tasks.append(
            {
                "title": title,
                "due_date": due_date,
                "due_date_text": (
                    str(due_date_text).strip()
                    if due_date_text
                    else None
                ),
            }
        )

    if not pending_tasks:

        return (
            "There are no pending study tasks.\n\n"
            "All your current tasks are completed."
        )

    def sort_key(task):

        due_date = task["due_date"]

        if due_date is None:

            return (
                2,
                datetime.max.date()
            )

        if due_date < today:

            return (
                0,
                due_date
            )

        return (
            1,
            due_date
        )

    pending_tasks.sort(
        key=sort_key
    )

    lines = [

        "Here is your study plan:",
        "",

        f"Today: "
        f"{today.strftime('%Y-%m-%d')}",

        "",

        "Priority order:",
    ]

    for number, task in enumerate(
        pending_tasks,
        start=1
    ):

        due_date = task["due_date"]

        if due_date:

            if due_date < today:

                status = "OVERDUE"

            elif due_date == today:

                status = "DUE TODAY"

            else:

                status = "UPCOMING"

            due_text = (
                f"{task['due_date_text']} "
                f"({status})"
            )

        else:

            due_text = "No due date"

        lines.append(
            f"{number}. "
            f"{task['title']} "
            f"| Due: {due_text}"
        )

    lines.append("")

    first_task = pending_tasks[0]

    lines.append(
        f"Start with: {first_task['title']}"
    )

    lines.append("")

    lines.append(
        "This plan uses only your confirmed "
        "pending tasks."
    )

    return "\n".join(lines)


# ============================================================
# COMPLETE TASK
# ============================================================

def deterministic_complete_task(
    user_input
):

    text = user_input.strip()

    patterns = [

        re.compile(
            r"^\s*complete\s+my\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*finish\s+my\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*complete\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*finish\s+(.+?)\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*mark\s+(.+?)\s+as\s+completed\s*$",
            re.IGNORECASE
        ),

        re.compile(
            r"^\s*mark\s+(.+?)\s+completed\s*$",
            re.IGNORECASE
        ),
    ]

    task_title = None

    for pattern in patterns:

        match = pattern.match(
            text
        )

        if match:

            task_title = (
                match.group(1)
                .strip()
            )

            break

    if not task_title:
        return None

    from .tools import complete_task

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not isinstance(tasks, list):

        return (
            "I could not read your task list."
        )

    normalized_title = normalize_text(
        task_title
    )

    matches = []

    for index, task in enumerate(
        tasks
    ):

        if not isinstance(task, dict):
            continue

        if task.get(
            "completed",
            False
        ):
            continue

        title = str(
            task.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        normalized_task = normalize_text(
            title
        )

        if (
            normalized_task == normalized_title
            or normalized_title in normalized_task
            or normalized_task in normalized_title
        ):

            matches.append(
                {
                    "index": index,
                    "title": title
                }
            )

    if not matches:

        return (
            f"No pending task found matching "
            f"'{task_title}'."
        )

    if len(matches) > 1:

        lines = [
            f"I found {len(matches)} "
            "matching pending tasks:",
            "",
        ]

        for number, match in enumerate(
            matches,
            start=1
        ):

            lines.append(
                f"{number}. {match['title']}"
            )

        lines.append("")

        lines.append(
            "Please tell me which one to complete."
        )

        return "\n".join(lines)

    selected_title = matches[0]["title"]

    try:

        result = complete_task.invoke(
            {
                "title": selected_title
            }
        )

        return str(result)

    except Exception as error:

        return (
            "TOOL_ERROR: Could not complete "
            f"task. Reason: {error}"
        )


# ============================================================
# TOOL RESULT
# ============================================================

def tool_result_to_text(
    result
):

    if result is None:
        return ""

    if isinstance(result, str):
        return result

    return str(result)


# ============================================================
# CONFIRMATION MESSAGE
# ============================================================

def confirmation_message(
    action
):

    action_type = action.get(
        "type"
    )

    if action_type == "delete_all_tasks":

        return (
            f"WARNING: This will permanently delete "
            f"all {action.get('count', 0)} task(s).\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "task_delete":

        title = action.get(
            "title",
            "Untitled"
        )

        status = (
            "Completed"
            if action.get(
                "completed",
                False
            )
            else "Pending"
        )

        due_date = (
            action.get(
                "due_date"
            )
            or "Not set"
        )

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Delete task:\n"
            f"{title} | {status} | {due_date}\n\n"
            "This action cannot be undone.\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "duplicate_task_cleanup":

        return duplicate_cleanup_message(
            action
        )

    if action_type == "file_create":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Create file:\n"
            f"{action.get('file_path')}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "file_edit":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Edit file:\n"
            f"{action.get('file_path')}\n\n"
            f"Replace:\n"
            f"{action.get('old_text')}\n\n"
            f"With:\n"
            f"{action.get('new_text')}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "file_rename":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Rename file:\n"
            f"{action.get('file_path')}\n"
            "to:\n"
            f"{action.get('new_path')}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "file_move":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Move file:\n"
            f"{action.get('file_path')}\n"
            "to:\n"
            f"{action.get('destination')}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "file_delete":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Delete file:\n"
            f"{action.get('file_path')}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "calendar_update":

        old_event = (
            f"{action.get('old_title')} | "
            f"{action.get('old_date')} | "
            f"{action.get('old_time') or 'Not set'}"
        )

        new_event = (
            f"{action.get('new_title')} | "
            f"{action.get('new_date')} | "
            f"{action.get('new_time') or 'Not set'}"
        )

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Update calendar event:\n\n"
            f"OLD: {old_event}\n"
            f"NEW: {new_event}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "reminder_update":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Update reminder:\n\n"
            f"OLD: {action.get('old_title')} | "
            f"{action.get('old_date')} | "
            f"{action.get('old_time') or 'Not set'}\n"
            f"NEW: {action.get('new_title')} | "
            f"{action.get('new_date')} | "
            f"{action.get('new_time') or 'Not set'}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "reminder_delete":

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Delete reminder:\n"
            f"{action.get('title')} | "
            f"{action.get('date')} | "
            f"{action.get('time') or 'Not set'}\n\n"
            "This action cannot be undone.\n"
            "Reply yes to confirm or no to cancel."
        )

    if action_type == "calendar_delete":

        event = (
            f"{action.get('title')} | "
            f"{action.get('date')} | "
            f"{action.get('time') or 'Not set'}"
        )

        return (
            "CONFIRMATION REQUIRED\n\n"
            "Delete calendar event:\n"
            f"{event}\n\n"
            "Reply yes to confirm or no to cancel."
        )

    return (
        "CONFIRMATION REQUIRED\n"
        "Reply yes to confirm or no to cancel."
    )


# ============================================================
# CONFIRM PENDING ACTION
# ============================================================

def confirm_pending_action(
    action
):

    action_type = action.get(
        "type"
    )

    if action_type == "delete_all_tasks":

        return perform_delete_all_tasks()

    if action_type == "task_delete":

        return perform_task_delete(
            action
        )

    if action_type == "duplicate_task_cleanup":

        return perform_duplicate_task_cleanup(
            action
        )

    if action_type == "file_create":

        return perform_create_file(
            action.get("file_path"),
            action.get("content", "")
        )

    if action_type == "file_edit":

        return perform_edit_file(
            action.get("file_path"),
            action.get("old_text", ""),
            action.get("new_text", ""),
            action.get("replace_all", False)
        )

    if action_type == "file_rename":

        return perform_rename_file(
            action.get("file_path"),
            action.get("new_path")
        )

    if action_type == "file_move":

        return perform_move_file(
            action.get("file_path"),
            action.get("destination")
        )

    if action_type == "file_delete":

        return perform_delete_file(
            action.get("file_path")
        )

    if action_type == "reminder_update":

        return perform_reminder_update(action)

    if action_type == "reminder_delete":

        return perform_reminder_delete(action)

    if action_type == "calendar_update":

        return perform_update_calendar_event(
            action.get("index"),
            action.get("new_title"),
            action.get("new_date"),
            action.get("new_time", ""),
            action.get("new_description", "")
        )

    if action_type == "calendar_delete":

        return perform_delete_calendar_event(
            action.get("index")
        )

    return (
        "TOOL_ERROR: Unknown confirmation action."
    )


# ============================================================
# MAIN JARVIS RUNNER
# ============================================================

def run_jarvis(
    user_input
):

    user_input = user_input.strip()

    if not user_input:

        return (
            "Please tell me what you need.",
            None
        )


    # ========================================================
    # DELETE SPECIFIC TASK
    # ========================================================

    task_delete_result = (
        deterministic_task_delete(
            user_input
        )
    )

    if task_delete_result is not None:

        action = parse_confirmation_result(
            task_delete_result
        )

        if action:

            return (
                confirmation_message(
                    action
                ),
                action
            )

        return (
            task_delete_result,
            None
        )


    # ========================================================
    # REMINDER UPDATE / DELETE
    # ========================================================

    reminder_delete_result = deterministic_reminder_delete(user_input)

    if reminder_delete_result is not None:

        action = parse_confirmation_result(reminder_delete_result)

        if action:
            return (confirmation_message(action), action)

        return (reminder_delete_result, None)

    reminder_update_result = deterministic_reminder_update(user_input)

    if reminder_update_result is not None:

        action = parse_confirmation_result(reminder_update_result)

        if action:
            return (confirmation_message(action), action)

        return (reminder_update_result, None)


    # ========================================================
    # CALENDAR UPDATE
    # ========================================================

    calendar_update_result = (
        deterministic_calendar_update(
            user_input
        )
    )

    if calendar_update_result is not None:

        action = parse_confirmation_result(
            calendar_update_result
        )

        if action:

            if action.get(
                "type"
            ) == "calendar_selection":

                request = {
                    "title": action.get(
                        "request_title"
                    ),
                    "new_date": action.get(
                        "new_date"
                    ),
                    "new_time": action.get(
                        "new_time"
                    ),
                    "operation": "update",
                }

                matches = action.get(
                    "events",
                    []
                )

                response = (
                    calendar_selection_message(
                        request,
                        matches
                    )
                )

                return (
                    response,
                    action
                )

            return (
                confirmation_message(
                    action
                ),
                action
            )

        return (
            calendar_update_result,
            None
        )


    # ========================================================
    # CALENDAR DELETE
    # ========================================================

    calendar_delete_result = (
        deterministic_calendar_delete(
            user_input
        )
    )

    if calendar_delete_result is not None:

        action = parse_confirmation_result(
            calendar_delete_result
        )

        if action:

            if action.get(
                "type"
            ) == "calendar_selection":

                request = {
                    "title": action.get(
                        "request_title"
                    ),
                    "requested_date": action.get(
                        "requested_date"
                    ),
                    "operation": "delete",
                }

                matches = action.get(
                    "events",
                    []
                )

                response = (
                    calendar_selection_message(
                        request,
                        matches
                    )
                )

                return (
                    response,
                    action
                )

            return (
                confirmation_message(
                    action
                ),
                action
            )

        return (
            calendar_delete_result,
            None
        )


    # ========================================================
    # DUPLICATE TASK CLEANUP
    # ========================================================

    duplicate_cleanup_result = (
        deterministic_duplicate_task_cleanup(
            user_input
        )
    )

    if duplicate_cleanup_result is not None:

        action = parse_confirmation_result(
            duplicate_cleanup_result
        )

        if action:

            return (
                confirmation_message(
                    action
                ),
                action
            )

        return (
            duplicate_cleanup_result,
            None
        )


    # ========================================================
    # TASK PRIORITY
    # ========================================================

    task_priority_result = (
        deterministic_task_priority(
            user_input
        )
    )

    if task_priority_result is not None:

        return (
            task_priority_result,
            None
        )


    # ========================================================
    # CALENDAR CONFLICT + SMART SCHEDULE
    # ========================================================

    calendar_conflict_result = (
        deterministic_calendar_conflict_route(
            user_input
        )
    )

    if calendar_conflict_result is not None:

        return (
            calendar_conflict_result,
            None
        )


    # ========================================================
    # CALENDAR INTELLIGENCE
    # ========================================================

    calendar_intelligence_result = (
        deterministic_calendar_intelligence(
            user_input
        )
    )

    if calendar_intelligence_result is not None:

        return (
            calendar_intelligence_result,
            None
        )


    # ========================================================
    # REMINDER ENGINE
    # ========================================================

    reminder_result = deterministic_reminder_route(
        user_input
    )

    if reminder_result is not None:

        return (
            reminder_result,
            None
        )


    # ========================================================
    # TASK INTELLIGENCE
    # ========================================================

    task_intelligence_result = (
        deterministic_task_intelligence(
            user_input
        )
    )

    if task_intelligence_result is not None:

        return (
            task_intelligence_result,
            None
        )


    # ========================================================
    # TASK LIST
    # ========================================================

    task_list_result = (
        deterministic_task_list(
            user_input
        )
    )

    if task_list_result is not None:

        return (
            task_list_result,
            None
        )


    # ========================================================
    # START STUDY SESSION
    # ========================================================

    start_study_result = deterministic_start_study(
        user_input
    )

    if start_study_result is not None:

        return (
            start_study_result,
            None
        )


    # ========================================================
    # STUDY PLANNER
    # ========================================================

    if is_study_planner_request(
        user_input
    ):

        return (
            get_smart_study_plan(user_input),
            None
        )


    # ========================================================
    # COMPLETE TASK
    # ========================================================

    complete_result = (
        deterministic_complete_task(
            user_input
        )
    )

    if complete_result is not None:

        return (
            complete_result,
            None
        )


    # ========================================================
    # CREATE TASK
    # ========================================================

    create_task_result = (
        deterministic_create_task(
            user_input
        )
    )

    if create_task_result is not None:

        return (
            create_task_result,
            None
        )


    # ========================================================
    # FILE ROUTING
    # ========================================================

    file_result = (
        deterministic_file_route(
            user_input
        )
    )

    if file_result is not None:

        action = parse_confirmation_result(
            file_result
        )

        if action:

            return (
                confirmation_message(
                    action
                ),
                action
            )

        return (
            tool_result_to_text(
                file_result
            ),
            None
        )


    # ========================================================
    # GENERIC LLM TOOL LOOP
    # ========================================================

    try:

        agent = create_agent()

    except Exception as error:

        return (
            format_llm_error(
                error
            ),
            None
        )


    messages = [

        (
            "system",
            """
You are JARVIS, a personal AI operating assistant.

Understand English, Hindi and Hinglish.

If the user speaks Hindi or Hinglish,
reply in Roman Hindi/Hinglish.

Never use Devanagari.

Be concise and practical.

Use tools when needed.

Never invent tool results.

For current date or time,
use get_current_time.

For tasks:
use get_tasks, create_task, update_task,
complete_task and delete_all_tasks.

IMPORTANT:
If the user wants to complete, finish,
or mark a task as completed, use the
complete_task tool.

IMPORTANT:
Before creating a task, check whether
the same task already exists.

Task titles are case-insensitive.

For example:
"Study JavaScript"
and
"study JavaScript"
are the same task.

Do not create duplicate tasks.

Specific task deletion is handled by the
deterministic task delete system.

For calendar:
use get_calendar, create_calendar_event,
update_calendar_event and delete_calendar_event.

Calendar updates and calendar deletions
require confirmation.

For memory:
use remember_fact and recall_memory.

For calculations:
use calculate.

For weather:
use get_weather.

For websites:
use open_website.

For supported applications:
use open_application.

For files:
use list_files, search_files,
search_file_contents, open_file and read_file.

For file creation, editing, renaming,
moving and deletion, use the corresponding
tools and respect their confirmation results.

Never claim an action succeeded unless
the tool confirms it.

Stop when the user's request is complete.
"""
        ),

        (
            "human",
            user_input
        )
    ]


    for _ in range(
        MAX_ITERATIONS
    ):

        try:

            response = invoke_agent_with_retry(
                agent,
                messages
            )

        except Exception as error:

            return (
                format_llm_error(
                    error
                ),
                None
            )


        if not response.tool_calls:

            content = response.content

            if not content:

                content = (
                    "I could not generate a response."
                )

            return (
                content,
                None
            )


        messages.append(
            response
        )


        for tool_call in response.tool_calls:

            tool_name = tool_call.get(
                "name"
            )

            tool_args = tool_call.get(
                "args",
                {}
            )

            tool_call_id = tool_call.get(
                "id"
            )

            selected_tool = None


            for available_tool in TOOLS:

                if available_tool.name == tool_name:

                    selected_tool = (
                        available_tool
                    )

                    break


            if selected_tool is None:

                tool_output = (
                    "TOOL_ERROR: Unknown tool: "
                    f"{tool_name}"
                )

            else:

                try:

                    tool_output = (
                        selected_tool.invoke(
                            tool_args
                        )
                    )

                except Exception as error:

                    tool_output = (
                        "TOOL_ERROR: "
                        f"{error}"
                    )


            action = parse_confirmation_result(
                tool_output
            )


            if action:

                if action.get(
                    "type"
                ) == "calendar_selection":

                    request = {
                        "title": action.get(
                            "request_title"
                        ),
                        "operation": action.get(
                            "operation",
                            "update"
                        ),
                        "new_date": action.get(
                            "new_date"
                        ),
                        "new_time": action.get(
                            "new_time"
                        ),
                    }

                    matches = action.get(
                        "events",
                        []
                    )

                    response_text = (
                        calendar_selection_message(
                            request,
                            matches
                        )
                    )

                    return (
                        response_text,
                        action
                    )


                return (
                    confirmation_message(
                        action
                    ),
                    action
                )


            messages.append(
                ToolMessage(
                    content=str(
                        tool_output
                    ),
                    tool_call_id=tool_call_id
                )
            )


    return (
        "I could not complete the request within "
        "the allowed steps.",
        None
    )
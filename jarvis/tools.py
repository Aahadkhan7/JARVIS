from datetime import datetime
import json
from pathlib import Path

import requests
from langchain_core.tools import tool

from .memory import store_fact, search_facts


TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"
CALENDAR_FILE = Path(__file__).parent.parent / "data" / "calendar.json"


@tool
def get_current_time() -> str:
    """Get the current date, day, and time."""

    now = datetime.now()

    return now.strftime(
        "%A, %B %d, %Y — %I:%M:%S %p"
    )


@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""

    try:

        result = eval(
            expression,
            {"__builtins__": {}},
            {}
        )

        return str(result)

    except Exception as error:

        return (
            f"TOOL_ERROR: Calculation failed. "
            f"Reason: {error}"
        )


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""

    try:

        url = f"https://wttr.in/{city}?format=j1"

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        current = data["current_condition"][0]

        temperature = current["temp_C"]
        feels_like = current["FeelsLikeC"]
        humidity = current["humidity"]

        description = (
            current["weatherDesc"][0]["value"]
        )

        return (
            f"Weather in {city}: {description}. "
            f"Temperature: {temperature}°C. "
            f"Feels like: {feels_like}°C. "
            f"Humidity: {humidity}%."
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Weather lookup failed "
            f"for {city}. Reason: {error}"
        )


@tool
def remember_fact(fact: str) -> str:
    """Save an important fact about the user."""

    try:

        store_fact(fact)

        return f"Remembered: {fact}"

    except Exception as error:

        return (
            f"TOOL_ERROR: Memory save failed. "
            f"Reason: {error}"
        )


@tool
def recall_memory(query: str) -> str:
    """Search previously remembered facts."""

    try:

        results = search_facts(query)

        if not results:

            return (
                "I don't have any matching memories."
            )

        return "\n".join(results)

    except Exception as error:

        return (
            f"TOOL_ERROR: Memory search failed. "
            f"Reason: {error}"
        )


def load_tasks():

    if not TASKS_FILE.exists():

        return []

    with open(
        TASKS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_tasks(tasks):

    TASKS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        TASKS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            tasks,
            file,
            indent=4
        )


@tool
def create_task(
    title: str,
    due_date: str = ""
) -> str:
    """Create a new task and prevent duplicate task titles."""

    try:

        title = title.strip()

        if not title:

            return (
                "TOOL_ERROR: Task title cannot be empty."
            )

        tasks = load_tasks()

        for task in tasks:

            if (
                task["title"].strip().lower()
                == title.lower()
            ):

                return (
                    f"Task already exists: "
                    f"{task['title']}"
                )

        task = {
            "title": title,
            "due_date": due_date.strip(),
            "completed": False
        }

        tasks.append(task)

        save_tasks(tasks)

        return f"Task created: {title}"

    except Exception as error:

        return (
            f"TOOL_ERROR: Task creation failed. "
            f"Reason: {error}"
        )

@tool
def get_tasks(
    status: str = "all"
) -> str:
    """
    Get saved tasks.

    status can be:
    all
    pending
    completed
    """

    try:

        tasks = load_tasks()

        if not tasks:

            return "No tasks found."

        status = status.lower().strip()

        if status == "pending":

            tasks = [
                task
                for task in tasks
                if not task["completed"]
            ]

        elif status == "completed":

            tasks = [
                task
                for task in tasks
                if task["completed"]
            ]

        elif status != "all":

            return (
                "TOOL_ERROR: Invalid task status. "
                "Use all, pending, or completed."
            )

        if not tasks:

            return (
                f"No {status} tasks found."
            )

        result = []

        for index, task in enumerate(
            tasks,
            start=1
        ):

            status_text = (
                "Completed"
                if task["completed"]
                else "Pending"
            )

            result.append(
                f"{index}. "
                f"{task['title']} — "
                f"{status_text} — "
                f"Due: "
                f"{task['due_date'] or 'Not set'}"
            )

        return "\n".join(result)

    except Exception as error:

        return (
            f"TOOL_ERROR: Task lookup failed. "
            f"Reason: {error}"
        )


@tool
def update_task(
    title: str,
    new_title: str = "",
    due_date: str = ""
) -> str:
    """
    Update an existing task.

    Can update the task title and/or due date.
    """

    try:

        tasks = load_tasks()

        if not tasks:

            return "No tasks found."

        for task in tasks:

            if task["title"].lower() == title.lower():

                old_title = task["title"]

                if new_title.strip():

                    task["title"] = new_title.strip()

                if due_date.strip():

                    task["due_date"] = due_date.strip()

                save_tasks(tasks)

                return (
                    f"Task updated: {old_title} -> "
                    f"{task['title']} — Due: "
                    f"{task['due_date'] or 'Not set'}"
                )

        return f"Task not found: {title}"

    except Exception as error:

        return (
            f"TOOL_ERROR: Task update failed. "
            f"Reason: {error}"
        )


@tool
def complete_task(title: str) -> str:
    """Mark a task as completed."""

    try:

        tasks = load_tasks()

        if not tasks:

            return "No tasks found."

        for task in tasks:

            if task["title"].lower() == title.lower():

                if task["completed"]:

                    return (
                        f"Task already completed: {title}"
                    )

                task["completed"] = True

                save_tasks(tasks)

                return f"Task completed: {title}"

        return f"Task not found: {title}"

    except Exception as error:

        return (
            f"TOOL_ERROR: Task completion failed. "
            f"Reason: {error}"
        )


def load_calendar():

    try:

        if not CALENDAR_FILE.exists():

            return []

        with open(
            CALENDAR_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return []


def save_calendar(events):

    CALENDAR_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        CALENDAR_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            events,
            file,
            indent=4
        )


@tool
def get_calendar(
    date: str = ""
) -> str:
    """Get calendar events for a specific date."""

    try:

        events = load_calendar()

        if not events:

            return "No calendar events found."

        if date:

            events = [
                event
                for event in events
                if event["date"].lower()
                == date.lower()
            ]

        if not events:

            return (
                f"No calendar events found for {date}."
            )

        result = []

        for index, event in enumerate(
            events,
            start=1
        ):

            time = (
                event.get("time")
                or "No time set"
            )

            description = (
                event.get("description")
                or ""
            )

            result.append(
                f"{index}. "
                f"{event['title']} — "
                f"{event['date']} — "
                f"{time}"
                + (
                    f" — {description}"
                    if description
                    else ""
                )
            )

        return "\n".join(result)

    except Exception as error:

        return (
            f"TOOL_ERROR: Calendar lookup failed. "
            f"Reason: {error}"
        )


@tool
def create_calendar_event(
    title: str,
    date: str,
    time: str = "",
    description: str = ""
) -> str:
    """Create and save a calendar event."""

    try:

        events = load_calendar()

        event = {
            "title": title,
            "date": date,
            "time": time,
            "description": description
        }

        events.append(event)

        save_calendar(events)

        return (
            f"Calendar event created: "
            f"{title} on {date}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Calendar event creation "
            f"failed. Reason: {error}"
        )


@tool
def delete_all_tasks() -> str:
    """
    Delete all tasks.

    This is a destructive action.
    User confirmation is required.
    """

    return (
        "CONFIRMATION_REQUIRED: "
        "This action would permanently delete "
        "all tasks. User confirmation is required "
        "before execution."
    )


TOOLS = [
    get_current_time,
    calculate,
    get_weather,
    remember_fact,
    recall_memory,
    create_task,
    get_tasks,
    update_task,
    complete_task,
    get_calendar,
    create_calendar_event,
    delete_all_tasks,
]
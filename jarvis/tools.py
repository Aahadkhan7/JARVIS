from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import webbrowser

import requests
from langchain_core.tools import tool

from .memory import store_fact, search_facts


TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"
CALENDAR_FILE = Path(__file__).parent.parent / "data" / "calendar.json"
PROJECT_DIR = Path(__file__).parent.parent

IGNORED_FOLDERS = {
    "venv",
    ".git",
    "__pycache__",
    "chroma_db",
}


# =========================
# TIME
# =========================

@tool
def get_current_time() -> str:
    """Get the current date, day, and time."""

    now = datetime.now()

    return now.strftime(
        "%A, %B %d, %Y — %I:%M:%S %p"
    )


# =========================
# CALCULATOR
# =========================

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


# =========================
# WEATHER
# =========================

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

        description = current[
            "weatherDesc"
        ][0]["value"]

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


# =========================
# MEMORY
# =========================

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

            return "I don't have any matching memories."

        return "\n".join(results)

    except Exception as error:

        return (
            f"TOOL_ERROR: Memory search failed. "
            f"Reason: {error}"
        )


# =========================
# TASKS
# =========================

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
                "TOOL_ERROR: Task title "
                "cannot be empty."
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
    """Update an existing task."""

    try:

        tasks = load_tasks()

        if not tasks:
            return "No tasks found."

        for task in tasks:

            if (
                task["title"].lower()
                == title.lower()
            ):

                old_title = task["title"]

                if new_title.strip():

                    task["title"] = (
                        new_title.strip()
                    )

                if due_date.strip():

                    task["due_date"] = (
                        due_date.strip()
                    )

                save_tasks(tasks)

                return (
                    f"Task updated: "
                    f"{old_title} -> "
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
def complete_task(
    title: str
) -> str:
    """Mark a task as completed."""

    try:

        tasks = load_tasks()

        if not tasks:
            return "No tasks found."

        for task in tasks:

            if (
                task["title"].lower()
                == title.lower()
            ):

                if task["completed"]:

                    return (
                        f"Task already completed: "
                        f"{title}"
                    )

                task["completed"] = True

                save_tasks(tasks)

                return (
                    f"Task completed: {title}"
                )

        return f"Task not found: {title}"

    except Exception as error:

        return (
            f"TOOL_ERROR: Task completion failed. "
            f"Reason: {error}"
        )


# =========================
# CALENDAR
# =========================

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
                f"No calendar events found "
                f"for {date}."
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
            f"TOOL_ERROR: Calendar event "
            f"creation failed. "
            f"Reason: {error}"
        )


# =========================
# DESKTOP TOOLS
# =========================

@tool
def open_website(
    url: str
) -> str:
    """Open a website in the default web browser."""

    try:

        url = url.strip()

        if not url.startswith(
            ("http://", "https://")
        ):

            return (
                "TOOL_ERROR: Website URL must "
                "start with http:// or https://."
            )

        webbrowser.open(url)

        return (
            f"Website opened: {url}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not open "
            f"website. Reason: {error}"
        )


@tool
def open_application(
    application: str
) -> str:
    """
    Open a safe predefined Windows application.

    Supported applications:
    notepad
    calculator
    vscode
    """

    try:

        application = (
            application
            .lower()
            .strip()
        )

        applications = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "vscode": ["code"],
        }

        command = applications.get(
            application
        )

        if command is None:

            return (
                "TOOL_ERROR: Application "
                "not supported. "
                "Supported: notepad, calculator, vscode."
            )

        subprocess.Popen(
            command,
            shell=False
        )

        return (
            f"Application opened: "
            f"{application}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not open "
            f"application. Reason: {error}"
        )


@tool
def open_jarvis_folder() -> str:
    """Open the JARVIS project folder in Windows Explorer."""

    try:

        folder = PROJECT_DIR

        os.startfile(folder)

        return (
            "JARVIS project folder opened."
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not open "
            f"JARVIS folder. Reason: {error}"
        )


# =========================
# FILE ASSISTANT
# =========================

def is_ignored_path(path: Path) -> bool:
    """Check whether a path contains an ignored folder."""

    return any(
        part in IGNORED_FOLDERS
        for part in path.parts
    )


def find_project_files(filename: str):
    """Find matching files while ignoring system/cache folders."""

    matches = []

    for item in PROJECT_DIR.rglob("*"):

        if is_ignored_path(item):
            continue

        if not item.is_file():
            continue

        if item.name.lower() == filename.lower():

            matches.append(item)

    return matches


@tool
def list_files(
    folder: str = ""
) -> str:
    """
    List files and folders inside a directory.

    If no folder is provided, use the JARVIS project folder.
    """

    try:

        if folder.strip():

            target = Path(
                folder
            ).expanduser()

        else:

            target = PROJECT_DIR

        if not target.exists():

            return (
                f"TOOL_ERROR: Folder not found: "
                f"{target}"
            )

        if not target.is_dir():

            return (
                f"TOOL_ERROR: Not a folder: "
                f"{target}"
            )

        items = sorted(
            target.iterdir(),
            key=lambda item: (
                not item.is_dir(),
                item.name.lower()
            )
        )

        result = []

        for item in items:

            if item.name in IGNORED_FOLDERS:

                continue

            item_type = (
                "[FOLDER]"
                if item.is_dir()
                else "[FILE]"
            )

            result.append(
                f"{item_type} {item.name}"
            )

        if not result:

            return (
                f"Folder is empty: {target}"
            )

        return (
            f"Contents of {target}:\n"
            + "\n".join(result)
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not list files. "
            f"Reason: {error}"
        )


@tool
def search_files(
    filename: str,
    folder: str = ""
) -> str:
    """
    Search for files or folders by name.

    Searches recursively while ignoring:
    venv
    .git
    __pycache__
    chroma_db
    """

    try:

        filename = filename.strip()

        if not filename:

            return (
                "TOOL_ERROR: Filename cannot be empty."
            )

        if folder.strip():

            target = Path(
                folder
            ).expanduser()

        else:

            target = PROJECT_DIR

        if not target.exists():

            return (
                f"TOOL_ERROR: Folder not found: "
                f"{target}"
            )

        if not target.is_dir():

            return (
                f"TOOL_ERROR: Not a folder: "
                f"{target}"
            )

        matches = []

        for item in target.rglob("*"):

            if is_ignored_path(item):
                continue

            if filename.lower() in item.name.lower():

                matches.append(
                    str(item)
                )

        if not matches:

            return (
                f"No files or folders found "
                f"matching '{filename}'."
            )

        return (
            f"Search results for '{filename}':\n"
            + "\n".join(matches[:50])
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: File search failed. "
            f"Reason: {error}"
        )


@tool
def open_file(
    file_path: str
) -> str:
    """
    Safely open a file.

    If multiple files have the same filename,
    return the matching options instead of choosing one.
    """

    try:

        file_path = file_path.strip()

        if not file_path:

            return (
                "TOOL_ERROR: File path cannot be empty."
            )

        target = Path(
            file_path
        ).expanduser()

        if target.exists():

            if not target.is_file():

                return (
                    f"TOOL_ERROR: Not a file: "
                    f"{target}"
                )

        else:

            matches = find_project_files(
                target.name
            )

            if not matches:

                return (
                    f"TOOL_ERROR: File not found: "
                    f"{file_path}"
                )

            if len(matches) > 1:

                result = [
                    "AMBIGUOUS_FILE: Multiple files found. "
                    "Please choose one:"
                ]

                for index, match in enumerate(
                    matches,
                    start=1
                ):

                    result.append(
                        f"{index}. {match}"
                    )

                return "\n".join(result)

            target = matches[0]

        if not target.is_file():

            return (
                f"TOOL_ERROR: Not a file: "
                f"{target}"
            )

        os.startfile(target)

        return (
            f"File opened: {target}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not open file. "
            f"Reason: {error}"
        )


# =========================
# READ FILE CONTENT
# =========================

@tool
def read_file(
    file_path: str
) -> str:
    """
    Read the text content of a file.

    If multiple files have the same filename,
    return the matching options instead of choosing one.
    """

    try:

        file_path = file_path.strip()

        if not file_path:

            return (
                "TOOL_ERROR: File path cannot be empty."
            )

        target = Path(
            file_path
        ).expanduser()

        if target.exists():

            if not target.is_file():

                return (
                    f"TOOL_ERROR: Not a file: "
                    f"{target}"
                )

        else:

            matches = find_project_files(
                target.name
            )

            if not matches:

                return (
                    f"TOOL_ERROR: File not found: "
                    f"{file_path}"
                )

            if len(matches) > 1:

                result = [
                    "AMBIGUOUS_FILE: Multiple files found. "
                    "Please choose one:"
                ]

                for index, match in enumerate(
                    matches,
                    start=1
                ):

                    result.append(
                        f"{index}. {match}"
                    )

                return "\n".join(result)

            target = matches[0]

        try:

            content = target.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            return (
                "TOOL_ERROR: This file is not "
                "a readable UTF-8 text file."
            )

        if not content.strip():

            return (
                f"File is empty: {target}"
            )

        max_chars = 12000

        if len(content) > max_chars:

            content = content[:max_chars]

            content += (
                "\n\n[File content truncated "
                "after 12000 characters.]"
            )

        return (
            f"FILE_CONTENT: {target}\n\n"
            f"{content}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not read file. "
            f"Reason: {error}"
        )


# =========================
# EDIT FILE
# =========================


@tool
def edit_file(
    file_path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False
) -> str:
    """
    Request a safe file edit.

    The file is NOT changed by this tool.
    It prepares a confirmation request first.
    """

    try:

        file_path = file_path.strip()

        if not file_path:

            return (
                "TOOL_ERROR: File path cannot be empty."
            )

        target = Path(
            file_path
        ).expanduser()

        if target.exists():

            if not target.is_file():

                return (
                    f"TOOL_ERROR: Not a file: "
                    f"{target}"
                )

        else:

            matches = find_project_files(
                target.name
            )

            if not matches:

                return (
                    f"TOOL_ERROR: File not found: "
                    f"{file_path}"
                )

            if len(matches) > 1:

                result = [
                    "AMBIGUOUS_FILE: Multiple files found. "
                    "Please choose one:"
                ]

                for index, match in enumerate(
                    matches,
                    start=1
                ):

                    result.append(
                        f"{index}. {match}"
                    )

                return "\n".join(result)

            target = matches[0]

        try:

            content = target.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            return (
                "TOOL_ERROR: This file is not "
                "a readable UTF-8 text file."
            )

        if old_text not in content:

            return (
                "TOOL_ERROR: The requested text "
                "was not found in the file."
            )

        if old_text == new_text:

            return (
                "TOOL_ERROR: Old text and new text "
                "are identical."
            )

        occurrence_count = content.count(
            old_text
        )

        return (
            "CONFIRMATION_REQUIRED_JSON: "
            + json.dumps(
                {
                    "type": "file_edit",
                    "file_path": str(target),
                    "old_text": old_text,
                    "new_text": new_text,
                    "replace_all": replace_all,
                    "occurrence_count": occurrence_count
                }
            )
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not prepare file edit. "
            f"Reason: {error}"
        )

# =========================
# DESTRUCTIVE ACTION
# =========================

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


# =========================
# ALL TOOLS
# =========================

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

    open_website,
    open_application,
    open_jarvis_folder,

    list_files,
    search_files,
    open_file,
    read_file,
    edit_file,

    delete_all_tasks,
]
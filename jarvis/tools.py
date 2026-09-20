import json
import math
import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

import requests
from langchain_core.tools import tool

from .memory import store_fact, search_facts


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

TASKS_PATH = DATA_DIR / "tasks.json"
CALENDAR_PATH = DATA_DIR / "calendar.json"


# ============================================================
# GENERAL HELPERS
# ============================================================

def ensure_data_directory():
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def load_json(path, default):
    ensure_data_directory()

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
    ensure_data_directory()

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


# ============================================================
# TIME
# ============================================================

@tool
def get_current_time():
    """
    Get the current local date and time.
    """
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# CALCULATOR
# ============================================================

@tool
def calculate(expression: str):
    """
    Calculate a mathematical expression.
    """

    allowed_names = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        result = eval(
            expression,
            {
                "__builtins__": {}
            },
            allowed_names
        )

        return str(result)

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not calculate "
            f"'{expression}'. {error}"
        )


# ============================================================
# MEMORY
# ============================================================

@tool
def remember_fact(fact: str):
    """
    Save an important long-term memory.
    """

    try:
        return store_fact(fact)

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not save memory. "
            f"{error}"
        )


@tool
def recall_memory(query: str):
    """
    Search long-term memory for relevant facts.
    """

    try:
        results = search_facts(query)

        if not results:
            return "No matching memories found."

        return "\n".join(
            f"- {fact}"
            for fact in results
        )

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not search memory. "
            f"{error}"
        )


# ============================================================
# TASKS
# ============================================================

@tool
def get_tasks():
    """
    Get all tasks.
    """

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not tasks:
        return "No tasks found."

    lines = [
        "| Title | Status | Due date |",
        "|-------|--------|----------|"
    ]

    for task in tasks:

        title = task.get(
            "title",
            "Untitled"
        )

        completed = task.get(
            "completed",
            False
        )

        status = (
            "Completed"
            if completed
            else "Pending"
        )

        due_date = task.get(
            "due_date"
        ) or "Not set"

        lines.append(
            f"| {title} | {status} | {due_date} |"
        )

    return "\n".join(lines)


@tool
def create_task(
    title: str,
    due_date: str = ""
):
    """
    Create a new task.
    """

    title = title.strip()

    if not title:
        return (
            "TOOL_ERROR: Task title cannot be empty."
        )

    tasks = load_json(
        TASKS_PATH,
        []
    )

    for task in tasks:

        if (
            task.get("title", "").strip().lower()
            == title.lower()
        ):
            return (
                f"Task already exists: "
                f"{task.get('title')}"
            )

    task = {
        "title": title,
        "due_date": due_date.strip() or None,
        "completed": False
    }

    tasks.append(task)

    save_json(
        TASKS_PATH,
        tasks
    )

    return (
        f"Task created successfully: {title}"
    )


@tool
def update_task(
    old_title: str,
    new_title: str = "",
    due_date: str = ""
):
    """
    Update an existing task.
    """

    tasks = load_json(
        TASKS_PATH,
        []
    )

    for task in tasks:

        if (
            task.get("title", "").strip().lower()
            == old_title.strip().lower()
        ):

            if new_title.strip():
                task["title"] = new_title.strip()

            if due_date.strip():
                task["due_date"] = due_date.strip()

            save_json(
                TASKS_PATH,
                tasks
            )

            return (
                f"Task updated successfully: "
                f"{task.get('title')}"
            )

    return (
        f"TOOL_ERROR: Task not found: {old_title}"
    )


@tool
def complete_task(title: str):
    """
    Mark a task as completed.
    """

    tasks = load_json(
        TASKS_PATH,
        []
    )

    for task in tasks:

        if (
            task.get("title", "").strip().lower()
            == title.strip().lower()
        ):

            task["completed"] = True

            save_json(
                TASKS_PATH,
                tasks
            )

            return (
                f"Task completed successfully: "
                f"{task.get('title')}"
            )

    return (
        f"TOOL_ERROR: Task not found: {title}"
    )


@tool
def delete_all_tasks():
    """
    Delete all tasks.
    This action requires confirmation.
    """

    tasks = load_json(
        TASKS_PATH,
        []
    )

    if not tasks:
        return "No tasks to delete."

    return json.dumps(
        {
            "type": "delete_all_tasks",
            "count": len(tasks),
            "message": (
                f"WARNING: This will permanently delete "
                f"all {len(tasks)} task(s)."
            )
        }
    )


def perform_delete_all_tasks():

    tasks = load_json(
        TASKS_PATH,
        []
    )

    count = len(tasks)

    save_json(
        TASKS_PATH,
        []
    )

    return (
        f"All tasks deleted successfully. "
        f"{count} task(s) removed."
    )


# ============================================================
# CALENDAR
# ============================================================

@tool
def get_calendar():
    """
    Get all calendar events.
    """

    events = load_json(
        CALENDAR_PATH,
        []
    )

    if not events:
        return "No calendar events found."

    lines = [
        "| Title | Date | Time | Description |",
        "|-------|------|------|-------------|"
    ]

    for event in events:

        title = event.get(
            "title",
            "Untitled"
        )

        date = event.get(
            "date",
            "Not set"
        )

        time = event.get(
            "time"
        ) or "Not set"

        description = event.get(
            "description"
        ) or "None"

        lines.append(
            f"| {title} | {date} | "
            f"{time} | {description} |"
        )

    return "\n".join(lines)


@tool
def create_calendar_event(
    title: str,
    date: str,
    time: str = "",
    description: str = ""
):
    """
    Create a calendar event.
    Prevent duplicate events when the same
    title, date, and time already exist.
    """

    title = title.strip()
    date = date.strip()
    time = time.strip()
    description = description.strip()

    if not title:
        return (
            "TOOL_ERROR: Event title cannot be empty."
        )

    if not date:
        return (
            "TOOL_ERROR: Event date cannot be empty."
        )

    events = load_json(
        CALENDAR_PATH,
        []
    )

    for existing_event in events:

        existing_title = (
            existing_event.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        existing_date = (
            existing_event.get(
                "date",
                ""
            )
            .strip()
        )

        existing_time = (
            existing_event.get(
                "time"
            ) or ""
        ).strip()

        if (
            existing_title == title.lower()
            and existing_date == date
            and existing_time == time
        ):
            return (
                "DUPLICATE_EVENT: "
                f"This calendar event already exists: "
                f"{existing_event.get('title')} "
                f"on {existing_date} "
                f"at {existing_time or 'Not set'}."
            )

    event = {
        "title": title,
        "date": date,
        "time": time or None,
        "description": description or None
    }

    events.append(event)

    save_json(
        CALENDAR_PATH,
        events
    )

    return (
        f"Calendar event created successfully: "
        f"{title} on {date}"
    )


# ============================================================
# CALENDAR UPDATE
# ============================================================

@tool
def update_calendar_event(
    title: str,
    date: str,
    time: str = "",
    new_title: str = "",
    new_date: str = "",
    new_time: str = "",
    new_description: str = ""
):
    """
    Prepare an existing calendar event for update.
    The actual update requires confirmation.
    """

    title = title.strip()
    date = date.strip()
    time = time.strip()
    new_title = new_title.strip()
    new_date = new_date.strip()
    new_time = new_time.strip()
    new_description = new_description.strip()

    if not title:
        return (
            "TOOL_ERROR: Event title cannot be empty."
        )

    if not date:
        return (
            "TOOL_ERROR: Event date cannot be empty."
        )

    events = load_json(
        CALENDAR_PATH,
        []
    )

    for index, event in enumerate(events):

        existing_title = (
            event.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        existing_date = (
            event.get(
                "date",
                ""
            )
            .strip()
        )

        existing_time = (
            event.get(
                "time"
            ) or ""
        ).strip()

        if (
            existing_title == title.lower()
            and existing_date == date
            and existing_time == time
        ):

            updated_title = (
                new_title
                if new_title
                else event.get("title", "")
            )

            updated_date = (
                new_date
                if new_date
                else event.get("date", "")
            )

            updated_time = (
                new_time
                if new_time
                else event.get("time") or ""
            )

            updated_description = (
                new_description
                if new_description
                else event.get("description") or ""
            )

            return json.dumps(
                {
                    "type": "calendar_update",
                    "index": index,
                    "old_title": event.get("title"),
                    "old_date": event.get("date"),
                    "old_time": event.get("time"),
                    "new_title": updated_title,
                    "new_date": updated_date,
                    "new_time": updated_time,
                    "new_description": updated_description
                }
            )

    return (
        "TOOL_ERROR: Calendar event not found: "
        f"{title} on {date} at "
        f"{time or 'Not set'}"
    )


def perform_update_calendar_event(
    index: int,
    new_title: str,
    new_date: str,
    new_time: str,
    new_description: str
):

    events = load_json(
        CALENDAR_PATH,
        []
    )

    if (
        index < 0
        or index >= len(events)
    ):
        return (
            "TOOL_ERROR: Calendar event no longer exists."
        )

    for existing_index, existing_event in enumerate(events):

        if existing_index == index:
            continue

        existing_title = (
            existing_event.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        existing_date = (
            existing_event.get(
                "date",
                ""
            )
            .strip()
        )

        existing_time = (
            existing_event.get(
                "time"
            ) or ""
        ).strip()

        if (
            existing_title == new_title.strip().lower()
            and existing_date == new_date.strip()
            and existing_time == new_time.strip()
        ):
            return (
                "TOOL_ERROR: Update would create "
                "a duplicate calendar event."
            )

    events[index] = {
        "title": new_title.strip(),
        "date": new_date.strip(),
        "time": new_time.strip() or None,
        "description": new_description.strip() or None
    }

    save_json(
        CALENDAR_PATH,
        events
    )

    return (
        "Calendar event updated successfully: "
        f"{new_title} on {new_date} "
        f"at {new_time or 'Not set'}."
    )


# ============================================================
# CALENDAR DELETE
# ============================================================

@tool
def delete_calendar_event(
    title: str,
    date: str,
    time: str = ""
):
    """
    Prepare an existing calendar event for deletion.
    The actual deletion requires confirmation.
    """

    title = title.strip()
    date = date.strip()
    time = time.strip()

    if not title:
        return (
            "TOOL_ERROR: Event title cannot be empty."
        )

    if not date:
        return (
            "TOOL_ERROR: Event date cannot be empty."
        )

    events = load_json(
        CALENDAR_PATH,
        []
    )

    for index, event in enumerate(events):

        existing_title = (
            event.get(
                "title",
                ""
            )
            .strip()
            .lower()
        )

        existing_date = (
            event.get(
                "date",
                ""
            )
            .strip()
        )

        existing_time = (
            event.get(
                "time"
            ) or ""
        ).strip()

        if (
            existing_title == title.lower()
            and existing_date == date
            and existing_time == time
        ):

            return json.dumps(
                {
                    "type": "calendar_delete",
                    "index": index,
                    "title": event.get("title"),
                    "date": event.get("date"),
                    "time": event.get("time"),
                    "description": event.get("description")
                }
            )

    return (
        "TOOL_ERROR: Calendar event not found: "
        f"{title} on {date} at "
        f"{time or 'Not set'}"
    )


def perform_delete_calendar_event(
    index: int
):

    events = load_json(
        CALENDAR_PATH,
        []
    )

    if (
        index < 0
        or index >= len(events)
    ):
        return (
            "TOOL_ERROR: Calendar event no longer exists."
        )

    deleted_event = events.pop(
        index
    )

    save_json(
        CALENDAR_PATH,
        events
    )

    return (
        "Calendar event deleted successfully: "
        f"{deleted_event.get('title')} "
        f"on {deleted_event.get('date')} "
        f"at {deleted_event.get('time') or 'Not set'}."
    )


# ============================================================
# WEATHER
# ============================================================

@tool
def get_weather(city: str):
    """
    Get current weather information for a city.
    """

    city = city.strip()

    if not city:
        return (
            "TOOL_ERROR: City cannot be empty."
        )

    try:

        url = (
            "https://wttr.in/"
            + requests.utils.quote(city)
            + "?format=3"
        )

        response = requests.get(
            url,
            timeout=10
        )

        if response.status_code != 200:
            return (
                f"TOOL_ERROR: Weather request failed "
                f"with status {response.status_code}."
            )

        return response.text.strip()

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not get weather. "
            f"{error}"
        )


# ============================================================
# DESKTOP / WEBSITE
# ============================================================

@tool
def open_website(url: str):
    """
    Open a website in the default browser.
    """

    url = url.strip()

    if not url:
        return (
            "TOOL_ERROR: Website URL cannot be empty."
        )

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        url = "https://" + url

    try:

        opened = webbrowser.open(url)

        if not opened:
            return (
                f"TOOL_ERROR: Could not open website: {url}"
            )

        return (
            f"Website opened successfully: {url}"
        )

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not open website. "
            f"{error}"
        )


@tool
def open_application(application: str):
    """
    Open a supported Windows application.
    """

    application = application.strip().lower()

    supported_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe"
    }

    executable = supported_apps.get(
        application
    )

    if not executable:
        return (
            "TOOL_ERROR: Unsupported application. "
            "Supported applications: "
            "Notepad, Calculator, File Explorer, CMD."
        )

    try:

        subprocess.Popen(
            executable
        )

        return (
            f"Application opened successfully: "
            f"{application}"
        )

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not open application. "
            f"{error}"
        )


@tool
def open_jarvis_folder():
    """
    Open the JARVIS project folder.
    """

    try:

        os.startfile(
            str(BASE_DIR)
        )

        return (
            f"JARVIS folder opened successfully: "
            f"{BASE_DIR}"
        )

    except Exception as error:
        return (
            f"TOOL_ERROR: Could not open JARVIS folder. "
            f"{error}"
        )


# ============================================================
# FILE ASSISTANT
# ============================================================

@tool
def list_files(
    folder: str = ""
):
    """
    List files and folders.
    """

    if folder.strip():

        folder_path = Path(
            folder.strip()
        )

    else:

        folder_path = BASE_DIR

    if not folder_path.exists():
        return (
            f"TOOL_ERROR: Folder not found: "
            f"{folder_path}"
        )

    if not folder_path.is_dir():
        return (
            f"TOOL_ERROR: Not a folder: "
            f"{folder_path}"
        )

    try:

        items = sorted(
            folder_path.iterdir(),
            key=lambda item: (
                not item.is_dir(),
                item.name.lower()
            )
        )

        if not items:
            return "Folder is empty."

        lines = []

        for item in items:

            if item.is_dir():

                lines.append(
                    f"[FOLDER] {item.name}"
                )

            else:

                lines.append(
                    f"[FILE] {item.name}"
                )

        return "\n".join(lines)

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not list files. "
            f"{error}"
        )


@tool
def search_files(
    filename: str
):
    """
    Search for files or folders by partial name
    inside the JARVIS project.
    """

    filename = filename.strip().lower()

    if not filename:
        return (
            "TOOL_ERROR: Search name cannot be empty."
        )

    excluded_folders = {
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        "chroma_db",
    }

    matches = []

    try:

        for item in BASE_DIR.rglob("*"):

            if any(
                part.lower() in excluded_folders
                for part in item.parts
            ):
                continue

            if filename in item.name.lower():

                matches.append(
                    str(item)
                )

        if not matches:

            return (
                f"No file or folder matching "
                f"'{filename}' was found."
            )

        return "\n".join(matches)

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not search files. "
            f"{error}"
        )


@tool
def search_file_contents(
    query: str
):
    """
    Search for text inside project files.
    """

    query = query.strip()

    if not query:
        return (
            "TOOL_ERROR: Search text cannot be empty."
        )

    excluded_folders = {
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        "chroma_db",
    }

    allowed_extensions = {
        ".py",
        ".txt",
        ".md",
        ".json",
        ".env",
        ".html",
        ".css",
        ".js",
    }

    matches = []

    try:

        for item in BASE_DIR.rglob("*"):

            if not item.is_file():
                continue

            if any(
                part.lower() in excluded_folders
                for part in item.parts
            ):
                continue

            if item.suffix.lower() not in allowed_extensions:
                continue

            try:

                content = item.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception:

                continue

            lines = content.splitlines()

            query_lower = query.lower()

            for line_number, line in enumerate(
                lines,
                start=1
            ):

                if query_lower in line.lower():

                    start = max(
                        0,
                        line_number - 2
                    )

                    end = min(
                        len(lines),
                        line_number + 1
                    )

                    context_lines = []

                    for index in range(
                        start,
                        end
                    ):

                        context_lines.append(
                            f"    {index + 1}: "
                            f"{lines[index]}"
                        )

                    matches.append(
                        f"FILE: {item}\n"
                        f"MATCH: Line {line_number}\n"
                        + "\n".join(context_lines)
                    )

                    break

        if not matches:

            return (
                f"No files containing "
                f"'{query}' were found."
            )

        return "\n".join(matches)

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not search "
            f"file contents. {error}"
        )


@tool
def open_file(
    file_path: str
):
    """
    Open a file using the Windows default application.
    """

    file_path = file_path.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if not path.is_file():
        return (
            f"TOOL_ERROR: Not a file: {path}"
        )

    try:

        os.startfile(
            str(path)
        )

        return (
            f"File opened successfully: {path}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not open file. "
            f"{error}"
        )


@tool
def read_file(
    file_path: str
):
    """
    Read a text file.
    """

    file_path = file_path.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if not path.is_file():
        return (
            f"TOOL_ERROR: Not a file: {path}"
        )

    try:

        content = path.read_text(
            encoding="utf-8"
        )

        if not content.strip():
            return (
                f"File is empty: {path.name}"
            )

        return (
            f"========== {path.name} ==========\n"
            f"{content}"
        )

    except UnicodeDecodeError:

        return (
            f"TOOL_ERROR: "
            f"{path.name} is not a UTF-8 text file."
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not read file. "
            f"{error}"
        )


# ============================================================
# FILE CREATE
# ============================================================

@tool
def create_file(
    file_path: str,
    content: str = ""
):
    """
    Prepare a new file for creation.
    The graph must request confirmation before creating it.
    """

    file_path = file_path.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if path.exists():
        return (
            f"TOOL_ERROR: File already exists: {path}"
        )

    return json.dumps(
        {
            "type": "file_create",
            "file_path": str(path),
            "content": content
        }
    )


def perform_create_file(
    file_path: str,
    content: str
):

    path = Path(
        file_path
    )

    if path.exists():
        return (
            f"TOOL_ERROR: File already exists: {path}"
        )

    try:

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"File created successfully: {path}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not create file. "
            f"{error}"
        )


# ============================================================
# FILE EDIT
# ============================================================

@tool
def edit_file(
    file_path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False
):
    """
    Prepare a file edit.
    The graph must request confirmation before editing.
    """

    file_path = file_path.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if not path.is_file():
        return (
            f"TOOL_ERROR: Not a file: {path}"
        )

    try:

        content = path.read_text(
            encoding="utf-8"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not read file. "
            f"{error}"
        )

    occurrence_count = content.count(
        old_text
    )

    if occurrence_count == 0:

        return (
            f"TOOL_ERROR: Text not found in "
            f"{path.name}."
        )

    return json.dumps(
        {
            "type": "file_edit",
            "file_path": str(path),
            "old_text": old_text,
            "new_text": new_text,
            "replace_all": replace_all,
            "occurrence_count": occurrence_count
        }
    )


def perform_edit_file(
    file_path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False
):

    path = Path(
        file_path
    )

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    try:

        content = path.read_text(
            encoding="utf-8"
        )

        if old_text not in content:

            return (
                "TOOL_ERROR: Text no longer exists "
                f"in {path.name}."
            )

        if replace_all:

            new_content = content.replace(
                old_text,
                new_text
            )

            count = content.count(
                old_text
            )

        else:

            new_content = content.replace(
                old_text,
                new_text,
                1
            )

            count = 1

        path.write_text(
            new_content,
            encoding="utf-8"
        )

        return (
            f"File edited successfully: "
            f"{path} ({count} occurrence(s) replaced)"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not edit file. "
            f"{error}"
        )


# ============================================================
# FILE RENAME
# ============================================================

@tool
def rename_file(
    file_path: str,
    new_name: str
):
    """
    Prepare a file rename.
    The graph must request confirmation before renaming.
    """

    file_path = file_path.strip()
    new_name = new_name.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    if not new_name:
        return (
            "TOOL_ERROR: New name cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    new_path = path.parent / new_name

    if new_path.exists():
        return (
            f"TOOL_ERROR: Destination already exists: "
            f"{new_path}"
        )

    return json.dumps(
        {
            "type": "file_rename",
            "file_path": str(path),
            "new_path": str(new_path)
        }
    )


def perform_rename_file(
    file_path: str,
    new_path: str
):

    path = Path(
        file_path
    )

    destination = Path(
        new_path
    )

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if destination.exists():
        return (
            f"TOOL_ERROR: Destination already exists: "
            f"{destination}"
        )

    try:

        path.rename(
            destination
        )

        return (
            f"File renamed successfully: "
            f"{path.name} -> {destination.name}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not rename file. "
            f"{error}"
        )


# ============================================================
# FILE MOVE
# ============================================================

@tool
def move_file(
    file_path: str,
    destination_folder: str
):
    """
    Prepare a file move.
    The graph must request confirmation before moving.
    """

    file_path = file_path.strip()
    destination_folder = destination_folder.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    if not destination_folder:
        return (
            "TOOL_ERROR: Destination folder cannot be empty."
        )

    source = Path(
        file_path
    )

    if not source.is_absolute():
        source = BASE_DIR / source

    destination = Path(
        destination_folder
    )

    if not destination.is_absolute():
        destination = BASE_DIR / destination

    if not source.exists():
        return (
            f"TOOL_ERROR: File not found: {source}"
        )

    if not source.is_file():
        return (
            f"TOOL_ERROR: Not a file: {source}"
        )

    if not destination.exists():
        return (
            f"TOOL_ERROR: Destination folder not found: "
            f"{destination}"
        )

    if not destination.is_dir():
        return (
            f"TOOL_ERROR: Destination is not a folder: "
            f"{destination}"
        )

    final_path = destination / source.name

    if final_path.exists():
        return (
            f"TOOL_ERROR: Destination file already exists: "
            f"{final_path}"
        )

    return json.dumps(
        {
            "type": "file_move",
            "file_path": str(source),
            "destination": str(final_path)
        }
    )


def perform_move_file(
    file_path: str,
    destination: str
):

    source = Path(
        file_path
    )

    destination_path = Path(
        destination
    )

    if not source.exists():
        return (
            f"TOOL_ERROR: File not found: {source}"
        )

    if destination_path.exists():
        return (
            f"TOOL_ERROR: Destination already exists: "
            f"{destination_path}"
        )

    try:

        source.rename(
            destination_path
        )

        return (
            f"File moved successfully: "
            f"{source} -> {destination_path}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not move file. "
            f"{error}"
        )


# ============================================================
# FILE DELETE
# ============================================================

@tool
def delete_file(
    file_path: str
):
    """
    Prepare a file deletion.
    The graph must request confirmation before deleting.
    """

    file_path = file_path.strip()

    if not file_path:
        return (
            "TOOL_ERROR: File path cannot be empty."
        )

    path = Path(
        file_path
    )

    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if not path.is_file():
        return (
            f"TOOL_ERROR: Not a file: {path}"
        )

    return json.dumps(
        {
            "type": "file_delete",
            "file_path": str(path)
        }
    )


def perform_delete_file(
    file_path: str
):

    path = Path(
        file_path
    )

    if not path.exists():
        return (
            f"TOOL_ERROR: File not found: {path}"
        )

    if not path.is_file():
        return (
            f"TOOL_ERROR: Not a file: {path}"
        )

    try:

        path.unlink()

        return (
            f"File deleted successfully: {path}"
        )

    except Exception as error:

        return (
            f"TOOL_ERROR: Could not delete file. "
            f"{error}"
        )


# ============================================================
# ALL TOOLS
# ============================================================

TOOLS = [
    get_current_time,
    calculate,
    remember_fact,
    recall_memory,

    get_tasks,
    create_task,
    update_task,
    complete_task,
    delete_all_tasks,

    get_calendar,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,

    get_weather,

    open_website,
    open_application,
    open_jarvis_folder,

    list_files,
    search_files,
    search_file_contents,
    open_file,
    read_file,

    create_file,
    edit_file,
    rename_file,
    move_file,
    delete_file,
]
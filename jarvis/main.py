import argparse

from .graph import (
    run_jarvis,
    confirm_pending_action,
    confirmation_message,
)
from .voice import listen, speak


def safe_speak(text):

    try:

        max_chars = 250

        if len(text) > max_chars:

            text = text[:max_chars]

            last_stop = max(
                text.rfind("."),
                text.rfind("!"),
                text.rfind("?")
            )

            if last_stop > 80:

                text = text[
                    :last_stop + 1
                ]

            else:

                text += "."

        speak(text)

    except Exception:

        print(
            "TTS temporarily unavailable. "
            "Continuing in text mode."
        )


def select_calendar_event(
    selection,
    pending_selection
):

    try:

        number = int(
            selection.strip()
        )

    except (
        ValueError,
        AttributeError
    ):

        return (
            "Please enter the event number.",
            pending_selection
        )

    events = pending_selection.get(
        "events",
        []
    )

    if number < 1 or number > len(events):

        return (
            f"Please choose a number from 1 "
            f"to {len(events)}.",
            pending_selection
        )

    selected = events[
        number - 1
    ]

    event = selected.get(
        "event",
        {}
    )

    index = selected.get(
        "index"
    )

    operation = pending_selection.get(
        "operation",
        "update"
    )

    base_action = pending_selection.get(
        "action",
        {}
    ).copy()

    # DELETE
    if operation == "delete":

        action = {
            "type": "calendar_delete",
            "index": index,
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

    # UPDATE
    else:

        action = base_action

        old_title = event.get(
            "title"
        )

        action["type"] = (
            "calendar_update"
        )

        action["index"] = index

        action["old_title"] = old_title

        action["old_date"] = event.get(
            "date"
        )

        action["old_time"] = event.get(
            "time"
        ) or ""

        action["new_title"] = old_title

        action["new_date"] = (
            pending_selection.get(
                "new_date"
            )
        )

        action["new_time"] = (
            pending_selection.get(
                "new_time"
            )
        )

        action["new_description"] = (
            event.get(
                "description"
            )
            or ""
        )

    return (
        confirmation_message(
            action
        ),
        action
    )


def process_request(
    user_input,
    pending_action
):

    if pending_action:

        action_type = pending_action.get(
            "type"
        )

        # Calendar event selection
        if action_type == "calendar_selection":

            response, new_action = (
                select_calendar_event(
                    user_input,
                    pending_action
                )
            )

            print(
                f"JARVIS: {response}"
            )

            safe_speak(
                response
            )

            return new_action

        # Normal confirmation
        answer = (
            user_input
            .lower()
            .strip()
        )

        if answer in {
            "yes",
            "y",
            "confirm",
            "confirmed",
        }:

            try:

                response = (
                    confirm_pending_action(
                        pending_action
                    )
                )

                print(
                    f"JARVIS: {response}"
                )

                safe_speak(
                    response
                )

                return None

            except Exception as error:

                print(
                    f"JARVIS Error: {error}"
                )

                safe_speak(
                    "Sorry sir, I could not "
                    "complete that action."
                )

                return pending_action

        if answer in {
            "no",
            "n",
            "cancel",
            "cancelled",
        }:

            response = (
                "Action cancelled."
            )

            print(
                f"JARVIS: {response}"
            )

            safe_speak(
                response
            )

            return None

        response = (
            "Please answer yes or no."
        )

        print(
            f"JARVIS: {response}"
        )

        safe_speak(
            response
        )

        return pending_action

    try:

        response, new_pending_action = (
            run_jarvis(
                user_input
            )
        )

        print(
            f"JARVIS: {response}"
        )

        safe_speak(
            response
        )

        return new_pending_action

    except Exception as error:

        print(
            f"JARVIS Error: {error}"
        )

        safe_speak(
            "Sorry sir, something went wrong."
        )

        return None


def text_mode():

    print(
        "JARVIS is online. "
        "Type 'exit' to stop."
    )

    pending_action = None

    while True:

        try:

            user_input = input(
                "You: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            break

        pending_action = (
            process_request(
                user_input,
                pending_action
            )
        )


def voice_mode():

    print(
        "JARVIS voice mode started."
    )

    pending_action = None

    while True:

        try:

            user_input = listen()

            if not user_input:
                continue

            print(
                f"You: {user_input}"
            )

            if (
                user_input
                .lower()
                .strip()
                == "exit"
            ):

                break

            pending_action = (
                process_request(
                    user_input,
                    pending_action
                )
            )

        except KeyboardInterrupt:

            print(
                "\nVoice mode stopped."
            )

            break

        except Exception as error:

            print(
                f"JARVIS Voice Error: {error}"
            )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=[
            "text",
            "voice"
        ],
        default="text"
    )

    args = parser.parse_args()

    if args.mode == "voice":

        voice_mode()

    else:

        text_mode()


if __name__ == "__main__":

    main()
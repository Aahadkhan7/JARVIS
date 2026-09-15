import argparse

from .graph import run_jarvis, confirm_pending_action
from .voice import listen, speak


def safe_speak(text):
    try:
        # Keep voice responses short to stay within TTS limits.
        max_chars = 250

        if len(text) > max_chars:
            text = text[:max_chars]

            # Avoid cutting in the middle of a sentence.
            last_stop = max(
                text.rfind("."),
                text.rfind("!"),
                text.rfind("?")
            )

            if last_stop > 80:
                text = text[:last_stop + 1]
            else:
                text += "."

        speak(text)

    except Exception as error:
        print(f"TTS unavailable: {error}")


def process_request(
    user_input,
    pending_action
):

    if pending_action:

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

                safe_speak(response)

                return None

            except Exception as error:

                print(
                    f"JARVIS Error: {error}"
                )

                safe_speak(
                    "Sorry sir, I could not complete that action."
                )

                return pending_action

        if answer in {
            "no",
            "n",
            "cancel",
            "cancelled",
        }:

            response = "Action cancelled."

            print(
                f"JARVIS: {response}"
            )

            safe_speak(response)

            return None

        response = (
            "Please answer yes or no."
        )

        print(
            f"JARVIS: {response}"
        )

        safe_speak(response)

        return pending_action

    try:

        response, new_pending_action = (
            run_jarvis(user_input)
        )

        print(
            f"JARVIS: {response}"
        )

        safe_speak(response)

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

    print()
    print("================================")
    print("        JARVIS ONLINE")
    print("================================")
    print("Text mode enabled.")
    print("Type 'exit' to stop.")
    print()

    pending_action = None

    while True:

        try:

            user_input = input(
                "You: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\nJARVIS: Goodbye, sir."
            )

            break

        if not user_input:
            continue

        if (
            user_input
            .lower()
            .strip()
            == "exit"
        ):

            print(
                "JARVIS: Goodbye, sir."
            )

            break

        pending_action = (
            process_request(
                user_input,
                pending_action
            )
        )


def voice_mode():

    print()
    print("================================")
    print("        JARVIS ONLINE")
    print("================================")
    print("Voice mode enabled.")
    print("Say 'exit' to stop.")
    print()

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

                response = (
                    "Goodbye, sir."
                )

                print(
                    f"JARVIS: {response}"
                )

                safe_speak(response)

                break

            pending_action = (
                process_request(
                    user_input,
                    pending_action
                )
            )

        except KeyboardInterrupt:

            print(
                "\nJARVIS: Goodbye, sir."
            )

            break

        except Exception as error:

            print(
                f"JARVIS Error: {error}"
            )


def main():

    parser = argparse.ArgumentParser(
        description="JARVIS Personal AI Assistant"
    )

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
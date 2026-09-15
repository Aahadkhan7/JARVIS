import threading

import customtkinter as ctk

from .graph import run_jarvis, confirm_pending_action
from .voice import listen, speak


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class JarvisGUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("JARVIS - Personal AI Assistant")
        self.geometry("1000x700")
        self.minsize(750, 550)

        self.pending_action = None

        self.create_ui()

    def create_ui(self):

        # Header
        self.header = ctk.CTkFrame(
            self,
            height=70,
            corner_radius=0
        )
        self.header.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            self.header,
            text="JARVIS",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        )
        self.title_label.pack(
            side="left",
            padx=25,
            pady=15
        )

        self.status_label = ctk.CTkLabel(
            self.header,
            text="● ONLINE",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(
            side="right",
            padx=25
        )

        # Chat area
        self.chat_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(size=15),
            wrap="word"
        )
        self.chat_box.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(20, 10)
        )

        self.chat_box.insert(
            "end",
            "JARVIS: Hello sir. How can I help you?\n\n"
        )

        self.chat_box.configure(
            state="disabled"
        )

        # Quick action buttons
        self.action_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.action_frame.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        self.tasks_button = ctk.CTkButton(
            self.action_frame,
            text="📋 TASKS",
            height=40,
            command=lambda: self.quick_command(
                "Show me my pending tasks"
            )
        )
        self.tasks_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5)
        )

        self.calendar_button = ctk.CTkButton(
            self.action_frame,
            text="📅 CALENDAR",
            height=40,
            command=lambda: self.quick_command(
                "Show me my calendar for today"
            )
        )
        self.calendar_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5
        )

        self.memory_button = ctk.CTkButton(
            self.action_frame,
            text="🧠 MEMORY",
            height=40,
            command=lambda: self.quick_command(
                "What do you remember about me?"
            )
        )
        self.memory_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0)
        )

        # Input frame
        self.input_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.input_frame.pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )

        self.input_box = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Type your message...",
            height=45,
            font=ctk.CTkFont(size=15)
        )
        self.input_box.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        # Voice button
        self.voice_button = ctk.CTkButton(
            self.input_frame,
            text="🎤",
            width=60,
            height=45,
            command=self.start_voice
        )
        self.voice_button.pack(
            side="left",
            padx=(0, 10)
        )

        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="SEND",
            width=100,
            height=45,
            command=self.send_message
        )
        self.send_button.pack(
            side="right"
        )

        self.input_box.bind(
            "<Return>",
            lambda event: self.send_message()
        )

    def send_message(self):

        user_input = self.input_box.get().strip()

        if not user_input:
            return

        self.input_box.delete(
            0,
            "end"
        )

        self.add_message(
            f"You: {user_input}\n"
        )

        self.process_input(
            user_input
        )

    def quick_command(self, command):

        self.add_message(
            f"You: {command}\n"
        )

        self.process_input(
            command
        )

    def process_input(self, user_input):

        self.set_busy(True)

        threading.Thread(
            target=self.process_request,
            args=(user_input,),
            daemon=True
        ).start()

    def process_request(self, user_input):

        try:

            if self.pending_action:

                answer = user_input.lower().strip()

                if answer in {
                    "yes",
                    "y",
                    "confirm",
                    "confirmed"
                }:

                    response = confirm_pending_action(
                        self.pending_action
                    )

                    self.pending_action = None

                elif answer in {
                    "no",
                    "n",
                    "cancel",
                    "cancelled"
                }:

                    response = "Action cancelled."
                    self.pending_action = None

                else:

                    response = "Please answer yes or no."

            else:

                response, new_pending_action = run_jarvis(
                    user_input
                )

                self.pending_action = (
                    new_pending_action
                )

            self.after(
                0,
                lambda: self.add_message(
                    f"JARVIS: {response}\n\n"
                )
            )

        except Exception as error:

            self.after(
                0,
                lambda: self.add_message(
                    f"JARVIS Error: {error}\n\n"
                )
            )

        finally:

            self.after(
                0,
                lambda: self.set_busy(False)
            )

    def start_voice(self):

        self.set_busy(True)

        self.add_message(
            "JARVIS: Listening...\n"
        )

        threading.Thread(
            target=self.process_voice,
            daemon=True
        ).start()

    def process_voice(self):

        try:

            user_input = listen()

            if not user_input:

                self.after(
                    0,
                    lambda: self.add_message(
                        "JARVIS: I couldn't hear you.\n\n"
                    )
                )

                return

            self.after(
                0,
                lambda: self.add_message(
                    f"You: {user_input}\n"
                )
            )

            if self.pending_action:

                answer = user_input.lower().strip()

                if answer in {
                    "yes",
                    "y",
                    "confirm",
                    "confirmed"
                }:

                    response = confirm_pending_action(
                        self.pending_action
                    )

                    self.pending_action = None

                elif answer in {
                    "no",
                    "n",
                    "cancel",
                    "cancelled"
                }:

                    response = "Action cancelled."
                    self.pending_action = None

                else:

                    response = "Please answer yes or no."

            else:

                response, new_pending_action = run_jarvis(
                    user_input
                )

                self.pending_action = (
                    new_pending_action
                )

            self.after(
                0,
                lambda: self.add_message(
                    f"JARVIS: {response}\n\n"
                )
            )

            try:
                speak(response)
            except Exception as error:
                print(
                    f"TTS unavailable: {error}"
                )

        except Exception as error:

            self.after(
                0,
                lambda: self.add_message(
                    f"JARVIS Error: {error}\n\n"
                )
            )

        finally:

            self.after(
                0,
                lambda: self.set_busy(False)
            )

    def set_busy(self, busy):

        if busy:

            self.send_button.configure(
                state="disabled",
                text="THINKING..."
            )

            self.voice_button.configure(
                state="disabled"
            )

            self.tasks_button.configure(
                state="disabled"
            )

            self.calendar_button.configure(
                state="disabled"
            )

            self.memory_button.configure(
                state="disabled"
            )

            self.status_label.configure(
                text="● THINKING..."
            )

        else:

            self.send_button.configure(
                state="normal",
                text="SEND"
            )

            self.voice_button.configure(
                state="normal"
            )

            self.tasks_button.configure(
                state="normal"
            )

            self.calendar_button.configure(
                state="normal"
            )

            self.memory_button.configure(
                state="normal"
            )

            self.status_label.configure(
                text="● ONLINE"
            )

            self.input_box.focus()

    def add_message(self, message):

        self.chat_box.configure(
            state="normal"
        )

        self.chat_box.insert(
            "end",
            message
        )

        self.chat_box.see(
            "end"
        )

        self.chat_box.configure(
            state="disabled"
        )


if __name__ == "__main__":
    app = JarvisGUI()
    app.mainloop()
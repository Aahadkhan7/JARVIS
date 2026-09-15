import threading
import tkinter as tk
from tkinter import simpledialog

import customtkinter as ctk

from .graph import run_jarvis, confirm_pending_action
from .voice import listen, speak


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class JarvisGUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("J A R V I S")
        self.geometry("1100x750")
        self.minsize(900, 650)

        self.pending_action = None
        self.is_busy = False

        self.build_ui()

    # =========================
    # BUILD UI
    # =========================

    def build_ui(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # =========================
        # HEADER
        # =========================

        self.header = ctk.CTkFrame(
            self,
            corner_radius=0
        )

        self.header.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.header.grid_columnconfigure(
            1,
            weight=1
        )

        self.logo = ctk.CTkLabel(
            self.header,
            text="J A R V I S",
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            )
        )

        self.logo.grid(
            row=0,
            column=0,
            padx=25,
            pady=15
        )

        self.status_label = ctk.CTkLabel(
            self.header,
            text="● ONLINE",
            text_color="green",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        )

        self.status_label.grid(
            row=0,
            column=2,
            padx=25
        )

        # =========================
        # MAIN FRAME
        # =========================

        self.main_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.main_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=15
        )

        self.main_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.main_frame.grid_rowconfigure(
            1,
            weight=1
        )

        # =========================
        # CORE
        # =========================

        self.core_frame = ctk.CTkFrame(
            self.main_frame,
            height=130,
            corner_radius=20
        )

        self.core_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 15)
        )

        self.core_frame.grid_propagate(False)

        self.core_label = ctk.CTkLabel(
            self.core_frame,
            text="◉\nONLINE",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        )

        self.core_label.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        # =========================
        # CHAT
        # =========================

        self.chat_box = ctk.CTkTextbox(
            self.main_frame,
            corner_radius=15,
            font=ctk.CTkFont(
                size=14
            ),
            wrap="word"
        )

        self.chat_box.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        self.chat_box.configure(
            state="disabled"
        )

        # =========================
        # QUICK ACTIONS
        # =========================

        self.quick_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.quick_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=12
        )

        for i in range(6):

            self.quick_frame.grid_columnconfigure(
                i,
                weight=1
            )

        # TASKS

        self.tasks_button = ctk.CTkButton(
            self.quick_frame,
            text="TASKS",
            command=lambda: self.quick_command(
                "Show me my pending tasks."
            )
        )

        self.tasks_button.grid(
            row=0,
            column=0,
            padx=4,
            sticky="ew"
        )

        # CALENDAR

        self.calendar_button = ctk.CTkButton(
            self.quick_frame,
            text="CALENDAR",
            command=lambda: self.quick_command(
                "Show me my calendar."
            )
        )

        self.calendar_button.grid(
            row=0,
            column=1,
            padx=4,
            sticky="ew"
        )

        # MEMORY

        self.memory_button = ctk.CTkButton(
            self.quick_frame,
            text="MEMORY",
            command=lambda: self.quick_command(
                "What do you remember about me?"
            )
        )

        self.memory_button.grid(
            row=0,
            column=2,
            padx=4,
            sticky="ew"
        )

        # FILES

        self.files_button = ctk.CTkButton(
            self.quick_frame,
            text="FILES",
            command=self.show_files
        )

        self.files_button.grid(
            row=0,
            column=3,
            padx=4,
            sticky="ew"
        )

        # SEARCH

        self.search_button = ctk.CTkButton(
            self.quick_frame,
            text="SEARCH",
            command=self.search_file
        )

        self.search_button.grid(
            row=0,
            column=4,
            padx=4,
            sticky="ew"
        )

        # OPEN

        self.open_button = ctk.CTkButton(
            self.quick_frame,
            text="OPEN",
            command=self.open_file
        )

        self.open_button.grid(
            row=0,
            column=5,
            padx=4,
            sticky="ew"
        )

        # =========================
        # INPUT
        # =========================

        self.input_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.input_frame.grid(
            row=3,
            column=0,
            sticky="ew"
        )

        self.input_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.input_box = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Talk to JARVIS...",
            height=45,
            font=ctk.CTkFont(
                size=14
            )
        )

        self.input_box.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8)
        )

        self.input_box.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        # MICROPHONE

        self.mic_button = ctk.CTkButton(
            self.input_frame,
            text="🎙",
            width=55,
            height=45,
            command=self.voice_input
        )

        self.mic_button.grid(
            row=0,
            column=1,
            padx=4
        )

        # SEND

        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="SEND",
            width=90,
            height=45,
            command=self.send_message
        )

        self.send_button.grid(
            row=0,
            column=2,
            padx=(4, 0)
        )

        # =========================
        # WELCOME
        # =========================

        self.add_message(
            "JARVIS",
            "Online, sir. How can I help?"
        )

    # =========================
    # ADD MESSAGE
    # =========================

    def add_message(
        self,
        sender,
        message
    ):

        self.chat_box.configure(
            state="normal"
        )

        self.chat_box.insert(
            "end",
            f"{sender}: {message}\n\n"
        )

        self.chat_box.see(
            "end"
        )

        self.chat_box.configure(
            state="disabled"
        )

    # =========================
    # BUSY STATUS
    # =========================

    def set_busy(
        self,
        busy
    ):

        self.is_busy = busy

        if busy:

            self.status_label.configure(
                text="● THINKING",
                text_color="orange"
            )

            self.core_label.configure(
                text="◉\nTHINKING"
            )

            buttons = [
                self.send_button,
                self.mic_button,
                self.tasks_button,
                self.calendar_button,
                self.memory_button,
                self.files_button,
                self.search_button,
                self.open_button
            ]

            for button in buttons:

                button.configure(
                    state="disabled"
                )

        else:

            self.status_label.configure(
                text="● ONLINE",
                text_color="green"
            )

            self.core_label.configure(
                text="◉\nONLINE"
            )

            buttons = [
                self.send_button,
                self.mic_button,
                self.tasks_button,
                self.calendar_button,
                self.memory_button,
                self.files_button,
                self.search_button,
                self.open_button
            ]

            for button in buttons:

                button.configure(
                    state="normal"
                )

    # =========================
    # SEND MESSAGE
    # =========================

    def send_message(self):

        if self.is_busy:

            return

        user_input = self.input_box.get().strip()

        if not user_input:

            return

        self.input_box.delete(
            0,
            "end"
        )

        self.process_text(
            user_input
        )

    # =========================
    # QUICK COMMAND
    # =========================

    def quick_command(
        self,
        command
    ):

        if self.is_busy:

            return

        self.process_text(
            command
        )

    # =========================
    # FILES
    # =========================

    def show_files(self):

        if self.is_busy:

            return

        self.process_text(
            "Show me the files in my JARVIS project folder."
        )

    # =========================
    # SEARCH FILE
    # =========================

    def search_file(self):

        if self.is_busy:

            return

        filename = simpledialog.askstring(
            "Search File",
            "Enter the file or folder name:"
        )

        if not filename:

            return

        self.process_text(
            f"Find {filename}."
        )

    # =========================
    # OPEN FILE
    # =========================

    def open_file(self):

        if self.is_busy:

            return

        filename = simpledialog.askstring(
            "Open File",
            "Enter the file name to open:"
        )

        if not filename:

            return

        self.process_text(
            f"Open {filename}."
        )

    # =========================
    # TEXT PROCESSING
    # =========================

    def process_text(
        self,
        user_input
    ):

        self.add_message(
            "YOU",
            user_input
        )

        self.set_busy(
            True
        )

        thread = threading.Thread(
            target=self.process_text_background,
            args=(user_input,),
            daemon=True
        )

        thread.start()

    # =========================
    # TEXT BACKGROUND
    # =========================

    def process_text_background(
        self,
        user_input
    ):

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

                    response = (
                        "Please answer yes or no."
                    )

            else:

                response, new_pending_action = run_jarvis(
                    user_input
                )

                self.pending_action = (
                    new_pending_action
                )

            self.after(
                0,
                lambda: self.finish_response(
                    response
                )
            )

        except Exception as error:

            self.after(
                0,
                lambda: self.finish_response(
                    f"Sorry sir, something went wrong: {error}"
                )
            )

    # =========================
    # FINISH RESPONSE
    # =========================

    def finish_response(
        self,
        response
    ):

        self.add_message(
            "JARVIS",
            response
        )

        self.set_busy(
            False
        )

    # =========================
    # VOICE INPUT
    # =========================

    def voice_input(self):

        if self.is_busy:

            return

        self.set_busy(
            True
        )

        thread = threading.Thread(
            target=self.voice_background,
            daemon=True
        )

        thread.start()

    # =========================
    # VOICE BACKGROUND
    # =========================

    def voice_background(self):

        try:

            user_input = listen()

            if not user_input:

                self.after(
                    0,
                    lambda: self.set_busy(False)
                )

                return

            self.after(
                0,
                lambda: self.add_message(
                    "YOU",
                    user_input
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

                    response = (
                        "Please answer yes or no."
                    )

            else:

                response, new_pending_action = run_jarvis(
                    user_input
                )

                self.pending_action = (
                    new_pending_action
                )

            self.after(
                0,
                lambda: self.finish_voice_response(
                    response
                )
            )

        except Exception as error:

            self.after(
                0,
                lambda: self.finish_voice_response(
                    f"Voice error: {error}"
                )
            )

    # =========================
    # FINISH VOICE RESPONSE
    # =========================

    def finish_voice_response(
        self,
        response
    ):

        self.add_message(
            "JARVIS",
            response
        )

        try:

            text_to_speak = response

            if len(text_to_speak) > 250:

                text_to_speak = (
                    text_to_speak[:250]
                )

                last_stop = max(
                    text_to_speak.rfind("."),
                    text_to_speak.rfind("!"),
                    text_to_speak.rfind("?")
                )

                if last_stop > 80:

                    text_to_speak = (
                        text_to_speak[
                            :last_stop + 1
                        ]
                    )

            speak(
                text_to_speak
            )

        except Exception:

            pass

        self.set_busy(
            False
        )


# =========================
# LAUNCH GUI
# =========================

def launch_gui():

    app = JarvisGUI()

    app.mainloop()


# =========================
# DIRECT RUN
# =========================

if __name__ == "__main__":

    launch_gui()
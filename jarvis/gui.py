import customtkinter as ctk
import threading
import math
import time


from . import graph
from .graph import run_jarvis
from .voice import listen, speak


class JarvisGUI:

    def __init__(self):

        self.app = ctk.CTk()

        self.app.title("JARVIS AI Assistant")
        self.app.geometry("800x600")
        self.app.minsize(700, 500)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.is_processing = False
        self.is_listening = False
        self.message_labels = []

        self.build_ui()
        self.animate_orb()

        self.add_message(
            "JARVIS online. How can I help you?",
            "jarvis"
        )

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        self.app.grid_columnconfigure(1, weight=1)
        self.app.grid_rowconfigure(0, weight=1)

        # =====================================================
        # SIDEBAR
        # =====================================================

        self.sidebar = ctk.CTkFrame(
            self.app,
            width=265,
            corner_radius=0
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.sidebar.grid_propagate(False)

        self.logo = ctk.CTkLabel(
            self.sidebar,
            text="J.A.R.V.I.S",
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            )
        )

        self.logo.pack(
            pady=(25, 5)
        )

        self.logo_subtitle = ctk.CTkLabel(
            self.sidebar,
            text="PERSONAL AI OPERATING ASSISTANT",
            font=ctk.CTkFont(size=10)
        )

        self.logo_subtitle.pack(
            pady=(0, 15)
        )

        # =====================================================
        # ORB
        # =====================================================

        self.orb = ctk.CTkCanvas(
            self.sidebar,
            width=180,
            height=180,
            bg="#1a1a1a",
            highlightthickness=0
        )

        self.orb.pack(
            pady=5
        )

        # =====================================================
        # STATUS
        # =====================================================

        self.status_card = ctk.CTkFrame(
            self.sidebar,
            corner_radius=12
        )

        self.status_card.pack(
            padx=18,
            pady=12,
            fill="x"
        )

        self.status_title = ctk.CTkLabel(
            self.status_card,
            text="SYSTEM STATUS",
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )

        self.status_title.pack(
            pady=(10, 2)
        )

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="● ONLINE",
            text_color="#00ff88",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        )

        self.status_label.pack(
            pady=(0, 10)
        )

        # =====================================================
        # TELEMETRY
        # =====================================================

        self.telemetry = ctk.CTkLabel(
            self.sidebar,
            text=(
                "CORE: ONLINE\n"
                "MEMORY: READY\n"
                "TOOLS: READY\n"
                "VOICE: READY"
            ),
            justify="left",
            font=ctk.CTkFont(size=11)
        )

        self.telemetry.pack(
            padx=25,
            pady=10,
            anchor="w"
        )

        # =====================================================
        # QUICK BUTTONS
        # =====================================================

        self.sidebar_button = ctk.CTkButton(
            self.sidebar,
            text="CLEAR CHAT",
            command=self.clear_chat
        )

        self.sidebar_button.pack(
            padx=18,
            pady=(10, 5),
            fill="x"
        )

        # =====================================================
        # MAIN AREA
        # =====================================================

        self.main = ctk.CTkFrame(
            self.app,
            corner_radius=0
        )

        self.main.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.main.grid_columnconfigure(
            0,
            weight=1
        )

        self.main.grid_rowconfigure(
            1,
            weight=1
        )

        # =====================================================
        # HEADER
        # =====================================================

        self.header = ctk.CTkFrame(
            self.main,
            height=65,
            corner_radius=0
        )

        self.header.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.header.grid_columnconfigure(
            0,
            weight=1
        )

        self.header_title = ctk.CTkLabel(
            self.header,
            text="JARVIS",
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        )

        self.header_title.grid(
            row=0,
            column=0,
            padx=20,
            pady=18,
            sticky="w"
        )

        self.header_status = ctk.CTkLabel(
            self.header,
            text="READY",
            text_color="#00ff88",
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )

        self.header_status.grid(
            row=0,
            column=1,
            padx=20,
            pady=18
        )

        # =====================================================
        # CHAT
        # =====================================================

        self.chat_content = ctk.CTkScrollableFrame(
            self.main,
            corner_radius=0
        )

        self.chat_content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=8,
            pady=5
        )

        self.chat_content.grid_columnconfigure(
            0,
            weight=1
        )

        # =====================================================
        # BOTTOM AREA
        # =====================================================

        self.bottom = ctk.CTkFrame(
            self.main,
            corner_radius=0
        )

        self.bottom.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=10,
            pady=10
        )

        self.bottom.grid_columnconfigure(
            0,
            weight=1
        )

        self.input_box = ctk.CTkEntry(
            self.bottom,
            placeholder_text="Ask JARVIS anything..."
        )

        self.input_box.grid(
            row=0,
            column=0,
            padx=(0, 8),
            pady=5,
            sticky="ew"
        )

        self.input_box.bind(
            "<Return>",
            self.send_message
        )

        self.send_button = ctk.CTkButton(
            self.bottom,
            text="SEND",
            width=75,
            command=self.send_message
        )

        self.send_button.grid(
            row=0,
            column=1,
            padx=4,
            pady=5
        )

        # =====================================================
        # MIC BUTTON
        # =====================================================

        self.mic_button = ctk.CTkButton(
            self.bottom,
            text="🎤 MIC",
            width=85,
            command=self.start_voice_input
        )

        self.mic_button.grid(
            row=0,
            column=2,
            padx=(4, 0),
            pady=5
        )

        # =====================================================
        # PROCESSING LABEL
        # =====================================================

        self.processing_label = ctk.CTkLabel(
            self.main,
            text="",
            font=ctk.CTkFont(size=11)
        )

        self.processing_label.grid(
            row=3,
            column=0,
            pady=(0, 5)
        )

    # =========================================================
    # MESSAGE
    # =========================================================

    def add_message(
        self,
        message,
        sender="jarvis"
    ):

        message = str(message)

        message_frame = ctk.CTkFrame(
            self.chat_content,
            corner_radius=12
        )

        message_frame.grid(
            row=len(self.message_labels),
            column=0,
            padx=8,
            pady=6,
            sticky="ew"
        )

        message_frame.grid_columnconfigure(
            0,
            weight=1
        )

        if sender == "user":

            sender_text = "YOU"
            sender_color = "#4da6ff"

        else:

            sender_text = "JARVIS"
            sender_color = "#00ff88"

        sender_label = ctk.CTkLabel(
            message_frame,
            text=sender_text,
            text_color=sender_color,
            font=ctk.CTkFont(
                size=10,
                weight="bold"
            )
        )

        sender_label.grid(
            row=0,
            column=0,
            padx=12,
            pady=(8, 2),
            sticky="w"
        )

        message_label = ctk.CTkLabel(
            message_frame,
            text=message,
            justify="left",
            anchor="w",
            wraplength=520,
            font=ctk.CTkFont(
                size=13
            )
        )

        message_label.grid(
            row=1,
            column=0,
            padx=12,
            pady=(2, 8),
            sticky="ew"
        )

        copy_button = ctk.CTkButton(
            message_frame,
            text="COPY",
            width=55,
            height=24,
            font=ctk.CTkFont(size=9),
            command=lambda m=message: self.copy_message(m)
        )

        copy_button.grid(
            row=0,
            column=1,
            rowspan=2,
            padx=8
        )

        self.message_labels.append(
            (
                message_label,
                sender
            )
        )

        self.app.after(
            50,
            self.scroll_chat_bottom
        )

    # =========================================================
    # COPY
    # =========================================================

    def copy_message(self, message):

        try:

            self.app.clipboard_clear()

            self.app.clipboard_append(
                str(message)
            )

            self.processing_label.configure(
                text="Message copied."
            )

            self.app.after(
                1200,
                lambda: self.processing_label.configure(
                    text=""
                )
            )

        except Exception:

            pass

    # =========================================================
    # SCROLL
    # =========================================================

    def scroll_chat_bottom(self):

        try:

            canvas = self.chat_content._parent_canvas

            canvas.update_idletasks()

            canvas.yview_moveto(1.0)

        except Exception:

            pass

    # =========================================================
    # CLEAR CHAT
    # =========================================================

    def clear_chat(self):

        for widget in self.chat_content.winfo_children():
            widget.destroy()

        self.message_labels.clear()

        self.add_message(
            "Chat cleared. How can I help you?",
            "jarvis"
        )

    # =========================================================
    # SEND TEXT
    # =========================================================

    def send_message(self, event=None):

        if self.is_processing:
            return

        text = self.input_box.get().strip()

        if not text:
            return

        self.input_box.delete(
            0,
            "end"
        )

        self.add_message(
            text,
            "user"
        )

        self.process_request_async(
            text,
            speak_response=False
        )

    # =========================================================
    # VOICE INPUT
    # =========================================================

    def start_voice_input(self):

        if self.is_processing:
            return

        if self.is_listening:
            return

        self.is_listening = True

        self.mic_button.configure(
            text="🎤 LISTENING...",
            state="disabled"
        )

        self.send_button.configure(
            state="disabled"
        )

        self.input_box.configure(
            state="disabled"
        )

        self.status_label.configure(
            text="● LISTENING",
            text_color="#ffaa00"
        )

        self.header_status.configure(
            text="LISTENING",
            text_color="#ffaa00"
        )

        self.processing_label.configure(
            text="Speak now..."
        )

        thread = threading.Thread(
            target=self.voice_worker,
            daemon=True
        )

        thread.start()

    # =========================================================
    # VOICE WORKER
    # =========================================================

    def voice_worker(self):

        try:

            text = listen()

            if not text:

                self.app.after(
                    0,
                    self.voice_finished
                )

                return

            self.app.after(
                0,
                lambda t=text: self.add_message(
                    t,
                    "user"
                )
            )

            self.app.after(
                0,
                lambda t=text: self.process_request_async(
                    t,
                    speak_response=True
                )
            )

        except Exception as error:

            self.app.after(
                0,
                lambda e=error: self.show_voice_error(e)
            )

    # =========================================================
    # VOICE FINISHED
    # =========================================================

    def voice_finished(self):

        self.is_listening = False

        self.mic_button.configure(
            text="🎤 MIC",
            state="normal"
        )

        self.send_button.configure(
            state="normal"
        )

        self.input_box.configure(
            state="normal"
        )

        self.status_label.configure(
            text="● ONLINE",
            text_color="#00ff88"
        )

        self.header_status.configure(
            text="READY",
            text_color="#00ff88"
        )

        self.processing_label.configure(
            text=""
        )

    # =========================================================
    # VOICE ERROR
    # =========================================================

    def show_voice_error(
        self,
        error
    ):

        print(
            f"Voice GUI error: {error}"
        )

        self.voice_finished()

        self.add_message(
            "I could not process the voice input.",
            "jarvis"
        )

    # =========================================================
    # PROCESS REQUEST ASYNC
    # =========================================================

    def process_request_async(
        self,
        text,
        speak_response=False
    ):

        if self.is_processing:
            return

        self.is_processing = True

        self.send_button.configure(
            state="disabled"
        )

        self.mic_button.configure(
            state="disabled"
        )

        self.input_box.configure(
            state="disabled"
        )

        self.status_label.configure(
            text="● PROCESSING",
            text_color="#ffaa00"
        )

        self.header_status.configure(
            text="PROCESSING",
            text_color="#ffaa00"
        )

        self.processing_label.configure(
            text="JARVIS is thinking..."
        )

        thread = threading.Thread(
            target=self.process_request,
            args=(
                text,
                speak_response
            ),
            daemon=True
        )

        thread.start()

    # =========================================================
    # PROCESS REQUEST
    # =========================================================

    def process_request(
        self,
        text,
        speak_response=False
    ):

        try:

            result = run_jarvis(text)

            if isinstance(result, tuple) and len(result) > 1:

                if result[1] is not None:

                    graph.PENDING_ACTION = result[1]

            self.app.after(
                0,
                lambda r=result,
                    sv=speak_response:
                self.show_result(
                    r,
                    sv
                )
            )

        except Exception as error:

            self.app.after(
                0,
                lambda e=error:
                self.show_error(e)
            )
    # =========================================================
    # SHOW RESULT
    # =========================================================

    def show_result(
        self,
        result,
        speak_response=False
    ):

        if isinstance(result, tuple):

            result_text = str(result[0])

        else:

            result_text = str(result)

        self.add_message(
            result_text,
            "jarvis"
        )

        if speak_response:

            speech_thread = threading.Thread(
                target=self.speak_response,
                args=(result_text,),
                daemon=True
            )

            speech_thread.start()

        else:

            self.finish_processing()

    # =========================================================
    # SPEAK RESPONSE
    # =========================================================

    def speak_response(
        self,
        text
    ):

        try:

            self.app.after(
                0,
                lambda: self.processing_label.configure(
                    text="JARVIS is speaking..."
                )
            )

            speak(text)

        except Exception as error:

            print(
                f"Speech error: {error}"
            )

        finally:

            self.app.after(
                0,
                self.finish_processing
            )

    # =========================================================
    # ERROR
    # =========================================================

    def show_error(
        self,
        error
    ):

        self.add_message(
            f"Error: {error}",
            "jarvis"
        )

        self.finish_processing()

    # =========================================================
    # FINISH PROCESSING
    # =========================================================

    def finish_processing(self):

        self.is_processing = False
        self.is_listening = False

        self.send_button.configure(
            state="normal"
        )

        self.mic_button.configure(
            text="🎤 MIC",
            state="normal"
        )

        self.input_box.configure(
            state="normal"
        )

        self.status_label.configure(
            text="● ONLINE",
            text_color="#00ff88"
        )

        self.header_status.configure(
            text="READY",
            text_color="#00ff88"
        )

        self.processing_label.configure(
            text=""
        )

        self.input_box.focus_set()

    # =========================================================
    # CONFIRMATION
    # =========================================================

    def confirm_action(
        self,
        answer
    ):

        if self.is_processing:
            return

        self.add_message(
            answer,
            "user"
        )

        self.process_request_async(
            answer,
            speak_response=False
        )

    # =========================================================
    # QUICK COMMANDS
    # =========================================================

    def quick_command(
        self,
        command
    ):

        if self.is_processing:
            return

        self.add_message(
            command,
            "user"
        )

        self.process_request_async(
            command,
            speak_response=False
        )

    # =========================================================
    # ORB ANIMATION
    # =========================================================

    def animate_orb(self):

        try:

            self.orb.delete("all")

            width = 180
            height = 180

            center_x = width / 2
            center_y = height / 2

            pulse = math.sin(
                time.time() * 3

            )    

            base_radius = 42

            radius = (
                base_radius
                + pulse * 2
            )

            self.orb.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                outline="#00aaff",
                width=3
            )

            self.orb.create_oval(
                center_x - 30,
                center_y - 30,
                center_x + 30,
                center_y + 30,
                fill="#0b2a3d",
                outline="#00ffcc",
                width=2
            )

            self.orb.create_text(
                center_x,
                center_y,
                text="J",
                fill="#00ffcc",
                font=("Arial", 28, "bold")
            )

        except Exception:

            pass

        self.app.after(
            100,
            self.animate_orb
        )

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        self.app.mainloop()


# =============================================================
# LAUNCH
# =============================================================

def launch_gui():

    app = JarvisGUI()

    app.run()


if __name__ == "__main__":

    launch_gui()
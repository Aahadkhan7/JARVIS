import sys


def main():
    try:
        from jarvis.gui import JarvisGUI

        app = JarvisGUI()
        app.app.mainloop()

    except Exception as error:
        print()
        print("JARVIS GUI ERROR")
        print()
        print(error)
        print()


if __name__ == "__main__":
    main()
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.dirname(current_dir)

sys.path.append(project_root)

from math_engine.error import ERROR_MESSAGES

OUTPUT_FILE = os.path.join(project_root, "ERRORS.md")


def main():
    print(f"Generiere Datei in: {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Error Codes Reference\n\n")
        f.write("This is a complete list of all error codes thrown by **math_engine**.\n\n")
        f.write("| Code | Message |\n")
        f.write("| :--- | :--- |\n")
        for code, message in sorted(ERROR_MESSAGES.items()):
            clean_message = message.replace("|", "\|")
            f.write(f"| **{code}** | {clean_message} |\n")

    print("✅ Fertig! ERRORS.md liegt jetzt im Hauptverzeichnis.")


if __name__ == "__main__":
    main()
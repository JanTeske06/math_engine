import argparse
import sys
import shlex
import ast
from . import (
    evaluate, error, __version__,
    set_memory, delete_memory, show_memory,
    change_setting, load_preset, load_all_settings,
    load_one_setting, reset_settings
)
try:
    import readline
except ImportError:
    pass


def print_help():
    print("\n=== Math Engine Commands ===")
    print("  help                       Show this help")
    print("  settings                   Show all current settings")
    print("  mem                        Show memory variables")
    print("  del mem <key> | all        Deletes specified memory variable")
    print("  load preset <dict>         Loads settings preset")
    print("  reset settings             Reset all settings to default")
    print("  reset mem                  Deletes all memory variables")
    print("  set setting <key> <val>    Change a setting (e.g., 'set setting decimal_places 4')")
    print("  set mem <key> <val>        Change / Create memory variables")
    print("  quit / exit                Exit the shell")
    print("============================\n")


def print_help_mem():
    print("\n=== Math Engine Memory Commands ===")
    print("  mem                        Show memory variables")
    print("  del mem <key> | all        Deletes specified memory variable")
    print("  reset mem                  Deletes all memory variables")
    print("  set mem <key> <val>        Change / Create memory variables")
    print("============================\n")


def print_help_settings():
    print("\n=== Math Engine Settings Commands ===")
    print("  settings                   Show all current settings")
    print("  load preset <dict>         Loads settings preset")
    print("  reset settings             Reset all settings to default")
    print("  set setting <key> <val>    Change a setting (e.g., 'set setting decimal_places 4')")
    print("============================\n")


# --- Command Handlers ---

def handle_set_command(args):
    if not args:
        print("Error: Missing subcommand. Use 'set setting' or 'set mem'.")
        return

    sub_command = args[0].lower()

    if sub_command == "setting":
        if len(args) < 3:
            print("Usage: set setting <key> <value>")
            return

        key = args[1]
        val_str = args[2]

        if val_str.lower() in ["true", "on"]:
            value = True
        elif val_str.lower() in ["false", "off"]:
            value = False
        elif val_str.isdigit():
            value = int(val_str)
        else:
            value = val_str

        try:
            change_setting(key, value)
            print(f"Setting updated: {key} -> {value}")
        except Exception as e:
            print(f"Error changing setting: {e}")

    elif sub_command == "mem":
        if len(args) < 3:
            print("Usage: set mem <key> <value>")
            return

        key = args[1]
        val_str = args[2]

        try:
            set_memory(key, val_str)
            print(f"Memory updated: {key} = {val_str}")
        except Exception as e:
            print(f"Error setting memory: {e}")

    else:
        print(f"Unknown set command: '{sub_command}'. Use 'setting' or 'mem'.")


def handle_del_command(args):
    if not args or args[0].lower() != "mem":
        print("Usage: del mem <key> OR del mem all")
        return

    if len(args) < 2:
        print("Missing key. Usage: del mem <key>")
        return

    target = args[1]

    if target.lower() == "all":
        try:
            delete_memory("all")
            print("Memory cleared.")
        except Exception as e:
            print(f"Error clearing memory: {e}")
    else:
        try:
            delete_memory(target)
            print(f"Deleted variable: {target}")
        except Exception as e:
            print(f"Error: {e}")


def handle_reset_command(args):
    if not args:
        print("Usage: reset settings OR reset mem")
        return

    target = args[0].lower()

    if target == "settings":
        reset_settings()
        print("All settings reset to defaults.")

    elif target == "mem":
        try:
            delete_memory("all")
            print("All memory variables deleted.")
        except Exception as e:
            print(f"Error resetting memory: {e}")
    else:
        print(f"Unknown reset target: '{target}'")


def handle_load_command(args):
    if not args or args[0].lower() != "preset":
        print("Usage: load preset <dict>")
        return

    if len(args) < 2:
        print("Missing dictionary. Usage: load preset {'decimal_places': 4}")
        return

    dict_str = " ".join(args[1:])

    try:
        preset_dict = ast.literal_eval(dict_str)
        if not isinstance(preset_dict, dict):
            print("Error: Input must be a dictionary like {'key': value}")
            return

        load_preset(preset_dict)
        print("Preset loaded successfully.")

    except Exception as e:
        print(f"Error loading preset: {e}")
        print("Make sure to use valid syntax, e.g.: load preset {'decimal_places': 4}")


# --- Main Loop ---

def run_interactive_mode():
    print(f"Math Engine {__version__} Interactive Shell")
    print("Type 'help' for commands, 'exit' to leave.")

    while True:
        try:
            user_input = input(">>> ").strip()
            if not user_input:
                continue

            parts = shlex.split(user_input)
            command = parts[0].lower()
            args = parts[1:]

            # --- Dispatcher ---

            if command in ["exit", "quit"]:
                break

            elif command == "help":
                # Sub-Help Support
                if args and args[0] == "mem":
                    print_help_mem()
                elif args and args[0] == "settings":
                    print_help_settings()
                else:
                    print_help()
                continue

            elif command == "settings":
                current = load_all_settings()
                print("\nCurrent Settings:")
                for k, v in current.items():
                    print(f"  {k}: {v}")
                print()
                continue

            elif command == "mem":
                mem_data = show_memory()
                print("\nMemory:")
                if not mem_data:
                    print("  (empty)")
                else:
                    if isinstance(mem_data, dict):
                        for k, v in mem_data.items():
                            print(f"  {k} = {v}")
                    else:
                        print(mem_data)
                print()
                continue

            elif command == "set":
                handle_set_command(args)
                continue

            elif command == "del":
                handle_del_command(args)
                continue

            elif command == "reset":
                handle_reset_command(args)
                continue

            elif command == "load":
                handle_load_command(args)
                continue

            result = process_input_and_evaluate(user_input)
            print(result)

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except error.MathError as e:
            print(f"Error {e.code}: {e.message}")
        except Exception as e:
            print(f"Error: {e}")


def process_input_and_evaluate(user_input):
    parts = []
    bracket_level = 0
    current_part = ""

    for char in user_input:
        if char == "(":
            bracket_level += 1
            current_part += char
        elif char == ")":
            bracket_level -= 1
            current_part += char
        elif char == "," and bracket_level == 0:
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
    parts.append(current_part.strip())

    expression = parts[0]
    temp_vars = {}
    for p in parts[1:]:
        if "=" in p:
            key, val_str = p.split("=", 1)
            key = key.strip()
            val_str = val_str.strip()

            try:
                if "." in val_str:
                    val = float(val_str)
                else:
                    val = int(val_str)
            except ValueError:
                val = val_str

            temp_vars[key] = val
    return evaluate(expression, **temp_vars)

# --- Entry Point ---

def main():
    parser = argparse.ArgumentParser(description="Math Engine CLI")
    parser.add_argument("expression", nargs="?", help="Expression to evaluate")
    parser.add_argument("-v", "--version", action="version", version=f"Math Engine {__version__}")

    args = parser.parse_args()

    if args.expression:
        try:
            result = evaluate(args.expression)
            print(result)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
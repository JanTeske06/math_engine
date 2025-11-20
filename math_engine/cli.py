import argparse
import sys
import shlex
import ast
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

# Deine internen Importe (beibehalten)
from . import (
    evaluate, error, __version__,
    set_memory, delete_memory, show_memory,
    change_setting, load_preset, load_all_settings,
    load_one_setting, reset_settings
)

console = Console()


def print_dict_as_table(title, data, key_label="Key", val_label="Value"):
    if not data:
        console.print(f"[yellow]No {title.lower()} found.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column(key_label, style="cyan", no_wrap=True)
    table.add_column(val_label, style="green")

    for k, v in data.items():
        table.add_row(str(k), str(v))

    console.print(table)


def print_help():
    """Zeigt Hilfe in einem Panel an"""
    help_text = """
[bold]Commands:[/bold]
  [cyan]help[/cyan]                       Show this help
  [cyan]settings[/cyan]                   Show all current settings
  [cyan]mem[/cyan]                        Show memory variables
  [cyan]del mem <key> | all[/cyan]        Delete memory variable
  [cyan]load preset <dict>[/cyan]         Load settings preset
  [cyan]reset settings | mem[/cyan]       Reset settings or memory
  [cyan]set setting <key> <val>[/cyan]    Change a setting
  [cyan]set mem <key> <val>[/cyan]        Set memory variable
  [cyan]exit / quit[/cyan]                Exit the shell
    """
    console.print(Panel(help_text.strip(), title="Math Engine Commands", expand=False))



def handle_set_command(args):
    if not args:
        console.print("[red]Error: Missing subcommand. Use 'set setting' or 'set mem'.[/red]")
        return

    sub_command = args[0].lower()

    if sub_command == "setting":
        if len(args) < 3:
            console.print("Usage: [yellow]set setting <key> <value>[/yellow]")
            return
        key, val_str = args[1], args[2]

        # Einfache Typ-Konvertierung
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
            console.print(f"[green]Setting updated:[/green] {key} -> {value}")
        except Exception as e:
            console.print(f"[red]Error changing setting:[/red] {e}")

    elif sub_command == "mem":
        if len(args) < 3:
            console.print("Usage: [yellow]set mem <key> <value>[/yellow]")
            return
        key, val_str = args[1], args[2]
        try:
            set_memory(key, val_str)
            console.print(f"[green]Memory updated:[/green] {key} = {val_str}")
        except Exception as e:
            console.print(f"[red]Error setting memory:[/red] {e}")


def handle_del_command(args):
    if not args or args[0].lower() != "mem":
        console.print("Usage: [yellow]del mem <key> OR del mem all[/yellow]")
        return
    if len(args) < 2:
        console.print("Missing key. Usage: del mem <key>")
        return

    target = args[1]
    try:
        if target.lower() == "all":
            delete_memory("all")
            console.print("[bold red]Memory cleared.[/bold red]")
        else:
            delete_memory(target)
            console.print(f"Deleted variable: [bold]{target}[/bold]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def handle_reset_command(args):
    if not args:
        console.print("Usage: reset settings OR reset mem")
        return
    target = args[0].lower()
    if target == "settings":
        reset_settings()
        console.print("[green]All settings reset to defaults.[/green]")
    elif target == "mem":
        try:
            delete_memory("all")
            console.print("[green]All memory variables deleted.[/green]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def handle_load_command(args):
    if not args or args[0].lower() != "preset":
        console.print("Usage: load preset <dict>")
        return
    try:
        dict_str = " ".join(args[1:])
        preset_dict = ast.literal_eval(dict_str)
        if not isinstance(preset_dict, dict):
            console.print("[red]Error: Input must be a dictionary[/red]")
            return
        load_preset(preset_dict)
        console.print("[green]Preset loaded successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error loading preset:[/red] {e}")


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
    return evaluate(expression, **temp_vars, is_cli=True)


def run_interactive_mode():
    console.clear()
    console.print(f"[bold blue]Math Engine {__version__} Interactive Shell[/bold blue]")
    console.print("Type [bold]help[/bold] for commands, [bold]exit[/bold] to leave.\n")

    completer = NestedCompleter.from_nested_dict({
        'help': {'mem': None, 'settings': None},
        'mem': None,
        'settings': None,
        'del': {'mem': {'all': None}},
        'reset': {'mem': None, 'settings': None},
        'load': {'preset': None},
        'set': {
            'mem': None,
            'setting': None
        },
        'exit': None,
        'quit': None
    })

    session = PromptSession(
        history=FileHistory(".math_engine_history"),
        completer=completer
    )

    style = Style.from_dict({
        'prompt': 'ansicyan bold',
    })

    while True:
        try:
            user_input = session.prompt('>>> ', style=style).strip()

            if not user_input:
                continue

            parts = shlex.split(user_input)
            command = parts[0].lower()
            args = parts[1:]

            if command in ["exit", "quit"]:
                break

            elif command == "help":
                print_help()

            elif command == "settings":
                current = load_all_settings()
                print_dict_as_table("Current Settings", current, "Setting", "Value")

            elif command == "mem":
                mem_data = show_memory()
                if isinstance(mem_data, dict):
                    print_dict_as_table("Memory", mem_data, "Variable", "Value")
                else:
                    console.print(f"[italic]{mem_data}[/italic]")

            elif command == "set":
                handle_set_command(args)
            elif command == "del":
                handle_del_command(args)
            elif command == "reset":
                handle_reset_command(args)
            elif command == "load":
                handle_load_command(args)
            elif command == "clear":
                console.clear()
                console.print(f"[bold blue]Math Engine {__version__} Interactive Shell[/bold blue]")
                console.print("Type [bold]help[/bold] for commands, [bold]exit[/bold] to leave.\n")
            else:
                # Mathe
                try:
                    result = process_input_and_evaluate(user_input)
                    if result is not None:
                        console.print(f"[bold green]= {result}[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Math Error:[/bold red] {e}")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")


def main():
    parser = argparse.ArgumentParser(description="Math Engine CLI")
    parser.add_argument("expression", nargs="?", help="Expression to evaluate")

    args = parser.parse_args()

    if args.expression:
        try:
            result = evaluate(args.expression)
            console.print(result)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
"""
Command-line interface for math_engine.

Provides two modes of operation:

1. **Direct mode** — evaluate a single expression passed as a CLI argument::

       $ math-engine "3 + 3"
       6

2. **Interactive mode (REPL)** — a persistent shell with command history,
   tab completion, variable management, and settings configuration::

       $ math-engine
       >>> 3 + 3 * 4
       = 15

Entry points (defined in ``pyproject.toml``):
    - ``math-engine`` → :func:`main`
    - ``calc``        → :func:`main`
    - ``start``       → :func:`main`
"""

import argparse
import sys
import shlex
import ast
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style


from .. import (
    evaluate, __version__,
    set_memory, delete_memory, show_memory,
    change_setting, load_preset, load_all_settings,
    reset_settings
)

console = Console()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_dict_as_table(title, data, key_label="Key", val_label="Value"):
    """Render a dictionary as a ``rich.Table`` and print it to the console.

    Args:
        title:     Table title displayed above the header row.
        data:      Dictionary to display (keys become the first column).
        key_label: Header label for the key column.
        val_label: Header label for the value column.
    """
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
    """Display the REPL help panel listing all available commands.

    Renders a ``rich.Panel`` containing a formatted summary of every
    command recognised by the interactive shell.
    """
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



# ---------------------------------------------------------------------------
# REPL command handlers
# ---------------------------------------------------------------------------

def handle_set_command(args):
    """Handle the ``set setting <key> <value>`` and ``set mem <key> <value>`` commands.

    Parses the sub-command, converts the value to the appropriate Python
    type (bool / int / str), and delegates to the corresponding API function.
    """
    if not args:
        console.print("[red]Error: Missing subcommand. Use 'set setting' or 'set mem'.[/red]")
        return

    sub_command = args[0].lower()

    if sub_command == "setting":
        if len(args) < 3:
            console.print("Usage: [yellow]set setting <key> <value>[/yellow]")
            return
        key, val_str = args[1], args[2]

        # Simple type coercion: convert the raw string value to the most
        # appropriate Python type (bool -> int -> str fallback).
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
    """Handle the ``del mem <key>`` and ``del mem all`` commands."""
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
    """Handle the ``reset settings`` and ``reset mem`` commands."""
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
    """Handle the ``load preset <dict>`` command.

    Parses the remaining arguments as a Python dictionary literal (via
    ``ast.literal_eval``) and passes it to ``load_preset()``.
    """
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


# ---------------------------------------------------------------------------
# Expression parsing and evaluation
# ---------------------------------------------------------------------------

def process_input_and_evaluate(user_input):
    """Parse REPL input for inline variable assignment and evaluate.

    Splits the input on commas (respecting parenthesis depth) to separate
    the expression from ``key=value`` variable assignments.

    Example::

        "x + 1, x=5"  ->  expression="x + 1", variables={"x": 5}

    Args:
        user_input: The raw string entered by the user in the REPL.

    Returns:
        The evaluation result (delegated to :func:`math_engine.evaluate`).
    """
    # --- Comma-aware splitting ---
    # We cannot simply call str.split(",") because the expression itself may
    # contain commas inside parenthesised function calls, e.g. "max(1,2), x=3".
    # Instead we track parenthesis nesting depth and only split on commas that
    # appear at the top level (bracket_level == 0).
    parts = []
    bracket_level = 0
    current_part = ""

    for char in user_input:
        if char == "(":
            bracket_level += 1  # entering a nested group — do not split here
            current_part += char
        elif char == ")":
            bracket_level -= 1  # leaving a nested group
            current_part += char
        elif char == "," and bracket_level == 0:
            # Top-level comma: marks the boundary between the expression
            # and an inline variable assignment (or between assignments).
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
    parts.append(current_part.strip())  # capture the final segment

    # The first segment is always the mathematical expression to evaluate.
    expression = parts[0]

    # Remaining segments are treated as inline variable definitions of the
    # form "key=value".  Each value is coerced to float, int, or kept as a
    # string, and the resulting dict is forwarded to evaluate() as kwargs.
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
# Module-level completers used as fallback / reference outside the REPL.
bool_completer = WordCompleter(['true', 'false', 'on', 'off'], ignore_case=True)

word_size_completer = WordCompleter(['8', '16', '32', '64', '0'], ignore_case=True)

# ---------------------------------------------------------------------------
# Interactive mode (REPL)
# ---------------------------------------------------------------------------

def run_interactive_mode(settings = None):
    """Start the interactive REPL shell.

    Creates a ``PromptSession`` with:
        - Command history (persisted to ``.math_engine_history``)
        - Nested tab completion for all commands and setting keys
        - Per-setting value completers (booleans, word sizes, prefixes)

    The REPL loop reads user input, dispatches commands (``help``,
    ``settings``, ``mem``, ``set``, ``del``, ``reset``, ``load``,
    ``clear``, ``exit``), or evaluates math expressions.

    Args:
        settings: Optional pre-loaded settings dictionary (unused in
                  current implementation beyond a guard check).
    """
    if settings == None:
        load_all_settings()
    console.clear()
    console.print(f"[bold blue]Math Engine {__version__} Interactive Shell[/bold blue]")
    console.print("Type [bold]help[/bold] for commands, [bold]exit[/bold] to leave.\n")

    # Load the current settings so we can derive per-key tab completers.
    current_settings = load_all_settings()

    # --- Tab completion setup ---
    # Boolean settings get true/false suggestions.
    bool_completer = WordCompleter(['true', 'false'], ignore_case=True)

    # Some settings have a fixed set of valid values; map them explicitly.
    specific_completers = {
        'word_size': WordCompleter(['8', '16', '32', '64', '0'], ignore_case=True),
        'default_output_format': WordCompleter(['decimal:', 'hex:', 'binary:', 'octal:', 'int:', 'str:', 'float:'], ignore_case=True)
    }

    # Build a completer map for "set setting <key> <value>" by inspecting
    # each setting's current value type and choosing an appropriate completer.
    setting_value_completers = {}

    for key, value in current_settings.items():
        if key in specific_completers:
            # Use the hand-crafted completer for this setting.
            setting_value_completers[key] = specific_completers[key]
        elif isinstance(value, bool):
            # Boolean settings offer true/false completions.
            setting_value_completers[key] = bool_completer
        elif isinstance(value, int) or isinstance(value, float):
            # Numeric settings suggest the current value as a starting point.
            default_numeric = [str(value)]
            setting_value_completers[key] = WordCompleter(default_numeric, ignore_case=True)
        else:
            # String or unknown type — no value completions available.
            setting_value_completers[key] = None

    # Assemble the nested completer tree that mirrors the command grammar.
    # Each dict level represents one token of the command.
    completer = NestedCompleter.from_nested_dict({
        'help': {'mem': None, 'settings': None},
        'mem': None,
        'settings': None,
        'del': {'mem': {'all': None}},
        'reset': {'mem': None, 'settings': None},
        'load': {'preset': None},
        'set': {
            'mem': None,
            'setting': setting_value_completers  # dynamically generated
        },
        'exit': None,
        'quit': None
    })

    # Create the prompt session with persistent command history and the
    # nested completer so that Tab triggers context-aware suggestions.
    session = PromptSession(
        history=FileHistory(".math_engine_history"),
        completer=completer
    )

    # Custom prompt style: cyan bold ">>>" prefix.
    style = Style.from_dict({
        'prompt': 'ansicyan bold',
    })

    # --- Main REPL loop ---
    # Each iteration reads one line of input, tokenises it with shlex, and
    # dispatches on the first token (the command).  Unrecognised commands
    # fall through to the math evaluator.
    while True:
        try:
            user_input = session.prompt('>>> ', style=style).strip()

            if not user_input:
                continue

            # Tokenise the input respecting shell-style quoting so that
            # values like "set mem greeting 'hello world'" work correctly.
            parts = shlex.split(user_input)
            command = parts[0].lower()
            args = parts[1:]

            # -- Command dispatch --
            if command in ["exit", "quit"]:
                # Terminate the REPL loop.
                break

            elif command == "help":
                # Display the help panel with all available commands.
                print_help()

            elif command == "settings":
                # Reload and display the full settings table.
                current = load_all_settings()
                print_dict_as_table("Current Settings", current, "Setting", "Value")

            elif command == "mem":
                # Show all stored memory variables (or a message if empty).
                mem_data = show_memory()
                if isinstance(mem_data, dict):
                    print_dict_as_table("Memory", mem_data, "Variable", "Value")
                else:
                    console.print(f"[italic]{mem_data}[/italic]")

            elif command == "set":
                # Delegate to handler for "set setting ..." / "set mem ...".
                handle_set_command(args)
            elif command == "del":
                # Delegate to handler for "del mem <key>" / "del mem all".
                handle_del_command(args)
            elif command == "reset":
                # Delegate to handler for "reset settings" / "reset mem".
                handle_reset_command(args)
            elif command == "load":
                # Delegate to handler for "load preset <dict>".
                handle_load_command(args)
            elif command == "clear":
                # Clear the terminal and reprint the shell banner.
                console.clear()
                console.print(f"[bold blue]Math Engine {__version__} Interactive Shell[/bold blue]")
                console.print("Type [bold]help[/bold] for commands, [bold]exit[/bold] to leave.\n")
            else:
                # No built-in command matched — treat the entire input as a
                # mathematical expression (possibly with inline variables).
                try:
                    result = process_input_and_evaluate(user_input)
                    if result is not None:
                        console.print(f"[bold green]= {result}[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Math Error:[/bold red] {e}")

        except (KeyboardInterrupt, EOFError):
            # Ctrl-C or Ctrl-D: exit gracefully.
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(settings = None):
    """Main CLI entry point (invoked by ``math-engine``, ``calc``, ``start``).

    Uses ``argparse`` to accept an optional positional expression argument:

    - If an expression is provided: evaluates it, prints the result, and exits.
    - If no expression: launches :func:`run_interactive_mode`.

    Args:
        settings: Optional pre-loaded settings dictionary.
    """
    if settings == None:
        load_all_settings()
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
        run_interactive_mode(settings)


# if __name__ == "__main__":
#     settings = load_all_settings()
#     new_dict = {key: None for key in settings}
#     main(new_dict)
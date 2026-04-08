"""
CLI sub-package for math_engine.

Re-exports the main entry points from :mod:`math_engine.cli.cli` so that
``math_engine.cli.main`` resolves correctly for the console_scripts entry
point defined in ``pyproject.toml``.
"""

# Public API re-exports: these names are importable directly from
# ``math_engine.cli`` and are used by the console_scripts entry points.
from .cli import (
    evaluate,
    run_interactive_mode,
    change_setting,
    delete_memory,
    load_preset,
    reset_settings,
    show_memory,
    main,
    process_input_and_evaluate
)

# PromptSession is an optional dependency (requires prompt_toolkit).
# Import it when available so that downstream code can detect REPL support;
# silently ignore ImportError for environments that lack the package.
try:
    from .cli import PromptSession
except ImportError:
    pass

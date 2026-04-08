"""
Example plugin template for math_engine.

This file demonstrates how to create a custom plugin by subclassing
:class:`~math_engine.utility.plugin_manager.BasePlugin`.

**Status: Work in progress** — the ``execute()`` method is not yet
implemented, and the plugin system is still under development.

To create your own plugin:
    1. Create a ``.py`` file in the ``plugins/`` directory.
    2. Define a class that inherits from ``BasePlugin``.
    3. Implement ``register_function()`` — return a blueprint dict.
    4. Implement ``execute(problem)`` — perform the computation.
"""

import decimal


class Hallo(BasePlugin):
    """Example plugin that would register a natural logarithm function ``ln()``.

    Attributes:
        name: Human-readable plugin name.
    """
    name = "Hallo"
    def __init__(self):
        pass

    def register_function(self):
        """Return the function blueprint for ``ln()``.

        Returns:
            dict: Blueprint describing the function name, parameter count,
                  expected type, argument separator, and implementing class.
        """
        return {
                "function"              : "ln",            # required to be in brackets, e.g. : ln(1) and must be string
                "number_of_parameters"  : 2,                # Only whole numbers 0 <= allowed
                "type"                  : decimal.Decimal,              # String, Decimal, Bool, int or float
                "divided_by"            : ",",              # Default is ',', but can be adjusted, except '(' or ')'
                "implementation_class"  : Hallo             # Name of ur Class
                                                        }
    def execute(self, problem):
        """Execute the ``ln()`` function (not yet implemented)."""
        pass
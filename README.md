
# Math Engine v0.6.0

[![PyPI Version](https://img.shields.io/pypi/v/math-engine.svg)](https://pypi.org/project/math-engine/)
[![License: MIT](https://img.shields.io/pypi/l/math-engine.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/math-engine.svg)](https://pypi.org/project/math-engine/)

A fast, safe, configurable expression parser and calculator for Python.

**math_engine** is a powerful expression evaluation library designed for developers who need a **safe**, **configurable**, and **extendable** alternative to Python’s built-in `eval()` or other ad-hoc parsers.  
It provides a complete pipeline:

* Tokenizer
* AST (Abstract Syntax Tree) parser
* Evaluator (numeric + equation solver)
* Formatter and type-safe output system
* Support for decimal, integer, binary, octal, hexadecimal
* Custom variables
* Scientific functions
* Strict error codes for reliable debugging and automated testing



This library is ideal for:

* Developers building calculators, interpreters, scripting engines
* Students learning compilers, math parsing, and ASTs
* Security-sensitive applications where `eval()` is not acceptable
* Anyone who needs equation solving, custom formats, and strict errors

---

# Features

### Core Features

* Full AST-based expression parsing
* Safe evaluation (no execution of Python code)
* Decimal, Integer, Float, Boolean, Binary, Octal, Hexadecimal
* Custom variables
* Linear equation solving (`x + 3 = 7`)
* Scientific functions: `sin`, `cos`, `tan`, `log`, `sqrt`, `π`, `e^`
* Automatic format correction (`correct_output_format`)
* Strong error handling with unique codes
* Settings system with presets
* Optional strict modes:
  * `only_hex`
  * `only_binary`
  * `only_octal`

### Non-Decimal Support

* Read binary `0b1101`
* Read octal `0o755`
* Read hexadecimal `0xFF`
* Convert results into binary/hex/octal format
* Enforce only-hex/only-binary/only-octal mode
* Prefix parsing (`hex:`, `bin:`, `int:`, `str:` ...)

---

# Installation

```bash
pip install math-engine
````

-----

# Command Line Interface (CLI)

Math Engine works directly from your terminal\! After installing via pip, you can use the command `math-engine` (or the short alias `calc`).

### 1\. Interactive Mode (REPL)

Start the shell to calculate, manage variables, and change settings dynamically.

```bash
$ math-engine

Math Engine 0.4.0 Interactive Shell
Type 'help' for commands, 'exit' to leave.
----------------------------------------
Examples:
  >>> 3 + 3 * 4 
  15
  
  >>> hex: 255
  0xff
  
  >>> x + 5, x=10    (Inline Variables)
  15
  
  >>> set setting word_size 8
  Setting updated: word_size -> 8
```

### 2\. Direct Calculation

You can also pass expressions directly (great for scripting):

```bash
$ math-engine "3 + 3"
6

$ math-engine "hex: 255"
0xff
```

-----

# Quick Start

## Basic Evaluation

```python
import math_engine

math_engine.evaluate("2 + 2")
# Decimal('4')
```

## Different Output Formats

```python
math_engine.evaluate("hex: 255")
# '0xff'

math_engine.evaluate("binary: 13")
# '0b1101'

math_engine.evaluate("octal: 64")
# '0o100'
```

## Automatic Format Correction

```python
import math_engine

settings = math_engine.load_all_settings()
settings["correct_output_format"] = True
math_engine.load_preset(settings)

math_engine.evaluate("bool: 3+3=6")
# True
```

## Reset all Settings to Default

```python
import math_engine

math_engine.reset_settings()
```

If a requested output type does not match the actual result, `correct_output_format=True` allows math\_engine to fall back to a compatible type instead of raising an error.

-----

# Prefix System (Casting Syntax)

math\_engine supports a powerful prefix-based casting system:

| Prefix   | Meaning     | Example                            |
| -------- | ----------- | ---------------------------------- |
| `dec:`   | Decimal     | `dec: 3/2` → `1.50`                |
| `int:`   | Integer     | `int: 10/3` → error if non-integer |
| `float:` | Float       | `float: 1/3`                       |
| `bool:`  | Boolean     | `bool: 3 = 3`                      |
| `hex:`   | Hexadecimal | `hex: 15`                          |
| `bin:`   | Binary      | `bin: 5`                           |
| `oct:`   | Octal       | `oct: 64`                          |
| `str:`   | String      | `str: 3+3` → `"6"`                 |

Example:

```python
math_engine.evaluate("hex: 3 + 3")
# '0x6'
```

-----

# Variables

```python
vars = {
    "A": 10,
    "B": 5,
}

math_engine.evaluate("A + B", variables=vars)
# Decimal('15')
```

Alternatively, you can pass variables as keyword arguments:

```python
math_engine.evaluate("A + B", A=10, B=5)
# Decimal('15')
```

Variables are mapped internally to a safe internal representation and are designed to be simple and predictable.

-----

# Scientific Functions

```python
math_engine.evaluate("sin(30)")
math_engine.evaluate("cos(90)")
math_engine.evaluate("log(100,10)")
math_engine.evaluate("√(16)")
math_engine.evaluate("pi * 2")
```

All functions are processed by the internal `ScientificEngine`, honoring your settings (for example, `use_degrees`).

-----

# Linear Equation Solver

```python
math_engine.evaluate("x + 3 = 10")
# Decimal('7')
```

Invalid or nonlinear equations produce errors with codes like:

  * 3005 – Non-linear equation
  * 3002 – Multiple variables
  * 3022 – One side empty

-----

# Non-Decimal Numbers (Binary, Octal, Hex)

```python
math_engine.evaluate("0xFF + 3")
# Decimal('258')

math_engine.evaluate("0b1010 * 3")
# Decimal('30')
```

Non-decimal parsing respects the setting `allow_non_decimal`. If it is set to `False`, using `0b`, `0o`, or `0x` will raise a conversion error.

-----

# Bitwise Operations & Developer Mode (v0.5.0)

Math Engine can act as a **programmer's calculator**. It supports standard operator precedence and bitwise logic.

### New Operators

| Operator | Description | Example  | Result |
| :------- | :---------- | :------- | :----- |
| `&`      | Bitwise AND | `3 & 1`  | `1`    |
| `\|`     | Bitwise OR  | `1 \| 2` | `3`    |
| `^`      | Bitwise XOR | `3 ^ 1`  | `2`    |
| `<<`     | Left Shift  | `1 << 2` | `4`    |
| `>>`     | Right Shift | `8 >> 2` | `2`    |
| `**`     | Power       | `2 ** 3` | `8`    |

> Note: Since `^` is used for **XOR**, use `**` for exponentiation (power).

### Word Size & Overflow Simulation

You can simulate hardware constraints (like C++ `int8`, `uint16`, etc.) by setting a `word_size`.

  * **`word_size: 0` (Default):** Python mode (arbitrary precision, no overflow).
  * **`word_size: 8/16/32/64`:** Enforces bit limits. Numbers will wrap around (overflow) accordingly.

### Signed vs. Unsigned Mode

When `word_size > 0`, you can control how values are interpreted via `signed_mode`:

  * **`True` (Default):** Use **Two's Complement** for negative values.
  * **`False`:** Treat all values as unsigned.

**Example: 8-bit Simulation**

```python
import math_engine

settings = math_engine.load_all_settings()
settings["word_size"] = 8
settings["signed_mode"] = True
math_engine.load_preset(settings)

math_engine.evaluate("127 + 1")
# In 8-bit signed arithmetic this overflows to -128
# Decimal('-128')
```

Hex output respects the current word size and signedness:

```python
math_engine.evaluate("hex: -1")
# Hex representation consistent with word_size / signed_mode configuration
```

### Force-only-hex Mode

```python
settings = math_engine.load_all_settings()
settings["only_hex"] = True
math_engine.load_preset(settings)

math_engine.evaluate("FF + 3")
# Decimal('258')
```
Input validation ensures safety and prevents mixing incompatible formats in strict modes.

---
## Bitwise & Low-Level Operations

Math Engine now includes a rich collection of low-level bit manipulation functions commonly used in systems programming, embedded development, cryptography, and hardware-oriented tools.

**Bitwise functions:**
- `bitand(x, y)` — bitwise AND  
- `bitor(x, y)` — bitwise OR  
- `bitxor(x, y)` — bitwise XOR  
- `bitnot(x)` — bitwise NOT  

**Bit manipulation utilities:**
- `setbit(x, n)` — sets bit *n*  
- `clrbit(x, n)` — clears bit *n*  
- `togbit(x, n)` — toggles bit *n*  
- `testbit(x, n)` — returns 1 if bit *n* is set, else 0  

**Shift operations:**
- `shl(x, n)` — logical left shift  
- `shr(x, n)` — logical right shift  

All bitwise functions:
- respect `word_size` and `signed_mode`  
- support overflow/wrap-around behavior  
- fully support binary, hex, decimal, and octal inputs  
- participate in the AST just like standard operators  

This makes Math Engine behave like a full-featured programmer’s calculator with CPU-like precision control.

-----

# Settings System

You can inspect and modify settings programmatically.

### Load Current Settings

```python
import math_engine

settings = math_engine.load_all_settings()
print(settings)
```

### Apply a Full Preset

This is a plain Python `dict` (not JSON):

```python
preset = {
    "decimal_places": 2,
    "use_degrees": False,
    "allow_augmented_assignment": True,
    "fractions": False,
    "allow_non_decimal": True,
    "debug": False,
    "correct_output_format": True,
    "default_output_format": "decimal:",
    "only_hex": False,
    "only_binary": False,
    "only_octal": False,
    # New in 0.3.0
    "word_size": 0,        # 0 = unlimited, or 8, 16, 32, 64
    "signed_mode": True,   # True = Two's Complement, False = Unsigned
    # New in 0.6.0
    "readable_error": False
}

math_engine.load_preset(preset)
```

### Change a Single Setting

```python
math_engine.change_setting("decimal_places", 10)
```

You can also read a single setting:

```python
decimal_places = math_engine.load_one_setting("decimal_places")
```

-----


# Error Handling (v0.6.0: Visual & Precise)

Math Engine 0.6.0 introduces a dual-mode error handling system designed for both interactive use and strict library integration.

## 1\. Visual Feedback (Default Behavior)

By default (`readable_error = True`), the engine catches syntax errors internally and prints a visual diagnostic to the console. This is perfect for CLI tools or quick debugging, as it points exactly to the issue without crashing the program.

```python
import math_engine

# readable_error is True by default
math_engine.evaluate("sin(5") 
```

**Console Output:**

```text
Errormessage: Unbalanced parenthesis.
Code: 2010
Equation: sin(5
             ^ HERE IS THE PROBLEM (Position: 5)
```

## 2\. Programmatic Handling (Exceptions)

If you are building an application or running unit tests, you likely want to catch exceptions instead of printing to stdout. You can disable `readable_error` to raise standard `MathError` exceptions.

The exception object carries **precise start and end indices**:

  * `e.position_start` (int): Index where the error begins.
  * `e.position_end` (int): Index where the error ends.

<!-- end list -->

```python
import math_engine
from math_engine import error as E

# Disable visual printing to catch exceptions
math_engine.change_setting("readable_error", False)

try:
    math_engine.evaluate("10.5 + 4.2.1")
except E.SyntaxError as e:
    print(f"Error Code: {e.code}")
    print(f"Location: {e.position_start} to {e.position_end}")
    
    # You can use these indices to highlight the error in your own UI
    bad_part = e.equation[e.position_start : e.position_end + 1]
    print(f"Invalid segment: '{bad_part}'")

```

## Testing and Reliability

To write unit tests with `pytest`, ensure you set `readable_error` to `False` so that exceptions are raised and can be asserted.

```python
import pytest
import math_engine
from math_engine import error as E

def test_division_by_zero():
    # Ensure exceptions are raised
    math_engine.change_setting("readable_error", False)
    
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("10 / 0")
        
    # Assert the error is Division by Zero (3003)
    assert exc.value.code == "3003"
    # Assert the error points exactly to the zero/operator
    assert exc.value.position_start == 3 
```
---
# Performance

  * No use of Python `eval()`
  * Predictable performance through AST evaluation
  * Optimized tokenization
  * Fast conversion of non-decimal numbers

Future updates focus on:

  * Expression caching
  * Compiler-like optimizations
  * Faster scientific evaluation

-----

# Use Cases

### Calculator Applications

Build full scientific or programmer calculators, both GUI and command line.

### Education

Great for learning about lexers, parsers, ASTs, and expression evaluation.

### Embedded Scripting

Safe math evaluation inside larger apps.

### Security-Sensitive Input

Rejects arbitrary Python code and ensures controlled evaluation.

### Data Processing

Conversion between hex/bin/decimal is easy and reliable.

-----

# Roadmap (Future Versions)

  * Non-decimal output formatting upgrades
  * Strict type-matching modes
  * Function overloading
  * Memory/register system
  * Speed optimization via caching
  * User-defined functions
  * Expression pre-compilation
  * Better debugging output

-----

# Changelog

See [CHANGELOG.md](https://github.com/JanTeske06/math_engine/blob/master/CHANGELOG.md) for details.

-----

# License
[MIT License](https://github.com/JanTeske06/math_engine/blob/master/LICENSE)

-----

# Contributing

Contributions are welcome.
Feel free to submit issues or PRs on GitHub:

[https://github.com/JanTeske06/math\_engine](https://github.com/JanTeske06/math_engine)

---


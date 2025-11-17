
# Math Engine 0.3.2

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

**Version _0.3.2_** adds extensive non-decimal number support (hex, binary, octal), prefix-based type casting, improved settings management, expanded error reporting, and an optional programmer mode with bitwise operations and word-size simulation.

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

### Non-Decimal Support (≥ 0.2.1)

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

---

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

reset_settings()
```


If a requested output type does not match the actual result, `correct_output_format=True` allows math_engine to fall back to a compatible type instead of raising an error.

---

# Prefix System (Casting Syntax)

math_engine supports a powerful prefix-based casting system:

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

---

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

---

# Scientific Functions

```python
math_engine.evaluate("sin(30)")
math_engine.evaluate("cos(90)")
math_engine.evaluate("log(100,10)")
math_engine.evaluate("√(16)")
math_engine.evaluate("pi * 2")
```

All functions are processed by the internal `ScientificEngine`, honoring your settings (for example, `use_degrees`).

---

# Linear Equation Solver

```python
math_engine.evaluate("x + 3 = 10")
# Decimal('7')
```

Invalid or nonlinear equations produce errors with codes like:

* 3005 – Non-linear equation
* 3002 – Multiple variables
* 3022 – One side empty

---

# Non-Decimal Numbers (Binary, Octal, Hex)

```python
math_engine.evaluate("0xFF + 3")
# Decimal('258')

math_engine.evaluate("0b1010 * 3")
# Decimal('30')
```

Non-decimal parsing respects the setting `allow_non_decimal`. If it is set to `False`, using `0b`, `0o`, or `0x` will raise a conversion error.

---

# Bitwise Operations & Developer Mode (v0.3.x)

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

---

# Error Handling

Every error is a custom exception with:

* Human-readable message
* Machine-readable error code
* Position (if applicable)
* The original expression

Example:

```python
import math_engine
from math_engine import error as E

try:
    math_engine.evaluate("1/0")
except E.CalculationError as e:
    print(e.code)      # 3003
    print(e.message)   # "Division by zero"
    print(e.equation)  # "1/0"
```

### Example Error Codes

| Code | Meaning                     |
| ---- | --------------------------- |
| 3003 | Division by zero            |
| 3034 | Empty input                 |
| 3036 | Multiple = signs            |
| 3032 | Multiple-character variable |
| 8000 | Conversion to int failed    |
| 8006 | Output conversion error     |

For a complete list of all error codes and their meanings, please see the **[Error Codes Reference](https://github.com/JanTeske06/math_engine/blob/master/ERRORS.md)**.

---
---

# Testing and Reliability

math_engine is designed with testing in mind:

* Full error-code consistency
* Strict syntax rules
* Unit-test friendly behavior
* No reliance on Python’s runtime execution

Example with `pytest`:

```python
import pytest
import math_engine
from math_engine import error as E

def test_division_by_zero_error_code():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("1/0")
    assert exc.value.code == "3003"
```

You can also test more advanced behavior (non-decimal, strict modes, bitwise operations, etc.) in the same way.

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

---

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

---

# Roadmap (Future Versions)

* Non-decimal output formatting upgrades
* Strict type-matching modes
* Function overloading
* Memory/register system
* Speed optimization via caching
* User-defined functions
* Expression pre-compilation
* Better debugging output

---

# License

MIT License

---

# Contributing

Contributions are welcome.
Feel free to submit issues or PRs on GitHub:

```text
https://github.com/JanTeske06/math_engine
```

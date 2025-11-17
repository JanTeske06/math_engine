# Math Engine 0.3.0

[![PyPI Version](https://img.shields.io/pypi/v/math-engine.svg)](https://pypi.org/project/math-engine/)
[![License: MIT](https://img.shields.io/pypi/l/math-engine.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/math-engine.svg)](https://pypi.org/project/math-engine/)

A fast, safe, configurable expression parser and calculator for Python

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

**Version 0.2.1** adds extensive non-decimal number support (hex, binary, octal), prefix-based type casting, improved settings management, and expanded error reporting.

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

### Non-Decimal Support (0.2.1)

* Read binary `0b1101`
* Read octal `0o755`
* Read hexadecimal `0xFF`
* Convert results into binary/hex/octal format
* Enforce only-hex/only-binary/only-octal mode
* Prefix parsing (`hex:`, `bin:`, `int:`, `str:` ...)

---

# Installation

```
pip install math-engine
```

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
math_engine.load_preset({"correct_output_format": True})
math_engine.evaluate("boolean: 3+3=6")
# True
```

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
    "B": 5
}

math_engine.evaluate("A + B", custom_variables=vars)
# Decimal('15')
```

Variables must be single characters (to enforce safety and keep parsing simple).

---

# Scientific Functions

```python
math_engine.evaluate("sin(30)")
math_engine.evaluate("cos(90)")
math_engine.evaluate("log(100,10)")
math_engine.evaluate("√(16)")
math_engine.evaluate("pi * 2")
```

All functions are processed by the internal ScientificEngine.

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

# Bitwise Operations & Developer Mode (v0.3.0)

Math Engine now acts as a fully functional **Programmer's Calculator**. It supports standard Python operator precedence and bitwise logic.

### New Operators

| Operator | Description | Example | Result |
| :--- | :--- | :--- | :--- |
| `&` | Bitwise AND | `3 & 1` | `1` |
| `\|` | Bitwise OR | `1 \| 2` | `3` |
| `^` | Bitwise XOR | `3 ^ 1` | `2` |
| `<<` | Left Shift | `1 << 2` | `4` |
| `>>` | Right Shift | `8 >> 2` | `2` |
| `**` | Power | `2 ** 3` | `8` |

> **Note:** Since `^` is now used for **XOR**, use `**` for exponentiation (power).

### Word Size & Overflow Simulation

You can simulate hardware constraints (like C++ `int8`, `uint16`, etc.) by setting a `word_size`.

* **`word_size: 0` (Default):** Python mode (Arbitrary precision, no overflow).
* **`word_size: 8/16/32/64`:** Enforces bit limits. Numbers will wrap around (overflow).

### Signed vs. Unsigned Mode

When `word_size > 0`, you can toggle how binary data is interpreted using `signed_mode`.

* **`True` (Default):** Uses **Two's Complement**. The highest bit indicates a negative number.
* **`False`:** Strictly positive numbers (Unsigned).

**Example: 8-Bit Simulation**

```python
# Setup: 8-Bit Signed Mode
settings = {
    "word_size": 8,
    "signed_mode": True
}
math_engine.load_preset(settings)

# Calculation: 127 + 1
# Mathematically 128, but in 8-bit signed this overflows to -128.
math_engine.evaluate("127 + 1")
# Decimal('-128')

# Calculation: -1 in Hex
# In 8-bit two's complement, -1 is represented as FF.
math_engine.evaluate("hex: -1")
# '-0x1' (Value is masked internally to 255)
```
### Force-only-hex mode

```python
settings = math_engine.load_all_settings()
settings["only_hex"] = True
math_engine.load_preset(settings)

math_engine.evaluate("FF + 3")
# Decimal('258')
```

Input validation ensures safety.

---

# Settings System

You may load presets:

```python
preset = {
    "decimal_places": 2,
    "use_degrees": false,
    "allow_augmented_assignment": true,
    "fractions": false,
    "allow_non_decimal": true,
    "debug": false,
    "correct_output_format": true,
    "default_output_format": "decimal:",
    "only_hex": false,
    "only_binary": false,
    "only_octal": false,
    # New in v0.3.0
    "word_size": 0,       # 0 = Unlimited, or 8, 16, 32, 64
    "signed_mode": true,  # True = Two's Complement, False = Unsigned
}

math_engine.load_preset(preset)
```

Or modify single settings:

```python
math_engine.save_setting("decimal_places", 10)
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
try:
    math_engine.evaluate("1/0")
except math_engine.error.CalculationError as e:
    print(e.code)  # 3003
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

---

# Testing and Reliability

math_engine is designed with testing in mind:

* Full error-code consistency
* Strict syntax rules
* Unit-test friendly behavior
* No reliance on Python’s runtime execution

You can easily test error codes:

```python
import pytest
from math_engine import error as E

def test_div_zero():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("1/0")
    assert exc.value.code == "3003"
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

---

# Use Cases

### Calculator Applications

Build full scientific calculators, both GUI and command line.

### Education

Great for learning about lexers, parsers, ASTs, and expression evaluation.

### Embedded Scripting

Safe math evaluation inside larger apps.

### Security-sensitive Input

Rejects arbitrary Python code and ensures controlled evaluation.

### Data Processing

Conversion between hex/bin/decimal is easy and reliable.

---

# Roadmap (Future Versions)

* Non-decimal output formatting upgrades
* Strict type-matching modes
* Function overloading
* Bitwise operators (`&`, `|`, `^`, `<<`, `>>`)
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

```
https://github.com/JanTeske06/math_engine
```

---


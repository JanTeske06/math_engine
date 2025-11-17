# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
---

## [0.5.0] - 2025-11-17 

### Added
- **Full Bit Manipulation Function Suite:**  
  Math Engine now includes a complete set of bit utilities often found in low-level programming:
  - `setbit(x, n)` – set bit *n*
  - `clrbit(x, n)` – clear bit *n*
  - `togbit(x, n)` – toggle bit *n*
  - `testbit(x, n)` – check whether bit *n* is set
  - `bitand(x, y)` – bitwise AND
  - `bitor(x, y)` – bitwise OR
  - `bitxor(x, y)` – bitwise XOR
  - `bitnot(x)` – bitwise NOT
  - `shl(x, n)` – logical left shift
  - `shr(x, n)` – logical right shift

- **Mixed-Base Support for Bit Operations:**  
  Bit functions now accept operands in any format (binary, hex, octal, decimal), and all inputs are normalized safely before evaluation.


### Improved
- **Parser Stability:**  
  More robust detection of invalid characters inside non-decimal literals, producing clearer and more accurate `8004` conversion errors.
- **Test Coverage:**  
  Extensive new test suite for every bit function, mixed bases, shift operations, and underscore handling.

### Fixed
- Corrected `shr()` behavior for right shifts on binary literals.
- Resolved tokenizer edge cases involving `only_hex`/`only_binary` strict modes interacting with function calls.

---
## [0.4.0] - 2025-11-17

### Added
- **Command Line Interface (CLI):** Introduced `math-engine` (and alias `calc`) as global entry points.
    - **Interactive Mode (REPL):** Provides a persistent shell session with history, variable management, and configuration commands.
    - **Direct Mode:** Allows evaluating expressions directly from the system terminal arguments.
- **Strict Parsing:** The parser now enforces complete consumption of the input string, rejecting expressions with trailing malformed data.

---

## [0.3.0] - 2025-11-16

### Breaking Changes
- **Operator Redefinition:** The caret symbol `^` is now strictly defined as **Bitwise XOR**. Exponentiation must be performed using `**`.
- **Operator Precedence:** Refactored the AST parser to align with standard Python precedence rules (Bitwise operations bind weaker than arithmetic operations).

### Added
- **Inline Variable Declaration:** Expressions now support temporary variable definitions via comma syntax (e.g., `"x + 1, x=5"`).
- **Bitwise Operations:** Implemented support for AND (`&`), OR (`|`), XOR (`^`), Left Shift (`<<`), and Right Shift (`>>`).
- **Hardware Simulation:**
    - Introduced `word_size` setting (0, 8, 16, 32, 64 bit) to simulate integer overflow and underflow behavior.
    - Introduced `signed_mode` setting to toggle between Two's Complement and Unsigned integer interpretation.
- **Non-Decimal Literals:** Added support for parsing Hexadecimal (`0xFF`), Binary (`0b101`), and Octal (`0o77`) integer literals.
- **Type Casting Prefixes:** Implemented input prefixes to force specific output formats (e.g., `hex:`, `bin:`, `bool:`, `int:`).
- **Strict Mode Settings:** Added configuration options (`only_hex`, `only_binary`) to restrict input formats for specific use cases.

---

## [0.2.0] - 2025-11-15

### Added
- **Equation Solver:** Implemented a solver for linear equations (e.g., `x + 5 = 10`).
- **Settings Management:** Introduced a persistent `config_manager` to handle user preferences and presets.
- **Scientific Engine:** Added support for trigonometric and logarithmic functions (`sin`, `cos`, `tan`, `log`, `sqrt`, `π`, `e`).
- **Formatting Options:** Added settings for decimal precision, fraction output, and automatic type correction.

---

## [0.1.0] - Initial Release - 2025-11-13

### Added
- **Core Architecture:** Implemented the Tokenizer, AST Parser, and Evaluator pipeline.
- **Safe Evaluation:** Built a custom execution engine avoiding Python's `eval()` for security.
- **Arithmetic Support:** Basic operations (`+`, `-`, `*`, `/`) with `decimal.Decimal` precision.
- **Variable System:** Added support for injection of custom variables into the evaluation context.

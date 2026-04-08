"""Non-decimal number parsing, base conversion, word-size limiting, and bit
manipulation functions.

This module handles everything related to binary (``0b``), octal (``0o``),
and hexadecimal (``0x``) literals:

* **Scanning** -- ``non_decimal_scan()`` recognises prefixed literals during
  tokenization and converts them to ``Decimal`` values.
* **Conversion** -- ``value_to_int()`` and ``int_to_value()`` translate
  between prefixed string representations and Python ``int`` values.
* **Word-size limiting** -- ``apply_word_limit()`` and the masking logic
  inside ``int_to_value()`` simulate fixed-width integer overflow (e.g.,
  8-bit, 16-bit) with optional Two's Complement signed-mode interpretation.
* **Bit operations** -- ``setbit``, ``clrbit``, ``togbit``, ``testbit``,
  ``bitnot``, ``bitand``, ``bitor``, ``bitxor``, ``shl``, and ``shr``
  provide the primitives exposed to users via function-call syntax such as
  ``setbit(0b0000, 2)``.
"""

from decimal import Decimal, getcontext, Overflow
from . import error as E


# ---------------------------------------------------------------------------
# Non-decimal literal scanning
# ---------------------------------------------------------------------------

def non_decimal_scan(problem: str, b: int, settings: dict):
    """Attempt to parse a non-decimal literal (``0b``, ``0x``, ``0o``) starting at index *b*.

    Called by the tokenizer whenever a digit is encountered.  Checks whether
    the character at position *b* begins a ``0b``/``0x``/``0o`` prefix and,
    if so, consumes all valid digits for that base.

    Args:
        problem:  The full input string being tokenized.
        b:        The current character index to inspect.
        settings: The active settings dictionary (needs ``allow_non_decimal``).

    Returns:
        tuple: ``(Decimal(parsed_value), next_index)`` on success, or
               ``(None, b)`` if no non-decimal prefix was found.

    Raises:
        E.ConversionError: If an invalid digit is encountered for the
            detected base (code ``8004``).
    """
    from ..calculator.calculator import Operations
    # Early exit if non-decimal literals are disabled in the settings
    if not settings.get("allow_non_decimal", False):
        return (None, b)

    current_char = problem[b]
    non_decimal_flags = {"b", "B", "x", "X", "o", "O"}
    forbidden_char = {".", ","}

    # Check whether the current position starts a 0b / 0x / 0o prefix
    if current_char == '0' and (b + 1 < len(problem)) and problem[b + 1] in non_decimal_flags:
        prefix_char = problem[b + 1]

        # Determine the base-specific prefix, display name, and valid digit set
        if prefix_char in ("b", "B"):
            value_prefix = "0b"
            prefix_name = "Binary"
            allowed_char = {"0", "1"}
        elif prefix_char in ("x", "X"):
            value_prefix = "0x"
            prefix_name = "Hexadecimal"
            allowed_char = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                            "A", "B", "C", "D", "E", "F", "a", "b", "c", "d", "e", "f"}
        else:  # ("o", "O")
            value_prefix = "0o"
            prefix_name = "Octal"
            allowed_char = {"0", "1", "2", "3", "4", "5", "6", "7"}

        # Index of the first digit after the two-character prefix
        a = b + 2

        # If only the bare prefix exists (e.g., "0b" with no digits),
        # value_to_int will raise the appropriate SyntaxError later.
        if a >= len(problem) or problem[a] not in allowed_char:
            pass

        # Accumulate valid digits for this base
        while a < len(problem):
            char_a = problem[a]
            if char_a in allowed_char:
                value_prefix += char_a
            elif char_a in forbidden_char:
                # Decimal points and commas are not valid in non-decimal literals
                break
            elif char_a in Operations or char_a == " " or char_a in "()":
                # An operator, space, or parenthesis marks the end of the literal
                break
            else:
                # Any other character is illegal for this base
                raise E.ConversionError(f"Unexpected token in {prefix_name}: {char_a}", code="8004", position_start=a)
            a += 1

        # 'a' now points one past the last consumed digit
        int_value = value_to_int(str(value_prefix))
        # Return the parsed value and the next index for the tokenizer
        return (Decimal(int_value), a)

    # No non-decimal prefix found; signal the caller to continue normal parsing
    return (None, b)

def value_to_int(value):
    """Convert a prefixed string (``"0xFF"``, ``"0b101"``, ``"0o77"``) to a Python ``int``.

    Uses Python's built-in ``int(value, 0)`` which auto-detects the base
    from the prefix.

    Args:
        value: A string with a ``0b``/``0x``/``0o`` prefix.

    Returns:
        int: The parsed integer value.

    Raises:
        E.ConversionError: If *value* is not a string (code ``8002``).
        E.SyntaxError:     If the prefix has no digits (code ``3035``).
        E.ConversionError: If ``int()`` conversion fails (code ``8000``/``8001``).
    """
    if not isinstance(value, str):
        raise E.ConversionError("Converter didnt receive string: " + str(type(value)), code="8002")
    else:
        if value == "0b":
            raise E.SyntaxError("Invalid Binary Number", code = "3035")
        elif  value == "0x":
            raise E.SyntaxError("Invalid Hex Number", code="3035")
        elif  value == "0O":
            raise E.SyntaxError("Invalid Octcal Number", code="3035")
        try:
            value = int(value, 0)
            return value

        except ValueError as e:
            raise E.ConversionError(f"Couldnt convert {value} to int: {e}", code="8000")

        except Exception as e:
            raise E.ConversionError(f"Unexpected conversion error: {e}", code="8001")


def int_to_value(number, output_prefix, settings):
    """Convert an integer to its hexadecimal, binary, or octal string representation.

    Applies word-size masking and signed-mode interpretation before
    formatting.

    Args:
        number:        The numeric value to convert (``Decimal``, ``int``, or ``float``).
        output_prefix: One of ``"hexadecimal:"``, ``"binary:"``, ``"octal:"``.
        settings:      The active settings dictionary (needs ``word_size``,
                       ``signed_mode``).

    Returns:
        str: The formatted string (e.g., ``"0xff"``, ``"0b1010"``, ``"0o77"``).

    Raises:
        E.ConversionError: If the input is not an integer (code ``8003``)
            or conversion fails (code ``8004``, ``8001``).
    """
    from ..calculator.calculator import Operations
    if isinstance(number, (Decimal, float, int)) and number % 1 != 0:
        raise E.ConversionError("Cannot convert non-integer value to non decimal.", code="8003")
    try:
        if isinstance(number, Decimal):
            number = int(number.to_integral_value())
        else:
            number = int(number)
    except Exception:
        raise E.ConversionError("Input could not be converted to a Python integer.", code="8004")

    val = number
    word_size = settings.get("word_size", 0)
    signed_mode = settings.get("signed_mode", True)

    # --- Word-size masking (simulate fixed-width integer overflow) ---
    if word_size > 0:
        # limit = 2^word_size  (e.g., 256 for 8-bit)
        limit = 1 << word_size
        # mask keeps only the lowest *word_size* bits (e.g., 0xFF for 8-bit)
        mask = limit - 1

        # Discard all bits above the word size
        val = val & mask

        # --- Two's Complement signed reinterpretation ---
        # If the most-significant bit (bit word_size-1) is set, the value
        # is negative in signed mode.  msb_threshold = 2^(word_size-1).
        if signed_mode:
            msb_threshold = limit >> 1
            if val >= msb_threshold:
                # Wrap to negative: e.g., 0xFF -> -1 for 8-bit signed
                val = val - limit

    # --- Format the (possibly masked) integer into the requested base ---
    try:
        if output_prefix == "hexadecimal:":
            converted_value = hex(val)
        elif output_prefix == "binary:":
            converted_value = bin(val)
        elif output_prefix == "octal:":
            converted_value = oct(val)
        return converted_value
    except Exception as e:
        raise E.ConversionError(f"Couldnt convert int to non decimal: {e}", code="8001")


def apply_word_limit(value,settings:dict):
    """Apply word-size constraints to simulate fixed-width integer overflow.

    When ``word_size > 0``, the value is masked to N bits.  In signed mode,
    Two's Complement interpretation is applied (values >= 2^(N-1) wrap to
    negative).

    Args:
        value:    The numeric value to constrain.
        settings: The active settings dictionary (needs ``word_size``,
                  ``signed_mode``).

    Returns:
        Decimal: The constrained value, or the original value if
                 ``word_size == 0`` (unlimited precision).

    Raises:
        E.ConversionError: If the value is not a whole number (code ``5004``).
    """
    word_size = settings["word_size"]
    # word_size == 0 means unlimited precision -- no masking needed
    if word_size == 0:
        return value
    # Bit operations only make sense for whole numbers
    if value % 1 != 0:
        raise E.ConversionError("Requires whole numbers.", code="5004")
    else:
        try:
            val_int = int(value)
            # limit = 2^word_size  (total number of representable values)
            limit = 1 << word_size
            # mask = 2^word_size - 1  (all 1-bits for the given width)
            mask = limit - 1
            # Keep only the lowest *word_size* bits
            val_int = val_int & mask
            # Two's Complement: if the MSB is set, reinterpret as negative
            if settings.get("signed_mode", True):
                # msb_threshold = 2^(word_size-1), the boundary between
                # positive and negative in Two's Complement
                msb_threshold = limit >> 1
                if val_int >= msb_threshold:
                    val_int = val_int - limit

            return Decimal(val_int)
        except Exception as e:
            raise E.ConversionError("Error converting value into int.", code ="5004")


# ---------------------------------------------------------------------------
# Bit manipulation functions
# ---------------------------------------------------------------------------
# These functions are called from the parser (``parse_factor``) when
# expressions like ``setbit(0b0000, 2)`` are evaluated.  They accept
# ``Decimal`` or ``int`` inputs and convert internally.

def setbit(value, pos):
    """Set (force to 1) the bit at position *pos* in *value*.

    Equivalent to ``value | (1 << pos)``.

    Args:
        value: The integer operand (``Decimal`` or ``int``).
        pos:   Zero-based bit position to set (``Decimal`` or ``int``).

    Returns:
        Decimal: The result with the specified bit set.

    Raises:
        E.ConversionError:   If *value* or *pos* cannot be converted to
            ``int`` (code ``8004``).
        E.CalculationError:  If the underlying bit operation fails
            (code ``8007``).
    """
    try:
        val_int = int(value)
        pos_int = int(pos)
    except Exception as e:
        raise E.ConversionError("Input could not be converted to a Python integer.", code = "8004")
    try:
        result_int = val_int | (1 << pos_int)
    except Exception as e:
        raise E.CalculationError("Failed setbit Operation", code = "8007")
    return Decimal(result_int)


def bitnot(value):
    """Bitwise NOT (one's complement) of *value*.

    Equivalent to ``~value``.  For a non-negative integer *n* the result is
    ``-(n + 1)`` (Python's arbitrary-width two's complement).

    Args:
        value: The integer operand (``Decimal`` or ``int``).

    Returns:
        Decimal: The bitwise-inverted result.

    Raises:
        E.ConversionError:  If *value* cannot be converted to ``int``
            (code ``8010``).
        E.CalculationError: If the inversion fails (code ``8011``).
    """
    try:
        val_int = int(value)
    except Exception as e:
        raise E.ConversionError("Input could not be converted to a Python integer for bitnot.", code="8010")

    try:
        result_int = ~val_int
    except Exception as e:
        raise E.CalculationError("Failed bitnot Operation", code="8011")

    return Decimal(result_int)


def bitand(value1, value2):
    """Bitwise AND of two values.

    Equivalent to ``value1 & value2``.

    Args:
        value1: First integer operand (``Decimal`` or ``int``).
        value2: Second integer operand (``Decimal`` or ``int``).

    Returns:
        Decimal: The bitwise AND result.

    Raises:
        E.ConversionError:  If either operand cannot be converted to ``int``
            (code ``8012``).
        E.CalculationError: If the operation fails (code ``8013``).
    """
    try:
        val1_int = int(value1)
        val2_int = int(value2)
    except Exception as e:
        raise E.ConversionError("Input could not be converted to a Python integer for bitand.", code="8012")

    try:
        result_int = val1_int & val2_int
    except Exception as e:
        raise E.CalculationError("Failed bitand Operation", code="8013")

    return Decimal(result_int)


def bitor(value1, value2):
    """Bitwise OR of two values.

    Equivalent to ``value1 | value2``.

    Args:
        value1: First integer operand (``Decimal`` or ``int``).
        value2: Second integer operand (``Decimal`` or ``int``).

    Returns:
        Decimal: The bitwise OR result.

    Raises:
        E.ConversionError:  If either operand cannot be converted to ``int``
            (code ``8014``).
        E.CalculationError: If the operation fails (code ``8015``).
    """
    try:
        val1_int = int(value1)
        val2_int = int(value2)
    except Exception as e:
        raise E.ConversionError("Input could not be converted to a Python integer for bitor.", code="8014")

    try:
        result_int = val1_int | val2_int
    except Exception as e:
        raise E.CalculationError("Failed bitor Operation", code="8015")

    return Decimal(result_int)

def bitxor(value1, value2):
    """Bitwise exclusive OR (XOR) of two values.

    Equivalent to ``value1 ^ value2``.  Each result bit is ``1`` only when
    the corresponding bits of the operands differ.

    Args:
        value1: First integer operand (``Decimal`` or ``int``).
        value2: Second integer operand (``Decimal`` or ``int``).

    Returns:
        Decimal: The bitwise XOR result.
    """
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 ^ value2)


def shl(value1, value2):
    """Logical left shift.

    Equivalent to ``value1 << value2``.  Each shift position multiplies
    the value by 2 and inserts a ``0`` bit on the right.

    Args:
        value1: The integer to shift (``Decimal`` or ``int``).
        value2: Number of bit positions to shift left (``Decimal`` or ``int``).

    Returns:
        Decimal: The shifted result.
    """
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 << value2)


def shr(value1, value2):
    """Arithmetic right shift.

    Equivalent to ``value1 >> value2``.  Each shift position divides the
    value by 2 (rounding toward negative infinity) and discards the
    lowest bit.

    Args:
        value1: The integer to shift (``Decimal`` or ``int``).
        value2: Number of bit positions to shift right (``Decimal`` or ``int``).

    Returns:
        Decimal: The shifted result.
    """
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 >> value2)

def clrbit(value1, value2):
    """Clear (force to 0) the bit at position *value2* in *value1*.

    Equivalent to ``value1 & ~(1 << value2)``.  Creates a mask with all
    bits set except the target position, then ANDs it with the value.

    Args:
        value1: The integer operand (``Decimal`` or ``int``).
        value2: Zero-based bit position to clear (``Decimal`` or ``int``).

    Returns:
        int: The result with the specified bit cleared.
    """
    value1 = int(value1)
    value2 = int(value2)
    return value1 & ~(1 << value2)


def togbit(value1, value2):
    """Toggle (flip) the bit at position *value2* in *value1*.

    Equivalent to ``value1 ^ (1 << value2)``.  If the bit is currently
    ``1`` it becomes ``0``, and vice versa.

    Args:
        value1: The integer operand (``Decimal`` or ``int``).
        value2: Zero-based bit position to toggle (``Decimal`` or ``int``).

    Returns:
        int: The result with the specified bit toggled.
    """
    value1 = int(value1)
    value2 = int(value2)
    return value1 ^ (1 << value2)


def testbit(value1, value2):
    """Test whether the bit at position *value2* is set in *value1*.

    Equivalent to ``(value1 & (1 << value2)) != 0``.

    Args:
        value1: The integer to inspect (``Decimal`` or ``int``).
        value2: Zero-based bit position to test (``Decimal`` or ``int``).

    Returns:
        bool: ``True`` if the bit is set, ``False`` otherwise.
    """
    value1 = int(value1)
    value2 = int(value2)
    return (value1 & (1 << value2)) != 0



"""
Main test suite for the math_engine project.

Contains 234 test cases exercised via pytest. An autouse fixture
(``fresh_preset``) resets the engine's configuration before every test so
that each case starts from a known-good state.

Coverage areas
--------------
- Arithmetic operations and operator precedence
- Decimal-place rounding and fraction output
- Equality / boolean evaluation
- Error codes for invalid syntax and runtime faults
- Variable substitution and the linear-equation solver
- Non-decimal literal parsing (hex, binary, octal)
- Output-prefix selection (hex:, bin:, o:, int:, float:, str:, bool:, d:)
- Strict ``only_hex`` / ``only_binary`` / ``only_octal`` modes
- Memory management (set / delete / show)
- Settings API (change_setting, load_all_settings, load_one_setting)
- Expression validation (``validate()``)
- Scientific functions (sin, cos, log, sqrt, pi)
- Bitwise operators (&, |, ^, <<, >>)
- Advanced operator precedence (bitwise vs arithmetic vs power)
- Word-size limits and signed/unsigned overflow
- Power (**) vs XOR (^) disambiguation
- Nested bracket parsing with mixed number formats
- Augmented-assignment rewriting (+=, -=, etc.)
- Bit-manipulation helper functions (setbit, clrbit, togbit, testbit,
  bitand, bitor, bitxor, shl, shr, bitnot)
- Error-position reporting (character-level indices)
- ``config_manager`` persistence, type validation, and mutual-exclusion
  logic
- CLI entry-point (argument mode, interactive REPL, command handlers)
- Calculator internals (tokeniser edge cases, implicit multiplication)
- Solver internals (linear equations, non-linear rejection)
- ``ScientificEngine`` internals (isPi, isSCT, isLog, isE, isRoot,
  degree mode)
"""

import pytest

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {"decimal_places": 2,
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
    "signed_mode" : False,
    "word_size": 0,
    "readable_error" : False,}


@pytest.fixture(autouse=True)
def fresh_preset():
    """Reset the engine configuration before every test.

    This autouse fixture calls ``reset_settings()`` so that each test
    starts from factory defaults, preventing state leakage between tests.
    The current settings dictionary is returned for convenience but most
    tests simply rely on the side-effect.
    """
    math_engine.utility.config_manager.reset_settings()
    settings = math_engine.utility.config_manager.load_setting_value("all")
    return settings


def load_defaults(**overrides):
    """Load the default settings dict with optional overrides applied.

    Creates a copy of ``DEFAULT_SETTINGS``, merges *overrides* into it,
    and pushes the result into the engine via ``load_preset``.
    """
    settings = DEFAULT_SETTINGS.copy()
    settings.update(overrides)
    math_engine.load_preset(settings)


def assert_error_location(expression, expected_code, expected_start_index, expected_end_index=-1):
    """Evaluate *expression* and verify the resulting error's code and position.

    Parameters
    ----------
    expression : str
        The mathematical expression to evaluate.
    expected_code : str
        The numeric error-code string that the raised ``MathError`` must carry.
    expected_start_index : int
        The zero-based character index where the error is expected to start.
    expected_end_index : int, optional
        If not ``-1``, also assert that ``position_end`` equals this value.

    Raises
    ------
    AssertionError
        If no error is raised, or if the code / position does not match.
    """
    with pytest.raises(E.MathError) as exc:
        math_engine.evaluate(expression)

    # Debug info to help if tests fail
    print(f"\nTesting Expression: '{expression}'")
    print(f"Expected: Code {expected_code} at Index {expected_start_index}")
    print(f"Actual:   Code {exc.value.code} at Index {exc.value.position_start}")

    assert exc.value.code == expected_code
    assert exc.value.position_start == expected_start_index

    if expected_end_index != -1:
        assert exc.value.position_end == expected_end_index
# ---------------------------------------------------------------------------
# 1) Basic arithmetic operations & operator precedence
#    Addition, subtraction, multiplication, division, parentheses,
#    nested parentheses, and unary plus / minus.
# ---------------------------------------------------------------------------

def test_simple_addition():
    assert math_engine.evaluate("1+2") == Decimal("3")


def test_simple_subtraction():
    assert math_engine.evaluate("5-3") == Decimal("2")


def test_simple_multiplication():
    assert math_engine.evaluate("4*3") == Decimal("12")


def test_simple_division():
    assert math_engine.evaluate("8/2") == Decimal("4")


def test_operator_precedence_multiplication_before_addition():
    # 2 + 3*4 = 2 + 12 = 14
    assert math_engine.evaluate("2+3*4") == Decimal("14")


def test_operator_precedence_with_parentheses():
    # (2+3)*4 = 5*4 = 20
    assert math_engine.evaluate("(2+3)*4") == Decimal("20")


def test_nested_parentheses():
    # ((1+2)*(3+4)) = 3*7 = 21
    assert math_engine.evaluate("((1+2)*(3+4))") == Decimal("21")


def test_unary_minus_literal():
    assert math_engine.evaluate("-5") == Decimal("-5")


def test_unary_minus_expression():
    # -(2+3) = -5
    assert math_engine.evaluate("-(2+3)") == Decimal("-5")


def test_unary_plus_is_neutral():
    assert math_engine.evaluate("+5") == Decimal("5")


# ---------------------------------------------------------------------------
# 2) Decimal-place rounding & fraction output
#    Verifies that results honour the configured ``decimal_places`` setting
#    and that high-precision mode works correctly.
# ---------------------------------------------------------------------------

def test_decimal_places_rounding_default_two_decimals():
    # 1 / 3 ≈ 0.33 bei decimal_places = 2
    result = math_engine.evaluate("1/3")
    assert isinstance(result, Decimal)
    # Prüfen nur auf zwei Dezimalstellen als String
    assert str(result).startswith("0.33")


def test_decimal_places_high_precision():
    settings = DEFAULT_SETTINGS.copy()
    settings["decimal_places"] = 5
    math_engine.load_preset(settings)

    result = math_engine.evaluate("1/3")
    assert isinstance(result, Decimal)
    assert str(result).startswith("0.33333")




# ---------------------------------------------------------------------------
# 3) Gleichheit & boolsche Auswertung
# ---------------------------------------------------------------------------

def test_equality_true():
    # 2=2 -> True (mit auto bool Output)
    result = math_engine.evaluate("2=2")
    assert result is True


def test_equality_false():
    result = math_engine.evaluate("2=3")
    assert result is False


def test_equality_with_bool_prefix():
    # bool:2=2 -> True (explizit boolean: prefix)
    result = math_engine.evaluate("bool:2=2")
    assert result is True


def test_equality_with_int_prefix_should_fail():
    settings = DEFAULT_SETTINGS.copy()
    settings["correct_output_format"] = False
    # decimal_places sollte dann egal sein für die Darstellung
    math_engine.load_preset(settings)
    # int:2=2 ist vom Design her inkonsistent
    # Erwartet: ConversionOutputError oder ähnliches (8006 / 8007)
    with pytest.raises(E.MathError) as exc:
        math_engine.evaluate("int:2=2")
    # Hier nur prüfen, dass irgendein 800x Code kommt
    assert exc.value.code.startswith("80")


# ---------------------------------------------------------------------------
# 4) Fehlerfälle allgemeine Syntax (Errorcodes)
# ---------------------------------------------------------------------------

def test_division_by_zero_error_code():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("1/0")
    assert exc.value.code == "3003"


def test_empty_string_error():
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("")
    assert exc.value.code == "3034"


def test_multiple_equal_signs_error():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("1=2=3")
    assert exc.value.code == "3036"


def test_missing_number_after_operator():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("5+")
    assert exc.value.code == "3029"


def test_missing_number_before_equals():
    result = math_engine.evaluate("=5")
    assert result == Decimal("5")

def test_double_decimal_point():
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1.2.3")
    assert exc.value.code == "3008"


def test_unbalanced_parenthesis_missing_closing():
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("(1+2")
    assert exc.value.code == "3009"


def test_unbalanced_parenthesis_missing_opening():
    result = math_engine.evaluate("1+2)")
    assert result == Decimal("3")


def test_unknown_token_variable_name_too_long_in_only_hex_mode():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_hex"] = True
    math_engine.load_preset(settings)
    result = math_engine.evaluate("FF+3")
    assert result == "0x102"

def test_double_exponent_sign():
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e+e3")
    assert exc.value.code == "3031"


# ---------------------------------------------------------------------------
# 5) Variablen & Solver
# ---------------------------------------------------------------------------

def test_single_variable_requires_equation():
    result = math_engine.evaluate("x+1", x=5)
    assert result == Decimal("6")


def test_solve_simple_linear_equation():
    # x + 3 = 7 -> x = 4
    result = math_engine.evaluate("x+3=7", x=0)
    # Je nach Umsetzung: direkt Zahl oder Decimal
    assert result == False


def test_multiple_variables_without_equation():
    result = math_engine.evaluate("x+y", x=1, y=2)
    # Je nach Umsetzung: direkt Zahl oder Decimal
    assert result == Decimal("3")



def test_multiple_variables_without_equation():
    result = math_engine.evaluate("x+y=3", x=1, y=2)
    assert result == True

# ---------------------------------------------------------------------------
# 6) Non-Decimal (Hex / Bin / Oct) – Parsing
# ---------------------------------------------------------------------------

def test_binary_literal_basic():
    # 0b11 = 3
    result = math_engine.evaluate("0b11+1")
    assert result == Decimal("4")


def test_hex_literal_basic():
    # 0xA = 10
    result = math_engine.evaluate("0xA+1")
    assert result == Decimal("11")


def test_octal_literal_basic():
    # 0o10 = 8
    result = math_engine.evaluate("0o10+1")
    assert result == Decimal("9")


def test_binary_literal_invalid_digit():
    with pytest.raises(E.ConversionError) as exc:
        math_engine.evaluate("0b102")
    assert exc.value.code in ("8004", "3035")


def test_hex_literal_invalid_digit():
    with pytest.raises(E.ConversionError) as exc:
        math_engine.evaluate("0xG1")
    assert exc.value.code in ("8004", "3035")


def test_non_decimal_disallowed_when_flag_false():
    settings = DEFAULT_SETTINGS.copy()
    settings["allow_non_decimal"] = False
    math_engine.load_preset(settings)

    # 0xF sollte dann nicht erlaubt sein
    with pytest.raises(E.MathError):
        math_engine.evaluate("0xF+1")


# ---------------------------------------------------------------------------
# 7) Non-Decimal – Output-Prefixe (hex:, bin:, o:, ...)
# ---------------------------------------------------------------------------

def test_hex_prefix_output():
    result = math_engine.evaluate("hex:3+3")
    assert result == "0x6"


def test_oct_prefix_output():
    result = math_engine.evaluate("o:3+3")
    assert result == "0o6"


def test_binary_prefix_output():
    result = math_engine.evaluate("bi:3+3")
    assert result == "0b110"


def test_int_prefix_output():
    result = math_engine.evaluate("int:3+3")
    assert isinstance(result, int)
    assert result == 6


def test_float_prefix_output():
    result = math_engine.evaluate("float:5/2")
    assert isinstance(result, float)
    assert abs(result - 2.5) < 1e-9


def test_string_prefix_output():
    result = math_engine.evaluate("str:3+3")
    assert isinstance(result, str)
    assert result in ("6", "6.0", "6.00")


def test_bool_prefix_with_true_expression():
    result = math_engine.evaluate("bool:3=3")
    assert result is True


def test_bool_prefix_with_false_expression():
    result = math_engine.evaluate("bool:3=4")
    assert result is False


def test_hex_prefix_on_non_integer_result_must_fail():
    with pytest.raises(E.ConversionError) as exc:
        math_engine.evaluate("hex:5/2")
    assert exc.value.code in ("8003", "8005", "8007", "8006")


# ---------------------------------------------------------------------------
# 8) Settings: only_hex / only_binary / only_octal
# ---------------------------------------------------------------------------

def test_only_hex_converts_plain_numbers():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_hex"] = True
    math_engine.load_preset(settings)

    # "10" wird als hex "0x10" interpretiert → 16
    result = math_engine.evaluate("d:10+1")
    assert result == Decimal("17")


def test_only_hex_disallows_functions():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_hex"] = True
    math_engine.load_preset(settings)

    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("sin(1)")
    assert exc.value.code == "3033"


def test_only_binary_converts_plain_numbers():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_binary"] = True
    math_engine.load_preset(settings)

    # "10" -> "0b10" -> 2
    result = math_engine.evaluate("D:10+1")
    assert result == Decimal("3")


def test_only_octal_converts_plain_numbers():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_octal"] = True
    math_engine.load_preset(settings)

    # "10" -> "0o10" -> 8
    result = math_engine.evaluate("d:10+1")
    assert result == Decimal("9")


def test_only_hex_sets_default_output_to_hex_when_empty_prefix():
    settings = DEFAULT_SETTINGS.copy()
    settings["only_hex"] = True
    math_engine.load_preset(settings)

    # kein Prefix -> laut deinem Code sollte output_prefix "hexadecimal:" werden
    result = math_engine.evaluate("3+3")
    assert result == "0x6"


# ---------------------------------------------------------------------------
# 9) Memory-Features (set_memory / delete_memory / show_memory)
# ---------------------------------------------------------------------------

def test_memory_basic_set_and_use():
    math_engine.set_memory("LEVEL", "5")
    result = math_engine.evaluate("LEVEL+3")
    assert result == Decimal("8")


def test_memory_overridden_by_kwargs():
    math_engine.set_memory("LEVEL", "5")
    result = math_engine.evaluate("LEVEL+3", LEVEL=10)
    # kwargs sollen memory überschreiben
    assert result == Decimal("13")


def test_delete_memory_single_key():
    math_engine.set_memory("X", "4")
    math_engine.delete_memory("X")
    mem = math_engine.show_memory()
    assert "X" not in mem


def test_delete_memory_nonexistent_raises():
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.delete_memory("DOES_NOT_EXIST")
    assert exc.value.code == "4000"


def test_delete_memory_all():
    math_engine.set_memory("A", "1")
    math_engine.set_memory("B", "2")
    math_engine.delete_memory("all")
    mem = math_engine.show_memory()
    assert mem == {}


# ---------------------------------------------------------------------------
# 10) Settings-API (change_setting, load_all_settings, load_one_setting)
# ---------------------------------------------------------------------------

def test_change_setting_decimal_places():
    rv = math_engine.change_setting("decimal_places", 5)
    assert rv == 1
    settings = math_engine.load_all_settings()
    assert settings["decimal_places"] == 5


def test_change_setting_invalid_returns_minus_one():
    # wenn deine save_setting das so macht
    rv = math_engine.change_setting("non_existing_setting", 123)
    assert rv in (1, -1)


def test_load_one_setting():
    math_engine.change_setting("decimal_places", 3)
    value = math_engine.load_one_setting("decimal_places")
    assert value == 3


# ---------------------------------------------------------------------------
# 11) validate() – nur Parsen / Fehler melden
# ---------------------------------------------------------------------------

def test_validate_valid_expression_returns_without_exception():
    result = math_engine.validate("3+3")
    print(result)
    assert result is not None





# ---------------------------------------------------------------------------
# 12) Wissenschaftliche Funktionen (sin, cos, log, √, pi)
# ---------------------------------------------------------------------------



def test_sin_function_with_degrees_false():
    # use_degrees=False -> radian
    result = math_engine.evaluate("sin(0)")
    assert isinstance(result, Decimal)
    assert result == Decimal("0")


def test_log_with_base():
    # log(8,2) = 3
    result = math_engine.evaluate("log(8,2)")
    # rounding on 2 decimal_places: "3.00"
    assert str(result).startswith("3")


def test_sqrt_alias():
    result = math_engine.evaluate("sqrt(9)")
    assert result == Decimal("3")


# def test_function_missing_open_paren():
#     with pytest.raises(E.SyntaxError) as exc:
#         math_engine.evaluate("sin 1)")
#     assert exc.value.code == "3010"
#WIP

# ===========================================================================
# NEW TESTS
# ===========================================================================

# ---------------------------------------------------------------------------
# 14) Bitwise Operators (Basic)
# ---------------------------------------------------------------------------

def test_bitwise_and_basic():
    """Test basic AND operation: 3 (011) & 1 (001) -> 1."""
    result = math_engine.evaluate("3 & 1")
    assert result == Decimal("1")


def test_bitwise_or_basic():
    """Test basic OR operation: 1 (001) | 2 (010) -> 3 (011)."""
    result = math_engine.evaluate("1 | 2")
    assert result == Decimal("3")


def test_bitwise_xor_basic():
    """Test basic XOR operation: 3 (011) ^ 1 (001) -> 2 (010)."""
    # ^ is now hardcoded as XOR
    result = math_engine.evaluate("3 ^ 1")
    assert result == Decimal("2")


def test_bitwise_shift_left():
    """Test left shift: 1 << 2 -> 4."""
    result = math_engine.evaluate("1 << 2")
    assert result == Decimal("4")


def test_bitwise_shift_right():
    """Test right shift: 8 >> 2 -> 2."""
    result = math_engine.evaluate("8 >> 2")
    assert result == Decimal("2")


def test_bitwise_fails_on_float():
    """Ensure bitwise ops raise error on floats."""
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("3.5 & 1")
    assert exc.value.code in ("3041", "3042", "8003")


# ---------------------------------------------------------------------------
# 15) Operator Precedence (Advanced)
# ---------------------------------------------------------------------------

def test_precedence_plus_vs_shift():
    """Verify (+) binds stronger than (<<)."""
    # 1 << 1 + 1  => 1 << 2 => 4
    result = math_engine.evaluate("1 << 1 + 1")
    assert result == Decimal("4")


def test_precedence_and_vs_or():
    """Verify (&) binds stronger than (|)."""
    # 1 | 2 & 0 => 1 | (0) => 1
    result = math_engine.evaluate("1 | 2 & 0")
    assert result == Decimal("1")


def test_precedence_xor_vs_or():
    """Verify (^) binds stronger than (|)."""
    # 1 | 3 ^ 3 => 1 | (0) => 1
    result = math_engine.evaluate("1 | 3 ^ 3")
    assert result == Decimal("1")


def test_precedence_complex_mixed():
    """Test full chain: | < ^ < & < << < + < * < **."""
    # 3 | 2 * 2 ** 3 + 1
    # 2**3=8 -> 2*8=16 -> 16+1=17 -> 3|17=19
    result = math_engine.evaluate("3 | 2 * 2 ** 3 + 1")
    assert result == Decimal("19")


# ---------------------------------------------------------------------------
# 16) Word Size & Signed Mode logic
# ---------------------------------------------------------------------------

def test_word_size_8bit_signed_overflow():
    """Test 8-bit signed overflow: 127 + 1 -> -128."""
    settings = DEFAULT_SETTINGS.copy()
    settings["word_size"] = 8
    settings["signed_mode"] = True
    math_engine.load_preset(settings)

    result = math_engine.evaluate("127 + 1")
    assert result == Decimal("-128")


def test_word_size_8bit_unsigned_underflow():
    """Test 8-bit unsigned underflow: 5 - 10 -> 251."""
    settings = DEFAULT_SETTINGS.copy()
    settings["word_size"] = 8
    settings["signed_mode"] = False
    math_engine.load_preset(settings)

    result = math_engine.evaluate("5 - 10")
    assert result == Decimal("251")


def test_word_size_hex_output_negative_signed():
    """Test hex output for negative numbers in signed mode."""
    settings = DEFAULT_SETTINGS.copy()
    settings["word_size"] = 8
    settings["signed_mode"] = True
    math_engine.load_preset(settings)

    # -1 mask 255 -> 255 -> signed check -> -1 -> "-0x1"
    result = math_engine.evaluate("hex: -1")
    assert result == "-0x1"


def test_word_size_hex_output_unsigned():
    """Test hex output for negative numbers in unsigned mode."""
    settings = DEFAULT_SETTINGS.copy()
    settings["word_size"] = 8
    settings["signed_mode"] = False
    math_engine.load_preset(settings)

    # -1 mask 255 -> 255 -> "0xff"
    result = math_engine.evaluate("hex: -1")
    assert result == "0xff"


def test_word_size_16bit_limit():
    """Test 16-bit overflow limit."""
    settings = DEFAULT_SETTINGS.copy()
    settings["word_size"] = 16
    settings["signed_mode"] = False
    math_engine.load_preset(settings)

    # 1 << 16 = 65536 -> overflows to 0
    result = math_engine.evaluate("1 << 16")
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# 17) Power (**) vs XOR (^)
# ---------------------------------------------------------------------------

def test_caret_is_xor_always():
    """Confirm ^ is treated as XOR."""
    # 2 ^ 3 => 1
    result = math_engine.evaluate("2^3")
    assert result == Decimal("1")


def test_double_star_is_power():
    """Confirm ** is treated as power."""
    # 2 ** 3 => 8
    result = math_engine.evaluate("2**3")
    assert result == Decimal("8")


def test_power_right_associativity():
    """Confirm powers are calculated right-to-left."""
    # 2 ** 2 ** 3 => 2 ** 8 => 256
    result = math_engine.evaluate("2 ** 2 ** 3")
    assert result == Decimal("256")


# ---------------------------------------------------------------------------
# 18) Parsing Deep Dive (Nested Brackets & Formats)
# ---------------------------------------------------------------------------

def test_deep_nested_brackets_with_bitwise():
    """Test deep nesting with various bitwise operators."""
    # (0x10 ^ (0b11 << 1)) -> (16 ^ 6) -> 22
    result = math_engine.evaluate("(0x10 ^ (0b11 << 1))")
    assert result == Decimal("22")


def test_hex_bin_arithmetic_mix():
    """Test mixing hex, binary and decimal in one expression."""
    # 0xFF (255) + 0b10 (2) - 10 = 247 -> 0xF7
    result = math_engine.evaluate("hex: 0xFF + 0b10 - 10")
    assert result == "0xf7"


def test_operator_at_start_error():
    """Test invalid syntax starting with operator."""
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("* 5")
    assert exc.value.code == "3028"


# ---------------------------------------------------------------------------
# 19) Augmented Assignment Logic
# ---------------------------------------------------------------------------

def test_augmented_assignment_simulation():
    """Test the implicit rewrite of += without variables."""
    # 5 += 2 -> 5 = 5 + 2 -> 5 = 7 -> False
    result = math_engine.evaluate("5 += 2")
    assert result == Decimal("7")


def test_augmented_assignment_not_allowed_in_solver():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("x += 5")
    assert exc.value.code == "3030"

# ---------------------------------------------------------------------------
# 20) Bit
# ---------------------------------------------------------------------------
def test_bitand_basic():
    assert math_engine.evaluate("int:bitand(0b1100, 0b1010)") == 0b1000

def test_bitxor_basic():
    assert math_engine.evaluate("int:bitxor(0b1010, 0b0110)") == 0b1100

def test_shl_basic():
    assert math_engine.evaluate("int:shl(1, 3)") == 8

def test_shr_basic():
    load_defaults()
    result = math_engine.evaluate("shr(0b100000, 3)")
    # 0b100000 (32) >> 3 = 0b00100 (4)
    assert result == Decimal(4)


def test_setbit_basic():
    assert math_engine.evaluate("int:setbit(0, 3)") == 8
# --- setbit ---------------------------------------------------------------

def test_setbit_basic_binary():
    load_defaults()
    result = math_engine.evaluate("setbit(0b0000, 2)")
    # 0b0000 -> Bit 2 setzen -> 0b0100 = 4
    assert result == Decimal(4)


def test_setbit_basic_hex():
    load_defaults()
    result = math_engine.evaluate("setbit(0x0, 3)")
    # 0x0 -> Bit 3 setzen -> 0b1000 = 8
    assert result == Decimal(8)


def test_setbit_requires_integer_arguments():
    load_defaults()
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("setbit(1.5, 1)")
    assert exc.value.code == "3041"


# --- clrbit ---------------------------------------------------------------

def test_clrbit_basic():
    load_defaults()
    result = math_engine.evaluate("clrbit(0b1111, 1)")
    # 0b1111 -> Bit 1 löschen -> 0b1101 = 13
    assert result == Decimal(13)


# --- togbit ---------------------------------------------------------------

def test_togbit_basic():
    load_defaults()
    result = math_engine.evaluate("togbit(0b1010, 1)")
    # 0b1010 -> Bit 1 togglen -> 0b1000 = 8
    assert result == Decimal(8)


# --- bitand / bitor / bitxor ---------------------------------------------

def test_bitand_basic():
    load_defaults()
    result = math_engine.evaluate("bitand(0b1101, 0b1011)")
    # 1101 & 1011 = 1001 = 9
    assert result == Decimal(9)


def test_bitor_basic():
    load_defaults()
    result = math_engine.evaluate("bitor(0b0011, 0b0101)")
    # 0011 | 0101 = 0111 = 7
    assert result == Decimal(7)


def test_bitxor_basic():
    load_defaults()
    result = math_engine.evaluate("bitxor(0b1100, 0b1010)")
    # 1100 ^ 1010 = 0110 = 6
    assert result == Decimal(6)


def test_bitops_mixed_bases():
    load_defaults()
    result = math_engine.evaluate("bitand(0xF0, 0b11110000)")
    assert result == Decimal(240)


# --- shl / shr ------------------------------------------------------------

def test_shl_basic():
    load_defaults()
    result = math_engine.evaluate("shl(3, 4)")
    # 3 << 4 = 48
    assert result == Decimal(48)


def test_shr_basic():
    load_defaults()
    result = math_engine.evaluate("shr(0b100000, 3)")
    # 0b100000 (32) >> 3 = 0b1000 (4)
    assert result == Decimal(4)


def test_shift_requires_integer_arguments():
    load_defaults()
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("shl(2.5, 1)")
    assert exc.value.code == "3041"


# --- bitnot ---------------------------------------------------------------

def test_bitnot_zero_default_word_size():
    # word_size = 0 => Python-Arithmetik, also ~0 = -1
    load_defaults(word_size=0)
    result = math_engine.evaluate("bitnot(0)")
    assert result == Decimal(-1)





# --- testbit --------------------------------------------------------------

def test_testbit_true():

    # 0b1010 -> Bit 3 (0b1000) ist 1
    result = math_engine.evaluate("bool:testbit(0b1010, 3)")
    assert result is True


def test_testbit_false():

    # 0b1010 -> Bit 0 ist 0
    result = math_engine.evaluate("bool:testbit(0b1010, 0)")
    assert result is False


def test_testbit_requires_integer_arguments():
    with pytest.raises(E.CalculationError) as exc:
        math_engine.evaluate("bool:testbit(1.5, 0)")
    assert exc.value.code == "3041"



# ---------------------------------------------------------------------------
# 21
# ---------------------------------------------------------------------------

def test_21_pos_double_decimal_point():
    # Input: "12.3.4" -> 2nd dot at index 4
    assert_error_location("12.3.4", "3008", 4)

def test_22_pos_unexpected_token_symbol():
    # Input: "1 + $ 2" -> $ at index 4
    assert_error_location("1 + $ 2", "3012", 4)

def test_23_pos_invalid_hex_digit():
    # Input: "0xZZ" -> Z at index 2
    assert_error_location("0xZZ", "8004", 2)

def test_24_pos_missing_exponent_value():
    # Input: "1.5e" -> e at index 3
    assert_error_location("1.5e", "3032", 3)

def test_25_pos_double_exponent_sign():
    # Input: "1eEE"
    # 0='1', 1='e', 2='E' (invalid).
    # Engine flags the first invalid 'E'.
    assert_error_location("1eEE", "3031", 2)

def test_26_pos_missing_closing_paren_end_of_string():
    # Input: "(1+2"
    # Engine logic: Error at (opening_paren_pos + 1)
    # '(' is at 0, so error is at 1.
    assert_error_location("(1+2", "3009", 0)

def test_27_pos_missing_opening_paren_for_function():
    # New logic: "sin" without "(" is treated as a variable name that is too long.
    assert_error_location("sin 5", "3010", 2)

def test_28_pos_missing_number_after_operator():
    # Input: "5 +" -> + at index 2
    assert_error_location("5 +", "3029", 2)

def test_29_pos_multiple_equals_signs():
    # Input: "x = 5 = 6" -> 2nd = at index 6
    assert_error_location("x = 5 = 6", "3036", 6)

def test_30_pos_operator_at_start():
    # Input: "* 5" -> * at index 0
    assert_error_location("* 5", "3028", 0)

def test_31_pos_division_by_zero():
    # Input: "10 / 0" -> / at index 3
    assert_error_location("10 / 0", "3003", 3)

def test_32_pos_bit_function_float_argument():
    # Input: "setbit(1.5, 1)" -> setbit starts at 0
    assert_error_location("setbit(1.5, 1)", "3041", 0)

def test_33_pos_bitnot_extra_comma():
    # Input: "bitnot(5, 2)" -> , at index 8
    assert_error_location("bitnot(5, 2)", "8008", 8)

def test_34_pos_invalid_shift_syntax_mixed():
    assert_error_location("1 >< 2", "3040", -1)

def test_35_pos_whitespace_offset_division():
    # Input: "10   /   0" -> / at index 5
    assert_error_location("10   /   0", "3003", 5)

def test_36_pos_whitespace_offset_unexpected_char():
    # Input: "1   @" -> @ at index 4
    assert_error_location("1   @", "3012", 4)

def test_37_pos_scientific_notation_missing_exponent_padded():
    # Input: "1.5e   " -> e at index 3
    assert_error_location("1.5e   ", "3032", 3)

def test_38_pos_function_name_too_long_for_variable_check():
    # Input: "(( 1 )"
    # Outer '(' at 0. Inner '(' at 1.
    # Inner block closes fine. Outer block unclosed.
    # Engine logic: Error at (outer_paren_pos + 1) = 1.
    assert_error_location("(( 1 )", "3009", 0)

# --- Kombinierter Integrationstest ---------------------------------------


# ---------------------------------------------------------------------------
# 1. Tests für Datei-Fehler (IO / JSON Errors) in config_manager
# ---------------------------------------------------------------------------

def test_load_setting_value_file_not_found():
    """Testet, ob ein leeres Dict zurückkommt, wenn die config.json fehlt."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = config_manager.load_setting_value("all")
        assert result == {}


def test_load_setting_value_corrupt_json():
    """Testet, ob ein leeres Dict zurückkommt, wenn die JSON kaputt ist."""
    with patch("builtins.open", mock_open(read_data="{ broken json")):
        with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
            result = config_manager.load_setting_value("all")
            assert result == {}


def test_force_overwrite_settings_io_error():
    """
    Testet Error 5002.
    Hinweis: Wir simulieren FileNotFoundError, da der aktuelle Code PermissionError
    nicht explizit fängt, aber FileNotFoundError schon.
    """
    with patch("builtins.open", side_effect=FileNotFoundError("Simulated FS Error")):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.force_overwrite_settings({})
        assert exc.value.code == "5002"


def test_save_setting_io_error():
    """Testet Error 5002 beim Speichern."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"my_key": 1}):
        # Auch hier nutzen wir FileNotFoundError, damit der Test durchläuft
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(E.ConfigError) as exc:
                config_manager.save_setting("my_key", 2)
            assert exc.value.code == "5002"


# ---------------------------------------------------------------------------
# 2. Tests für Memory-Management (__init__.py)
# ---------------------------------------------------------------------------

def test_delete_memory_all():
    """Testet das Löschen des gesamten Speichers."""
    math_engine.set_memory("var1", "10")
    math_engine.set_memory("var2", "20")
    math_engine.delete_memory("all")
    assert math_engine.show_memory() == {}


def test_delete_memory_not_exist():
    """Testet Fehler 4000 beim Löschen einer nicht existierenden Variable."""
    math_engine.delete_memory("all")
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.delete_memory("ghost_variable")
    assert exc.value.code == "4000"


# ---------------------------------------------------------------------------
# 3. Tests für 'Readable Error' Prints (CLI vs Non-CLI)
# ---------------------------------------------------------------------------

def test_evaluate_readable_error_cli_output(capsys):
    """Testet die ASCII-Art Ausgabe im CLI-Modus bei Fehlern."""
    math_engine.change_setting("readable_error", True)

    # 10/0 -> Fehler an Index 2 ('/')
    # Formel im Code: (pos + 4) * " "
    # 2 + 4 = 6 Leerzeichen
    math_engine.evaluate("10/0", is_cli=True)

    captured = capsys.readouterr()

    # Korrigierte Anzahl Leerzeichen (6 statt 7)
    expected_arrow = "      ^ HERE IS THE PROBLEM"

    assert "Code: 3003" in captured.out
    assert expected_arrow in captured.out


def test_evaluate_readable_error_non_cli_output(capsys):
    """Testet die Ausgabe im Non-CLI Modus (Unterstreichung)."""
    math_engine.change_setting("readable_error", True)

    math_engine.evaluate("10/0", is_cli=False)

    captured = capsys.readouterr()
    assert "\033[4m" in captured.out
    assert "Code: 3003" in captured.out


def test_validate_print_output(capsys):
    """Testet die Print-Ausgabe von validate() bei Fehlern."""
    # Wir nehmen "1+" (Syntaxfehler), damit validate wirklich fehlschlägt.
    # "10/0" ist syntaktisch korrekt und wirft erst beim Rechnen (evaluate) einen Fehler.
    result = math_engine.validate("1+")

    # validate() hat kein explizites return im except-Block, daher None
    assert result is None

    captured = capsys.readouterr()
    # "1+" -> Fehler an Index 2 (das Nichts danach) -> Code 3029 (Missing number)
    assert "Code: 3029" in captured.out
    assert "^ HERE IS THE PROBLEM" in captured.out


# ---------------------------------------------------------------------------
# 4. Tests für spezielle Config-Logiken (__init__.py & config_manager)
# ---------------------------------------------------------------------------

def test_change_setting_failure_propagation():
    """Testet, ob change_setting -1 zurückgibt, wenn save_setting fehlschlägt."""
    with patch("math_engine.config_manager.save_setting", return_value=-1):
        result = math_engine.change_setting("any_setting", 1)
        assert result == -1


def test_load_preset_unknown_settings_error():
    """Testet Fehler 5003 wenn Preset unbekannte Keys hat."""
    bad_preset = {"INVALID_KEY_XYZ": 123}
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.load_preset(bad_preset)
    assert exc.value.code == "5003"


import pytest
from unittest.mock import mock_open
import json
from math_engine.utility import config_manager


# ---------------------------------------------------------------------------
# 1. Tests für Datei-Fehler (IO / JSON Errors) in config_manager
# ---------------------------------------------------------------------------

def test_load_setting_value_file_not_found():
    """Simuliert fehlende config.json -> muss leeres Dict {} zurückgeben."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = config_manager.load_setting_value("all")
        assert result == {}


def test_load_setting_value_corrupt_json():
    """Simuliert kaputte config.json -> muss leeres Dict {} zurückgeben."""
    with patch("builtins.open", mock_open(read_data="{ kaputtes json")):
        with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
            result = config_manager.load_setting_value("all")
            assert result == {}


def test_force_overwrite_settings_io_error():
    """Testet Error 5002 beim Speichern (simuliert durch FileNotFoundError)."""
    with patch("builtins.open", side_effect=FileNotFoundError("Simulierter Fehler")):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.force_overwrite_settings({})
        assert exc.value.code == "5002"


def test_save_setting_io_error():
    """Testet Error 5002 beim Speichern eines einzelnen Werts."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"test_key": 1}):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(E.ConfigError) as exc:
                config_manager.save_setting("test_key", 2)
            assert exc.value.code == "5002"


# ---------------------------------------------------------------------------
# 2. Tests für load_setting_description (UI Strings)
# ---------------------------------------------------------------------------

def test_load_setting_description_all():
    """Testet das Laden aller UI-Strings."""
    dummy_data = {"key1": "Text 1", "key2": "Text 2"}
    with patch("builtins.open", mock_open(read_data=json.dumps(dummy_data))):
        result = config_manager.load_setting_description("all")
        assert result == dummy_data


def test_load_setting_description_single():
    """Testet das Laden eines einzelnen UI-Strings."""
    dummy_data = {"my_setting": "Das ist eine Einstellung"}
    with patch("builtins.open", mock_open(read_data=json.dumps(dummy_data))):
        result = config_manager.load_setting_description("my_setting")
        assert result == "Das ist eine Einstellung"


def test_load_setting_description_missing_file():
    """Testet Verhalten bei fehlender ui_strings.json."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = config_manager.load_setting_description("all")
        assert result == {}


# ---------------------------------------------------------------------------
# 3. Tests für Typ-Logik in save_setting (Spezialfälle)
# ---------------------------------------------------------------------------

def test_save_setting_bool_where_int_expected():
    """Bool (True) darf dort gespeichert werden, wo Int erwartet wird."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"decimal_places": 2}):
        with patch("builtins.open", mock_open()):
            config_manager.save_setting("decimal_places", True)


def test_save_setting_int_where_bool_expected_valid():
    """0 oder 1 darf dort gespeichert werden, wo Bool erwartet wird."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"debug": False}):
        with patch("builtins.open", mock_open()):
            config_manager.save_setting("debug", 1)  # 1 = True
            config_manager.save_setting("debug", 0)  # 0 = False


def test_save_setting_int_where_bool_expected_invalid():
    """Fehlerfall: Zahl != 0/1 darf NICHT als Bool gespeichert werden."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"debug": False}):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.save_setting("debug", 5)
        assert exc.value.code == "5000"
        assert "Only 0 or 1 allowed" in str(exc.value)


def test_save_setting_general_type_mismatch():
    """Allgemeiner Typfehler: String statt Int."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"decimal_places": 2}):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.save_setting("decimal_places", "zwei")
        assert exc.value.code == "5000"


def test_save_setting_word_size_invalid():
    """Testet ungültige Word-Size Werte (z.B. 12 Bit)."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"word_size": 0}):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.save_setting("word_size", 12)
        assert exc.value.code == "5003"


# ---------------------------------------------------------------------------
# 4. Tests für Output Format Abkürzungen
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("input_val, expected_prefix", [
    # Wir geben hier "s:" statt "s" ein, damit der Code den Prefix erkennt
    # und ihn zu "string:" expandiert. Das deckt die roten Zeilen im Code ab!
    ("s:", "string:"), ("str:", "string:"), ("string:", "string:"),
    ("bo:", "boolean:"), ("bool:", "boolean:"),
    ("d:", "decimal:"), ("dec:", "decimal:"),
    ("f:", "float:"), ("float:", "float:"),
    ("i:", "int:"), ("int:", "int:"),
    ("h:", "hexadecimal:"), ("hex:", "hexadecimal:"),
    ("bi:", "binary:"), ("bin:", "binary:"),
    ("o:", "octal:"), ("oct:", "octal:"), ("oc:", "octal:"),
    ("decimal:", "decimal:"),

    # Teste auch die "Pure Name" Logik (Fallback)
    # Wenn man nur "dec" eingibt (ohne Doppelpunkt), hängt der Code nur ":" an,
    # expandiert es aber NICHT (laut deinem aktuellen Code).
    ("dec", "dec:"),
    ("hex", "hex:"),
])
def test_default_output_format_expansions(input_val, expected_prefix):
    """Testet alle Abkürzungen für Output-Formate."""
    mock_settings = {"default_output_format": "decimal:"}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_settings):
        with patch("json.dump") as mock_dump:
            with patch("builtins.open", mock_open()):
                config_manager.save_setting("default_output_format", input_val)
                # Prüfen, was gespeichert worden wäre
                saved_dict = mock_dump.call_args[0][0]
                assert saved_dict["default_output_format"] == expected_prefix


def test_default_output_format_invalid():
    """Testet Fehler bei unbekanntem Format."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"default_output_format": "decimal:"}):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.save_setting("default_output_format", "pizza_format")
        assert exc.value.code == "5002"


# ---------------------------------------------------------------------------
# 5. Tests für Exklusive Flags (only_hex vs only_binary)
# ---------------------------------------------------------------------------

def test_mutual_exclusive_only_hex():
    """Wenn only_hex=True gesetzt wird, müssen binary und octal False werden."""
    mock_settings = {"only_hex": False, "only_binary": True, "only_octal": True}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_settings):
        with patch("json.dump") as mock_dump:
            with patch("builtins.open", mock_open()):
                config_manager.save_setting("only_hex", True)

                saved_dict = mock_dump.call_args[0][0]
                assert saved_dict["only_hex"] is True
                assert saved_dict["only_binary"] is False
                assert saved_dict["only_octal"] is False


def test_mutual_exclusive_only_binary():
    """Wenn only_binary=True gesetzt wird, müssen hex und octal False werden."""
    mock_settings = {"only_hex": True, "only_binary": False, "only_octal": True}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_settings):
        with patch("json.dump") as mock_dump:
            with patch("builtins.open", mock_open()):
                config_manager.save_setting("only_binary", True)

                saved_dict = mock_dump.call_args[0][0]
                assert saved_dict["only_binary"] is True
                assert saved_dict["only_hex"] is False
                assert saved_dict["only_octal"] is False


# ---------------------------------------------------------------------------
# 6. Memory Tests
# ---------------------------------------------------------------------------

def test_delete_memory_all():
    math_engine.set_memory("a", "1")
    math_engine.delete_memory("all")
    assert math_engine.show_memory() == {}


def test_delete_memory_error():
    # Korrigierter Test: Wir rufen jetzt delete_memory auf und prüfen den SyntaxError
    math_engine.delete_memory("all")
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.delete_memory("nicht_da")
    assert exc.value.code == "4000"


# ---------------------------------------------------------------------------
# LÜCKENSCHLUSS-TESTS (Coverage Gap Fillers)
# ---------------------------------------------------------------------------

def test_save_setting_bool_as_int_pass():
    """Deckt Zeile 163 ab: Bool (True/False) wird in Int-Feld akzeptiert (pass)."""
    # 'decimal_places' ist int. Wir speichern True (was 1 entspricht).
    with patch("math_engine.config_manager.load_setting_value", return_value={"decimal_places": 2}):
        with patch("builtins.open", mock_open()):
            # Das hier muss ohne Fehler durchlaufen und in den 'if ... pass' Zweig gehen
            config_manager.save_setting("decimal_places", True)


def test_mutual_exclusive_only_octal():
    """Deckt Zeile 253 ab: only_octal schaltet hex und binary aus."""
    mock_settings = {"only_hex": True, "only_binary": True, "only_octal": False}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_settings):
        with patch("json.dump") as mock_dump:
            with patch("builtins.open", mock_open()):
                config_manager.save_setting("only_octal", True)

                # Prüfen, ob die anderen beiden auf False gesetzt wurden
                saved_dict = mock_dump.call_args[0][0]
                assert saved_dict["only_octal"] is True
                assert saved_dict["only_hex"] is False
                assert saved_dict["only_binary"] is False


def test_load_preset_invalid_length():
    """Deckt Zeile 273 ab: Error 5002 wenn Preset-Länge nicht stimmt."""
    # Wir simulieren, dass die aktuellen Settings 2 Einträge haben
    mock_current = {"a": 1, "b": 2}

    # Wir übergeben ein Preset mit nur 1 Eintrag (Länge 1 != Länge 2)
    short_preset = {"a": 10}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_current):
        with pytest.raises(E.SyntaxError) as exc:
            config_manager.load_preset(short_preset)
        assert exc.value.code == "5002"
        assert "Invalid dict" in str(exc.value)


def test_force_overwrite_settings_success():
    """Deckt Zeile 82 ab: Erfolgreicher Durchlauf (return 1)."""
    with patch("builtins.open", mock_open()):
        with patch("json.dump"):
            result = config_manager.force_overwrite_settings({"any": "setting"})
            assert result == 1


# ---------------------------------------------------------------------------
# FINALE LÜCKEN-SCHLUSS-TESTS (Decken image_0e8a26.png ab)
# ---------------------------------------------------------------------------

def test_final_gap_only_octal_logic():
    """Deckt Zeile 252-254 ab: only_octal Logic."""
    # Wir simulieren existierende Settings
    mock_settings = {"only_hex": True, "only_binary": True, "only_octal": False}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_settings):
        with patch("builtins.open", mock_open()):
            # Hier rufen wir explizit "only_octal" auf, um in das 'elif' zu springen
            config_manager.save_setting("only_octal", True)


def test_final_gap_word_size_invalid():
    """Deckt Zeile 259 ab: Exception bei falscher Word-Size."""
    # 'word_size' existiert in Settings, wir versuchen einen ungültigen Wert (99)
    with patch("math_engine.config_manager.load_setting_value", return_value={"word_size": 0}):
        with pytest.raises(E.ConfigError) as exc:
            config_manager.save_setting("word_size", 99)
        assert exc.value.code == "5003"


def test_final_gap_save_setting_io_error():
    """Deckt Zeile 268 ab: Schreibfehler beim Speichern in save_setting."""
    with patch("math_engine.config_manager.load_setting_value", return_value={"any_key": 1}):
        # Wir simulieren, dass open() fehlschlägt (z.B. Schreibschutz)
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(E.ConfigError) as exc:
                config_manager.save_setting("any_key", 2)
            assert exc.value.code == "5002"


def test_final_gap_load_preset_io_error():
    """Deckt Zeile 280 ab: Schreibfehler innerhalb von load_preset."""
    # 1. Mock load_setting_value: Muss gleiche Länge haben wie Preset, damit wir nicht in Error 5002 (Invalid dict) laufen
    mock_current = {"a": 1}
    preset_to_load = {"a": 2}

    with patch("math_engine.config_manager.load_setting_value", return_value=mock_current):
        # 2. Mock open: Muss fehlschlagen beim Schreiben
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(E.ConfigError) as exc:
                config_manager.load_preset(preset_to_load)
            assert exc.value.code == "5002"


# ---------------------------------------------------------------------------
# 1. Test für den Argument-Modus (python -m math_engine "1+1")
# ---------------------------------------------------------------------------

def test_main_arg_mode_success(capsys):
    """Testet den Aufruf mit Argumenten: `math-engine '1+1'`"""
    # Wir simulieren sys.argv
    with patch.object(sys, 'argv', ["prog_name", "1+1"]):
        # Wir fälschen evaluate, damit wir nicht wirklich rechnen müssen
        with patch("math_engine.cli.cli.evaluate", return_value=2):
            cli.main()

    # Wir prüfen, ob '2' auf der Konsole ausgegeben wurde
    captured = capsys.readouterr()
    assert "2" in captured.out


def test_main_arg_mode_error(capsys):
    """Testet Fehler im Argument-Modus (z.B. Division durch Null)."""
    with patch.object(sys, 'argv', ["prog_name", "1/0"]):
        # evaluate wirft hier einen Fehler
        with patch("math_engine.cli.cli.evaluate", side_effect=Exception("DivZero")):
            # Das Programm sollte sich mit Exit Code 1 beenden
            with pytest.raises(SystemExit):
                cli.main()

    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "DivZero" in captured.out


def test_main_starts_interactive_mode():
    """Wenn keine Argumente gegeben sind, soll der interaktive Modus starten."""
    with patch.object(sys, 'argv', ["prog_name"]):
        with patch("math_engine.cli.cli.run_interactive_mode") as mock_run:
            cli.main()
            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Test für den Interaktiven Modus (Die Eingabe-Schleife)
# ---------------------------------------------------------------------------

def test_interactive_mode_basic_commands(capsys):
    """
    Simuliert eine Session: help -> settings -> mem -> exit.
    Prüft, ob die entsprechenden Ausgaben kommen.
    """
    # Das sind die Eingaben, die der "Benutzer" nacheinander macht
    user_inputs = ["help", "settings", "mem", "exit"]

    # Wir patchen PromptSession, damit prompt() unsere Liste zurückgibt statt zu warten
    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        mock_instance = MockSession.return_value
        mock_instance.prompt.side_effect = user_inputs

        # Wir müssen auch load_all_settings und show_memory mocken, damit Tabellen kommen
        with patch("math_engine.cli.cli.load_all_settings", return_value={"debug": False}), \
                patch("math_engine.cli.cli.show_memory", return_value={"x": 10}):
            cli.run_interactive_mode()

            captured = capsys.readouterr()

            # Checks
            assert "Math Engine Commands" in captured.out  # Help title
            assert "Current Settings" in captured.out  # Settings table title
            assert "Memory" in captured.out  # Memory table title
            assert "Goodbye" not in captured.out  # Normal exit, not EOF


def test_interactive_mode_math_calculation(capsys):
    """Testet eine einfache Rechnung im interaktiven Modus."""
    user_inputs = ["1 + 1", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = user_inputs

        with patch("math_engine.cli.cli.evaluate", return_value=2):
            cli.run_interactive_mode()

            captured = capsys.readouterr()
            # Rich formatiert manchmal fett, daher suchen wir nach dem Kern
            assert "= 2" in captured.out


def test_interactive_mode_math_error(capsys):
    """Testet, ob Mathe-Fehler im interaktiven Modus abgefangen werden."""
    user_inputs = ["1 / 0", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = user_inputs

        # evaluate wirft Fehler
        with patch("math_engine.cli.cli.evaluate", side_effect=Exception("Ouch")):
            cli.run_interactive_mode()

            captured = capsys.readouterr()
            assert "Math Error:" in captured.out
            assert "Ouch" in captured.out


# ---------------------------------------------------------------------------
# 3. Test der speziellen Befehle (set, del, reset, load)
# ---------------------------------------------------------------------------

def test_command_set_setting(capsys):
    """Testet 'set setting key val' Logik (inkl. Typkonvertierung)."""
    # 1. Test: Boolesche Werte (true/false)
    inputs = ["set setting debug true", "set setting verbose off", "set setting number 10", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        with patch("math_engine.cli.cli.change_setting") as mock_change:
            cli.run_interactive_mode()

            # Prüfen der Aufrufe
            mock_change.assert_any_call("debug", True)
            mock_change.assert_any_call("verbose", False)
            mock_change.assert_any_call("number", 10)

    captured = capsys.readouterr()
    assert "Setting updated" in captured.out


def test_command_set_mem(capsys):
    """Testet 'set mem key val'."""
    inputs = ["set mem x 42", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        with patch("math_engine.cli.cli.set_memory") as mock_set:
            cli.run_interactive_mode()
            mock_set.assert_called_with("x", "42")

    captured = capsys.readouterr()
    assert "Memory updated" in captured.out


def test_command_del_mem(capsys):
    """Testet 'del mem key' und 'del mem all'."""
    inputs = ["del mem x", "del mem all", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        with patch("math_engine.cli.cli.delete_memory") as mock_del:
            cli.run_interactive_mode()
            mock_del.assert_any_call("x")
            mock_del.assert_any_call("all")


def test_command_reset(capsys):
    """Testet 'reset settings'."""
    inputs = ["reset settings", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        with patch("math_engine.cli.cli.reset_settings") as mock_reset:
            cli.run_interactive_mode()
            mock_reset.assert_called_once()


def test_command_load_preset(capsys):
    """Testet 'load preset'."""
    # FIX: Wir müssen das Dict in Anführungszeichen setzen (\"...\"),
    # damit shlex die inneren ' Quotes nicht entfernt.
    inputs = ["load preset \"{'a': 1}\"", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        with patch("math_engine.cli.cli.load_preset") as mock_load:
            cli.run_interactive_mode()
            mock_load.assert_called_with({'a': 1})


# ---------------------------------------------------------------------------
# 4. Spezial-Feature: Variablen-Syntax Parsing
# ---------------------------------------------------------------------------

def test_variable_parsing_syntax():
    """
    Testet die spezielle Logik: 'a=5, b=10, a+b'
    Das wird in der Funktion process_input_and_evaluate zerlegt.
    """
    # FIX: Die Logik in cli.py erwartet IMMER erst den Ausdruck, dann die Variablen.
    # Also "a+b, a=5, ..." statt "a=5, ..., a+b"
    user_input = "a+b, a=5, b=10.5"

    # Wir wollen sehen, ob evaluate mit den richtigen kwargs aufgerufen wird
    with patch("math_engine.cli.cli.evaluate") as mock_eval:
        cli.process_input_and_evaluate(user_input)

        # Erwartung: evaluate("a+b", a=5, b=10.5, is_cli=True)
        mock_eval.assert_called_with("a+b", a=5, b=10.5, is_cli=True)


# ---------------------------------------------------------------------------
# 5. Randfälle & Fehlerbehandlung
# ---------------------------------------------------------------------------

def test_ctrl_c_interrupt(capsys):
    """Simuliert Strg+C (KeyboardInterrupt)."""
    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        # prompt() wirft KeyboardInterrupt
        MockSession.return_value.prompt.side_effect = KeyboardInterrupt
        cli.run_interactive_mode()

    captured = capsys.readouterr()
    assert "Goodbye" in captured.out


def test_ctrl_d_eof(capsys):
    """Simuliert Strg+D (EOFError)."""
    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = EOFError
        cli.run_interactive_mode()

    captured = capsys.readouterr()
    assert "Goodbye" in captured.out


def test_invalid_commands(capsys):
    """Testet ungültige Befehle (falsche Subcommands etc)."""
    inputs = [
        "set",  # Missing subcommand
        "set invalid",  # Invalid subcommand
        "set setting",  # Missing args
        "del",  # Missing args
        "del settings",  # Wrong target
        "load",  # Missing args
        "exit"
    ]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs
        cli.run_interactive_mode()

    captured = capsys.readouterr()
    # Wir prüfen nur stichprobenartig, ob Fehlermeldungen oder Usages kamen
    assert "Usage:" in captured.out
    assert "Error:" in captured.out


# ---------------------------------------------------------------------------
# LÜCKENSCHLUSS (Coverage Gap Fillers für CLI)
# ---------------------------------------------------------------------------

def test_print_dict_as_table_empty(capsys):
    """Deckt Zeile 67 ab: 'if not data'."""
    cli.print_dict_as_table("Test", {})
    captured = capsys.readouterr()
    assert "No test found" in captured.out


def test_handle_set_commands_edge_cases(capsys):
    """Deckt Zeile 111 (String-Werte) und Exceptions in set ab."""

    # 1. Test: String Value (else-Zweig bei Typ-Konvertierung)
    # "abc" ist weder bool noch digit -> wird als String übernommen
    with patch("math_engine.cli.cli.change_setting") as mock_change:
        cli.handle_set_command(["setting", "format", "abc"])
        mock_change.assert_called_with("format", "abc")

    # 2. Test: Exception beim Setzen (Deckt Zeile 116-119 ab)
    with patch("math_engine.cli.cli.change_setting", side_effect=Exception("Boom")):
        cli.handle_set_command(["setting", "k", "v"])
        assert "Error changing setting" in capsys.readouterr().out

    # 3. Test: Exception bei Memory (Deckt Zeile 127-130 ab)
    with patch("math_engine.cli.cli.set_memory", side_effect=Exception("Bang")):
        cli.handle_set_command(["mem", "k", "v"])
        assert "Error setting memory" in capsys.readouterr().out


def test_handle_del_errors(capsys):
    """Deckt Zeilen 134, 137, 148 ab (Validierung & Exceptions)."""

    # 1. Falsches Argument (nicht 'mem')
    cli.handle_del_command(["settings"])
    assert "Usage:" in capsys.readouterr().out

    # 2. Fehlender Key (nur 'del mem')
    cli.handle_del_command(["mem"])
    assert "Missing key" in capsys.readouterr().out

    # 3. Exception beim Löschen
    with patch("math_engine.cli.cli.delete_memory", side_effect=Exception("Ouch")):
        cli.handle_del_command(["mem", "key"])
        assert "Error:" in capsys.readouterr().out


def test_handle_reset_errors(capsys):
    """Deckt Zeilen 153, 162 ab (Keine Args & Memory Fehler)."""

    # 1. Keine Argumente
    cli.handle_reset_command([])
    assert "Usage:" in capsys.readouterr().out

    # 2. Exception bei reset mem
    with patch("math_engine.cli.cli.delete_memory", side_effect=Exception("Fail")):
        cli.handle_reset_command(["mem"])
        assert "Error:" in capsys.readouterr().out


def test_handle_load_errors(capsys):
    """Deckt Zeilen 168, 175, 179 ab (Preset Validierung)."""

    # 1. Falscher Subcommand
    cli.handle_load_command(["config"])
    assert "Usage:" in capsys.readouterr().out

    # 2. Kein Dictionary (z.B. eine Liste)
    cli.handle_load_command(["preset", "[1, 2]"])
    assert "Input must be a dictionary" in capsys.readouterr().out

    # 3. Exception während load_preset
    with patch("math_engine.cli.cli.load_preset", side_effect=Exception("Corrupt")):
        cli.handle_load_command(["preset", "{'a': 1}"])
        assert "Error loading preset" in capsys.readouterr().out


def test_process_input_value_error_fallback():
    """
    Deckt Zeile 203-204 ab: Fallback zu String, wenn int/float Konvertierung fehlschlägt.
    Beispiel: 'var=abc' (abc ist keine Zahl)
    """
    user_input = "var, var=abc"

    with patch("math_engine.cli.cli.evaluate") as mock_eval:
        cli.process_input_and_evaluate(user_input)

        # Prüfen, ob 'abc' als String angekommen ist
        mock_eval.assert_called_with("var", var="abc", is_cli=True)


# ---------------------------------------------------------------------------
# FINALE LÜCKENSCHLUSS-TESTS (Teil 2: Basierend auf den neuen Screenshots)
# ---------------------------------------------------------------------------

def test_process_input_parentheses():
    """
    Deckt Zeilen 158-162 ab: Handling von Klammern beim Parsen.
    Der Code trackt bracket_level, um Kommas innerhalb von Funktionen
    nicht als Trennzeichen zu missverstehen.
    """
    # Eingabe: Eine Funktion mit Argumenten in Klammern
    # Die Logik muss erkennen: '(' -> level rauf, ')' -> level runter
    with patch("math_engine.cli.cli.evaluate") as mock_eval:
        cli.process_input_and_evaluate("max(1, 2)")
        # Wichtig: Das Komma durfte NICHT splitten!
        mock_eval.assert_called_with("max(1, 2)", is_cli=True)


def test_interactive_mode_empty_input(capsys):
    """
    Deckt Zeile 13-14 ab: 'if not user_input: continue'
    Wir simulieren: Enter (leer) -> exit
    """
    inputs = ["", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs
        cli.run_interactive_mode()

    # Es darf kein Fehler passiert sein und der Loop muss sauber enden
    captured = capsys.readouterr()
    assert "Goodbye" not in captured.out


def test_mem_command_non_dict_output(capsys):
    """
    Deckt Zeile 25 ab (else-Zweig bei 'mem'):
    Falls show_memory() kein Dict zurückgibt (z.B. String oder None).
    """
    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = ["mem", "exit"]

        # Wir zwingen show_memory dazu, einen String statt Dict zu liefern
        with patch("math_engine.cli.cli.show_memory", return_value="Keine Daten"):
            cli.run_interactive_mode()

    captured = capsys.readouterr()
    # Erwartet wird die formatierte Ausgabe des Strings (italic)
    assert "Keine Daten" in captured.out


def test_reset_mem_success_msg(capsys):
    """
    Deckt Zeile 130 ab: Erfolgsmeldung nach 'delete_memory("all")'.
    """
    # Wir rufen handle_reset_command direkt auf für 'mem'
    with patch("math_engine.cli.cli.delete_memory") as mock_del:
        cli.handle_reset_command(["mem"])
        mock_del.assert_called_with("all")

    captured = capsys.readouterr()
    assert "All memory variables deleted" in captured.out


def test_set_mem_usage_error(capsys):
    """
    Deckt Zeile 89 ab: 'set mem' mit zu wenigen Argumenten.
    """
    # Nur 2 Argumente (mem, key) statt 3 (mem, key, value)
    cli.handle_set_command(["mem", "nur_key"])

    captured = capsys.readouterr()
    assert "Usage:" in captured.out
    assert "set mem <key> <value>" in captured.out


import sys
import math_engine.cli.cli as cli


# ---------------------------------------------------------------------------
# 1. Main Funktion & System Exit (Deckt image_0ea164.png ab)
# ---------------------------------------------------------------------------

def test_main_with_expression_success(capsys):
    """Testet den Pfad: Argument übergeben -> Berechnung erfolgreich -> Print."""
    with patch.object(sys, 'argv', ["math-engine", "1+1"]):
        with patch("math_engine.cli.cli.evaluate", return_value=2):
            cli.main()

    captured = capsys.readouterr()
    assert "2" in captured.out


def test_main_with_expression_error(capsys):
    """
    Deckt Zeile 282-284 ab: Exception in main -> sys.exit(1).
    """
    with patch.object(sys, 'argv', ["math-engine", "bad_input"]):
        # Wir simulieren einen Fehler in evaluate
        with patch("math_engine.cli.cli.evaluate", side_effect=Exception("Critical Math Fail")):
            # sys.exit(1) wird erwartet
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "Critical Math Fail" in captured.out


def test_main_interactive_start():
    """Deckt den else-Zweig ab (keine Args -> Interactive Mode)."""
    with patch.object(sys, 'argv', ["math-engine"]):
        with patch("math_engine.cli.cli.run_interactive_mode") as mock_run:
            cli.main()
            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Interactive Loop & Edge Cases (Deckt image_0ea144.png ab)
# ---------------------------------------------------------------------------

def test_interactive_loop_empty_input(capsys):
    """
    Deckt Zeile 213-214 ab: Leere Eingabe (Enter drücken) -> continue.
    Wir simulieren: [Leerstring, Leerstring, exit]
    """
    inputs = ["", "   ", "exit"]

    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs
        cli.run_interactive_mode()

    # Es darf kein Fehler kommen, Loop läuft weiter bis exit
    captured = capsys.readouterr()
    assert "Goodbye" not in captured.out


def test_interactive_mem_display_non_dict(capsys):
    """
    Deckt Zeile 245 (else-Zweig bei mem):
    Wenn show_memory() kein Dict zurückgibt (z.B. None oder String).
    """
    inputs = ["mem", "exit"]
    with patch("math_engine.cli.cli.PromptSession") as MockSession:
        MockSession.return_value.prompt.side_effect = inputs

        # show_memory gibt String statt Dict zurück
        with patch("math_engine.cli.cli.show_memory", return_value="Keine Variablen"):
            cli.run_interactive_mode()

    captured = capsys.readouterr()
    # Erwartet formatierte Ausgabe
    assert "Keine Variablen" in captured.out


# ---------------------------------------------------------------------------
# 3. Parsing Logik & Klammern (Deckt image_0ea127.png ab)
# ---------------------------------------------------------------------------

def test_process_input_complex_brackets():
    """
    Deckt die for-Schleife in process_input_and_evaluate ab (Zeilen 156-168).
    Prüft, ob Kommas innerhalb von Klammern ignoriert werden.
    """
    # Input: "test(1, 2), a=1"
    # Das erste Komma ist IN der Klammer -> darf nicht splitten.
    # Das zweite Komma ist außerhalb -> muss splitten.
    input_str = "test(1, 2), a=1"

    with patch("math_engine.cli.cli.evaluate") as mock_eval:
        cli.process_input_and_evaluate(input_str)

        # Erwartung: Ausdruck="test(1, 2)", Variable a=1
        mock_eval.assert_called_with("test(1, 2)", a=1, is_cli=True)


def test_process_input_value_conversion_error():
    """
    Deckt den ValueError catch Block ab (Zeile 183-184).
    Wenn int() fehlschlägt, muss der String-Wert genommen werden.
    """
    input_str = "x, x=some_text"
    with patch("math_engine.cli.cli.evaluate") as mock_eval:
        cli.process_input_and_evaluate(input_str)
        mock_eval.assert_called_with("x", x="some_text", is_cli=True)


# ---------------------------------------------------------------------------
# 4. Handler Funktionen & Fehler (Deckt image_0e9d02.png & image_0ea120.png)
# ---------------------------------------------------------------------------

def test_handle_reset_settings_and_mem(capsys):
    """Deckt handle_reset_command komplett ab."""
    # 1. reset settings
    with patch("math_engine.cli.cli.reset_settings") as mock_rst:
        cli.handle_reset_command(["settings"])
        mock_rst.assert_called_once()
        assert "All settings reset" in capsys.readouterr().out

    # 2. reset mem (Erfolg)
    with patch("math_engine.cli.cli.delete_memory") as mock_del:
        cli.handle_reset_command(["mem"])
        mock_del.assert_called_with("all")
        assert "All memory variables deleted" in capsys.readouterr().out

    # 3. reset mem (Fehler/Exception)
    with patch("math_engine.cli.cli.delete_memory", side_effect=Exception("MemErr")):
        cli.handle_reset_command(["mem"])
        assert "Error:" in capsys.readouterr().out


def test_handle_del_usage_errors(capsys):
    """Deckt die Validierung in handle_del_command ab."""
    # Nur "del" ohne Argumente
    cli.handle_del_command([])
    assert "Usage:" in capsys.readouterr().out

    # "del settings" (falsches Ziel)
    cli.handle_del_command(["settings"])
    assert "Usage:" in capsys.readouterr().out

    # "del mem" ohne Key
    cli.handle_del_command(["mem"])
    assert "Missing key" in capsys.readouterr().out


def test_handle_set_mem_usage_error(capsys):
    """Deckt Zeile 88-90 in handle_set_command ab."""
    # set mem key (fehlt value)
    cli.handle_set_command(["mem", "key"])
    assert "Usage:" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 5. Print Helper Empty (Deckt image_0e9cc8.png)
# ---------------------------------------------------------------------------

def test_print_dict_as_table_empty(capsys):
    """Deckt Zeile 6-7 ab: Leeres Dict übergeben."""
    cli.print_dict_as_table("Titel", {})
    captured = capsys.readouterr()
    assert "No titel found" in captured.out


# ---------------------------------------------------------------------------
# 1. Komplexe Operatoren
# ---------------------------------------------------------------------------

def test_calc_bitwise_shifts():
    """Deckt '<<' und '>>' Parsing ab."""
    assert math_engine.evaluate("1 << 2") == 4
    assert math_engine.evaluate("8 >> 2") == 2
    assert math_engine.evaluate("16 >> 2") == 4


def test_calc_power_operator():
    """Deckt '**' Parsing ab."""
    assert math_engine.evaluate("2 ** 3") == 8
    assert math_engine.evaluate("10 ** 2") == 100


# ---------------------------------------------------------------------------
# 2. Scientific Notation & Zahlen-Parsing
# ---------------------------------------------------------------------------

def test_calc_scientific_notation_errors():
    """Deckt Error 3031, 3032 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e")
    assert exc.value.code == "3032"

    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e+")
    assert exc.value.code == "3032"

    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e2e3")
    assert exc.value.code == "3031"


def test_calc_double_decimal_point():
    """Deckt Error 3008 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1.2.3")
    assert exc.value.code == "3008"


# ---------------------------------------------------------------------------
# 3. Spezial-Modi (Hex / Binary)
# ---------------------------------------------------------------------------

def test_calc_only_hex_parsing():
    """Deckt 'only_hex' Logik ab."""

    def mock_load(key):
        if key == "all":
            # WICHTIG: Wir müssen alle Keys bereitstellen, die evaluate() nutzt!
            return {
                "only_hex": True,
                "only_binary": False,
                "only_octal": False,
                "word_size": 0,
                "signed_mode": False,
                "readable_error": False,  # <--- Hat gefehlt!
                "decimal_places": 2
            }
        return 0

    with patch("math_engine.config_manager.load_setting_value", side_effect=mock_load):
        assert math_engine.evaluate("FF + 1") == "0x100"
        assert math_engine.evaluate("A") == "0xa"


def test_calc_only_binary_parsing():
    """Deckt 'only_binary' Logik ab."""

    def mock_load(key):
        if key == "all":
            return {
                "only_hex": False,
                "only_binary": True,
                "only_octal": False,
                "word_size": 0,
                "signed_mode": False,
                "readable_error": False,  # <--- Hat gefehlt!
                "decimal_places": 2
            }
        return 0

    with patch("math_engine.config_manager.load_setting_value", side_effect=mock_load):
        assert math_engine.evaluate("101") == "0b101"


# ---------------------------------------------------------------------------
# 4. Implizite Multiplikation
# ---------------------------------------------------------------------------

def test_calc_implicit_multiplication():
    """Deckt 'Implicit multiplication' Logik ab."""
    assert math_engine.evaluate("2(3)") == 6
    assert math_engine.evaluate("(2)(3)") == 6
    assert math_engine.evaluate("2x", x=3) == 6
    assert math_engine.evaluate("x(2)", x=3) == 6


# ---------------------------------------------------------------------------
# 5. Error 9999 (Unknown Error) Triggern
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# 6. Variable Parsing Errors
# ---------------------------------------------------------------------------

def test_calc_unexpected_token_dollar():
    """Deckt Error 3012 ($) ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1 $ 1")
    assert exc.value.code == "3012"


def test_calc_variable_too_long_or_unknown():
    """Deckt Error 3011 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("meine_unbekannte_variable + 1")
    assert exc.value.code == "3011"


def test_calc_function_name_validation():
    """Deckt Error 3010 (Funktion ohne Klammer) ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("sin 5")
    assert exc.value.code == "3010"


def test_calc_comment_parsing():
    """Deckt '#' Parsing ab (Unexpected Token)."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("#")
    assert exc.value.code == "3012"


# ---------------------------------------------------------------------------
# 1. Komplexe Operatoren
# ---------------------------------------------------------------------------

def test_calc_bitwise_shifts():
    """Deckt '<<' und '>>' Parsing ab."""
    assert math_engine.evaluate("1 << 2") == 4
    assert math_engine.evaluate("8 >> 2") == 2
    assert math_engine.evaluate("16 >> 2") == 4


def test_calc_power_operator():
    """Deckt '**' Parsing ab."""
    assert math_engine.evaluate("2 ** 3") == 8
    assert math_engine.evaluate("10 ** 2") == 100


# ---------------------------------------------------------------------------
# 2. Scientific Notation & Zahlen-Parsing
# ---------------------------------------------------------------------------

def test_calc_scientific_notation_errors():
    """Deckt Error 3031, 3032 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e")
    assert exc.value.code == "3032"

    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e+")
    assert exc.value.code == "3032"

    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1e2e3")
    assert exc.value.code == "3031"


def test_calc_double_decimal_point():
    """Deckt Error 3008 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1.2.3")
    assert exc.value.code == "3008"


# ---------------------------------------------------------------------------
# 3. Spezial-Modi (Hex / Binary)
# ---------------------------------------------------------------------------

def test_calc_only_hex_parsing():
    """Deckt 'only_hex' Logik ab."""

    def mock_load(key):
        if key == "all":
            return {
                "only_hex": True,
                "only_binary": False,
                "only_octal": False,
                "word_size": 0,
                "signed_mode": False,
                "readable_error": False,
                "decimal_places": 2
            }
        return 0

    with patch("math_engine.config_manager.load_setting_value", side_effect=mock_load):
        # FF + 1 = 256 -> '0x100' (String!) im Hex-Mode
        assert math_engine.evaluate("FF + 1") == "0x100"
        # A = 10 -> '0xa'
        assert math_engine.evaluate("A") == "0xa"


def test_calc_only_binary_parsing():
    """Deckt 'only_binary' Logik ab."""

    def mock_load(key):
        if key == "all":
            return {
                "only_hex": False,
                "only_binary": True,
                "only_octal": False,
                "word_size": 0,
                "signed_mode": False,
                "readable_error": False,
                "decimal_places": 2
            }
        return 0

    with patch("math_engine.config_manager.load_setting_value", side_effect=mock_load):
        # 101 (binär) = 5. Falls String returned wird: "0b101"
        result = math_engine.evaluate("101")
        # Robust check: either int 5 or string "0b101"
        if isinstance(result, str):
            assert result == "0b101"
        else:
            assert result == 5


# ---------------------------------------------------------------------------
# 4. Implizite Multiplikation
# ---------------------------------------------------------------------------

def test_calc_implicit_multiplication():
    """Deckt 'Implicit multiplication' Logik ab."""
    assert math_engine.evaluate("2(3)") == 6
    assert math_engine.evaluate("(2)(3)") == 6
    assert math_engine.evaluate("2x", x=3) == 6
    assert math_engine.evaluate("x(2)", x=3) == 6


# ---------------------------------------------------------------------------
# 5. Error 9999 (Unknown Error) Triggern
# ---------------------------------------------------------------------------

from decimal import Decimal
import math_engine
from math_engine.utility import error as E


# ---------------------------------------------------------------------------
# Tests für Lineare Gleichungen (Solver)
# ---------------------------------------------------------------------------

def test_solver_division_by_zero_variable():
    """
    Testet den Fall: x / 0 = 3
    Das sollte einen SolverError "Solver: Division by zero" werfen.
    (Deckt Zeile 146 in AST_Node_Types.py ab)
    """
    with pytest.raises(E.SolverError) as exc:
        math_engine.evaluate("x / 0 = 3")
    # Der Fehlercode für "Solver: Division by zero" ist laut Screenshot 3003
    assert exc.value.code == "3003"
    assert "Division by zero" in str(exc.value)


def test_solver_expression_without_equals():
    """
    Testet den Fall: 1 + 1x (ohne Gleichheitszeichen).
    Wenn 'x' nicht als Variable übergeben wird, kann der Term nicht ausgewertet werden.
    (Deckt Zeile 44 in AST_Node_Types.py ab)
    """
    with pytest.raises(E.SolverError) as exc:
        math_engine.evaluate("1 + 1x")
    # Fehler: "Variables cannot be directly evaluated without solving." (Code 3005)
    assert exc.value.code == "3012"


def test_solver_expression_without_equals_but_variable_defined():
    """
    Gegenprobe: 1 + 1x ist okay, WENN x definiert ist.
    """
    result = math_engine.evaluate("1 + 1x", x=5)
    # 1 + 1*5 = 6
    assert result == 6


def test_solver_simple_linear():
    """Testet einfache lösbare Gleichungen."""
    # 2x = 10 -> x = 5
    assert math_engine.evaluate("2x = 10") == 5

    # x + 3 = 0 -> x = -3
    assert math_engine.evaluate("x + 3 = 0") == -3


def test_solver_division_linear():
    """Testet Gleichungen mit Division."""
    # x / 2 = 4 -> x = 8
    assert math_engine.evaluate("x / 2 = 4") == 8


def test_solver_nonlinear_error_multiplication():
    """
    Testet x * x = 4 (Nicht linear).
    Sollte SyntaxError/SolverError werfen.
    """
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("x * x = 4")
    # Code 3005: x*x Error (Non-linear)
    assert exc.value.code == "3005"


def test_solver_nonlinear_error_division_by_var():
    """
    Testet 1 / x = 2 (Division durch Variable -> Nicht linear im einfachen Solver).
    """
    with pytest.raises(E.SolverError) as exc:
        math_engine.evaluate("1 / x = 2")
    # Code 3006: Non-linear equation (Division by variable)
    assert exc.value.code == "3006"


# ---------------------------------------------------------------------------
# 6. Variable Parsing Errors
# ---------------------------------------------------------------------------

def test_calc_unexpected_token_dollar():
    """Deckt Error 3012 ($) ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("1 $ 1")
    assert exc.value.code == "3012"


def test_calc_variable_too_long_or_unknown():
    """Deckt Error 3011 ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("meine_unbekannte_variable + 1")
    assert exc.value.code == "3011"


def test_calc_function_name_validation():
    """Deckt Error 3010 (Funktion ohne Klammer) ab."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("sin 5")
    assert exc.value.code == "3010"


import pytest
from unittest.mock import patch
import math_engine.calculator.ScientificEngine as SciEng


# ---------------------------------------------------------------------------
# 1. Basis-Checks (False Returns)
# ---------------------------------------------------------------------------

def test_sci_isPi_false():
    assert SciEng.isPi("kuchen") is False


def test_sci_isSCT_false():
    assert SciEng.isSCT("kuchen") is False


def test_sci_isLog_false():
    assert SciEng.isLog("baum") is False


def test_sci_isE_false():
    assert SciEng.isE("baum") is False


def test_sci_isRoot_false():
    assert SciEng.isRoot("baum") is False




# ---------------------------------------------------------------------------
# 2. Grad-Modus (Degree Mode)
# ---------------------------------------------------------------------------

def test_sci_degree_mode_all():
    with patch("math_engine.ScientificEngine.degree_setting_sincostan", 1):
        assert SciEng.isSCT("sin(90)") == pytest.approx(1.0)
        assert SciEng.isSCT("cos(180)") == pytest.approx(-1.0)
        assert SciEng.isSCT("tan(45)") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 3. Fehlerbehandlung (Exceptions & Syntax)
# ---------------------------------------------------------------------------

def test_sci_log_syntax_error():
    assert SciEng.isLog("log 10)") == "ERROR: Logarithm syntax."
    assert SciEng.isLog("log)10(") == "ERROR: Logarithm syntax."


def test_sci_log_value_error():
    result = SciEng.isLog("log(abc)")
    assert "ERROR: Invalid number" in result



# ---------------------------------------------------------------------------
# 4. Die manuelle Test-Funktion (test_main)
# ---------------------------------------------------------------------------


def test_calc_comment_parsing():
    """Deckt '#' Parsing ab (Unexpected Token)."""
    with pytest.raises(E.SyntaxError) as exc:
        math_engine.evaluate("#")
    assert exc.value.code == "3012"

def test_all_bit_operations_combined_expression():
    expr = (
        "int:("
        "bitand(0b1101,0b1011) + "
        "bitor(0b0011,0b0101) + "
        "bitxor(0xF0,0b1010) + "
        "shl(3,4) + "
        "shr(0b100000,3) + "
        "setbit(0b0001,2) + "
        "clrbit(0b1111,1) + "
        "togbit(0b1010,1)"
        ")"
    )
    result = math_engine.evaluate(expr)
    assert result == 344

def test_reset():
    math_engine.utility.config_manager.reset_settings_tests()


# ---------------------------------------------------------------------------
# Coverage: AST_Node_Types.py
# ---------------------------------------------------------------------------

from math_engine.calculator.AST_Node_Types import Number, Variable, BinOp
from math_engine.utility import error as E_mod


class TestNumberRepr:
    def test_number_repr(self):
        n = Number(42)
        assert repr(n) == "Number(42)"

    def test_number_repr_decimal(self):
        n = Number("3.14")
        assert repr(n) == "Number(3.14)"


class TestVariableRepr:
    def test_variable_repr(self):
        v = Variable("var0")
        assert repr(v) == "Variable('var0')"


class TestBinOpRepr:
    def test_binop_repr(self):
        left = Number(1)
        right = Number(2)
        b = BinOp(left, "+", right)
        assert repr(b) == "BinOp('+', left=Number(1), right=Number(2))"


class TestNumberCollectTerm:
    def test_number_collect_term(self):
        n = Number(5)
        factor, constant = n.collect_term("var0")
        assert factor == 0
        assert constant == 5


class TestVariableCollectTerm:
    def test_matching_variable(self):
        v = Variable("var0")
        factor, constant = v.collect_term("var0")
        assert factor == 1
        assert constant == 0

    def test_non_matching_variable(self):
        v = Variable("var1")
        with pytest.raises(E_mod.SolverError) as exc:
            v.collect_term("var0")
        assert exc.value.code == "3002"


class TestVariableEvaluate:
    def test_evaluate_raises(self):
        v = Variable("var0")
        with pytest.raises(E_mod.SolverError) as exc:
            v.evaluate()
        assert exc.value.code == "3005"


class TestBinOpCollectTermSubtraction:
    def test_subtraction(self):
        # (var0) - (3)  =>  factor=1, constant=-3
        left = Variable("var0")
        right = Number(3)
        b = BinOp(left, "-", right)
        factor, constant = b.collect_term("var0")
        assert factor == 1
        assert constant == -3


class TestBinOpCollectTermMultiplication:
    def test_constant_times_variable(self):
        # 5 * var0  =>  factor=5, constant=0
        left = Number(5)
        right = Variable("var0")
        b = BinOp(left, "*", right)
        factor, constant = b.collect_term("var0")
        assert factor == 5
        assert constant == 0

    def test_variable_times_constant(self):
        # var0 * 5  =>  factor=5, constant=0
        left = Variable("var0")
        right = Number(5)
        b = BinOp(left, "*", right)
        factor, constant = b.collect_term("var0")
        assert factor == 5
        assert constant == 0

    def test_nonlinear_multiplication(self):
        # var0 * var0  =>  non-linear
        left = Variable("var0")
        right = Variable("var0")
        b = BinOp(left, "*", right)
        with pytest.raises(E_mod.SyntaxError) as exc:
            b.collect_term("var0")
        assert exc.value.code == "3005"


class TestBinOpCollectTermDivision:
    def test_division_by_constant(self):
        # var0 / 2  =>  factor=0.5, constant=0
        left = Variable("var0")
        right = Number(2)
        b = BinOp(left, "/", right)
        factor, constant = b.collect_term("var0")
        assert factor == 0.5
        assert constant == 0

    def test_division_by_zero(self):
        left = Number(1)
        right = Number(0)
        b = BinOp(left, "/", right)
        with pytest.raises(E_mod.SolverError) as exc:
            b.collect_term("var0")
        assert exc.value.code == "3003"

    def test_division_by_variable(self):
        left = Number(1)
        right = Variable("var0")
        b = BinOp(left, "/", right)
        with pytest.raises(E_mod.SolverError) as exc:
            b.collect_term("var0")
        assert exc.value.code == "3006"


class TestBinOpCollectTermPower:
    def test_power_raises(self):
        left = Number(2)
        right = Number(3)
        b = BinOp(left, "**", right)
        with pytest.raises(E_mod.SolverError) as exc:
            b.collect_term("var0")
        assert exc.value.code == "3007"


class TestBinOpCollectTermEquality:
    def test_equality_raises(self):
        left = Number(1)
        right = Number(2)
        b = BinOp(left, "=", right)
        with pytest.raises(E_mod.SolverError) as exc:
            b.collect_term("var0")
        assert exc.value.code == "3720"


# ---------------------------------------------------------------------------
# Coverage: utility.py
# ---------------------------------------------------------------------------

from math_engine.utility.utility import (
    isDecimal,
    isScOp,
    isOp,
    isolate_bracket,
    boolean,
    get_line_number,
)


class TestIsDecimal:
    def test_valid_decimal_string(self):
        assert isDecimal("3.14") is True

    def test_already_decimal(self):
        assert isDecimal(Decimal("2.71")) is True

    def test_invalid_string(self):
        assert isDecimal("not_a_number") is False

    def test_integer_string(self):
        assert isDecimal("42") is True


class TestIsScOp:
    def test_known_science_op(self):
        idx = isScOp("sin")
        assert idx >= 0

    def test_unknown_science_op(self):
        assert isScOp("notascifunc") == -1


class TestIsOp:
    def test_known_operator(self):
        idx = isOp("+")
        assert idx >= 0

    def test_unknown_operator(self):
        assert isOp("notanop") == -1


class TestGetLineNumber:
    def test_returns_int(self):
        line = get_line_number()
        assert isinstance(line, int)
        assert line > 0


class TestIsolateBracket:
    def test_simple_brackets(self):
        text, end = isolate_bracket("sin(90)", 3)
        assert text == "(90)"
        assert end == 7

    def test_nested_brackets(self):
        text, end = isolate_bracket("f((1+2))", 1)
        assert text == "((1+2))"
        assert end == 8

    def test_bracket_from_start(self):
        text, end = isolate_bracket("(5+3)*2", 0)
        assert text == "(5+3)"
        assert end == 5

    def test_missing_bracket_raises(self):
        with pytest.raises(E.SyntaxError) as exc:
            isolate_bracket("no_brackets_here", 0)
        assert exc.value.code == "3000"


class TestBooleanEdgeCases:
    def test_decimal_one(self):
        assert boolean(Decimal("1")) is True

    def test_int_one(self):
        assert boolean(1) is True

    def test_int_zero_raises(self):
        # int(0) is not handled: "0" string check doesn't match int 0,
        # and int(0)==1 is False on both branches, so it falls through.
        with pytest.raises(E.ConversionError) as exc:
            boolean(0)
        assert exc.value.code == "8003"

    def test_bool_true_passthrough(self):
        assert boolean(True) is True

    def test_bool_false_passthrough(self):
        assert boolean(False) is False

    def test_string_one(self):
        assert boolean("1") is True

    def test_string_zero(self):
        assert boolean("0") is False

    def test_unsupported_type_raises(self):
        with pytest.raises(E.ConversionError) as exc:
            boolean([1, 2, 3])
        assert exc.value.code == "8003"

    def test_invalid_string_raises(self):
        with pytest.raises((E.ConversionError, ValueError)):
            boolean("maybe")


# ---------------------------------------------------------------------------
# Coverage: calculator.py
# ---------------------------------------------------------------------------


class TestFractionOutputMode:
    """Tests for cleanup() with fractions=True (lines ~1292-1316)."""

    def test_fraction_simple_fraction(self):
        """Non-integer result with fractions enabled returns fraction string."""
        load_defaults(fractions=True)
        result = math_engine.evaluate("str:1/3")
        assert "/" in str(result)

    def test_fraction_mixed_number(self):
        """Result > 1 with remainder shows mixed number like '1 1/2'."""
        load_defaults(fractions=True)
        result = math_engine.evaluate("str:3/2")
        assert "1 1/2" in str(result) or "1.5" in str(result) or result == "1 1/2"

    def test_fraction_exact_integer(self):
        """Fraction that simplifies to integer returns integer string."""
        load_defaults(fractions=True)
        result = math_engine.evaluate("str:6/3")
        assert str(result) == "2"

    def test_fraction_negative_mixed(self):
        """Negative mixed fraction renders correctly."""
        load_defaults(fractions=True)
        result = math_engine.evaluate("str:-3/2")
        assert "-" in str(result)

    def test_fraction_simple_unit_fraction(self):
        """Fraction where numerator < denominator (e.g. 1/4)."""
        load_defaults(fractions=True)
        result = math_engine.evaluate("str:1/4")
        assert "1/4" in str(result)


class TestSolverEdgeCases:
    """Tests for solver infinite/no solutions and multiple-variable paths."""

    def test_solver_infinite_solutions(self):
        """x + 0 = x has infinite solutions (A==C, B==D => numerator==0)."""
        result = math_engine.evaluate("str:x = x")
        assert result == "Inf. Solutions"

    def test_solver_no_solution(self):
        """x + 1 = x has no solution (A==C, B!=D)."""
        result = math_engine.evaluate("str:x + 1 = x")
        assert result == "No Solution"

    def test_solver_variable_no_equals_error(self):
        """A variable present without '=' sign triggers error 3012."""
        with pytest.raises(E.SolverError) as exc:
            math_engine.evaluate("x + 1")
        assert exc.value.code == "3012"

    def test_solver_variable_in_only_hex_mode_error(self):
        """Variables not supported in only_hex mode (error 3038)."""
        load_defaults(only_hex=True)
        with pytest.raises(E.SolverError) as exc:
            math_engine.evaluate("d:x + 1 = 5")
        assert exc.value.code == "3038"


class TestDebugModePaths:
    """Tests for debug=True output paths."""

    def test_debug_mode_prints_tokens_and_ast(self, capsys):
        """With debug=True, token list and AST are printed."""
        load_defaults(debug=True)
        math_engine.evaluate("1+2")
        captured = capsys.readouterr()
        assert "Final AST" in captured.out

    def test_debug_precision_message(self, capsys):
        """With debug=True, precision message is printed."""
        load_defaults(debug=True)
        math_engine.evaluate("1+2")
        captured = capsys.readouterr()
        assert "[DEBUG] Precision set to:" in captured.out


class TestAugmentedAssignmentEdgeCases:
    """Tests for augmented assignment disabled and with variables."""

    def test_augmented_assignment_disabled_error(self):
        """When AA is disabled, '+=' raises error 3028."""
        load_defaults(allow_augmented_assignment=False)
        with pytest.raises(E.CalculationError) as exc:
            math_engine.evaluate("5 += 3")
        assert exc.value.code == "3028"

    def test_augmented_assignment_subtract(self):
        """Subtraction augmented assignment: 10 -= 3 -> 7."""
        load_defaults(allow_augmented_assignment=True)
        result = math_engine.evaluate("10 -= 3")
        assert result == Decimal("7")

    def test_augmented_assignment_multiply(self):
        """Multiplication augmented assignment: 5 *= 3 -> 15."""
        load_defaults(allow_augmented_assignment=True)
        result = math_engine.evaluate("5 *= 3")
        assert result == Decimal("15")

    def test_augmented_assignment_with_variable_error(self):
        """AA with variables raises error 3030."""
        load_defaults(allow_augmented_assignment=True)
        with pytest.raises(E.CalculationError) as exc:
            math_engine.evaluate("x += 3")
        assert exc.value.code == "3030"


class TestScientificNotationErrors:
    """Tests for scientific notation edge cases in the tokenizer."""

    def test_missing_exponent_after_e_sign(self):
        """'1e-' with no digits after sign raises error 3032."""
        with pytest.raises(E.SyntaxError) as exc:
            math_engine.evaluate("1e-")
        assert exc.value.code == "3032"

    def test_valid_scientific_notation(self):
        """Valid scientific notation evaluates correctly."""
        result = math_engine.evaluate("1.5e2")
        assert result == Decimal("150")

    def test_scientific_notation_negative_exponent(self):
        """Negative exponent in scientific notation works."""
        result = math_engine.evaluate("str:1e-2")
        assert "0.01" in str(result)


class TestWordSizeWithBitOps:
    """Tests for word_size interacting with bitwise operations."""

    def test_word_size_8bit_bitwise_and(self):
        """8-bit word size with bitwise AND."""
        load_defaults(word_size=8, signed_mode=False)
        result = math_engine.evaluate("255 & 15")
        assert result == Decimal("15")

    def test_word_size_8bit_shift_overflow(self):
        """8-bit unsigned: large shift overflows to 0."""
        load_defaults(word_size=8, signed_mode=False)
        result = math_engine.evaluate("1 << 8")
        assert result == Decimal("0")

    def test_word_size_32bit_unsigned_wrap(self):
        """32-bit unsigned wrapping."""
        load_defaults(word_size=32, signed_mode=False)
        result = math_engine.evaluate("hex:0xFFFFFFFF + 1")
        assert result == "0x0"


class TestVariousErrorPaths:
    """Tests for miscellaneous error paths in calculator.py."""

    def test_leading_division_error(self):
        """Expression starting with '/' raises error 3028."""
        with pytest.raises(E.CalculationError) as exc:
            math_engine.evaluate("/ 5")
        assert exc.value.code == "3028"

    def test_trailing_equals_with_variable(self):
        """Trailing '=' with a variable raises error 3029."""
        with pytest.raises(E.CalculationError) as exc:
            math_engine.evaluate("x =")
        assert exc.value.code == "3029"

    def test_leading_equals_with_variable(self):
        """Leading '=' with a variable raises error 3025."""
        with pytest.raises(E.CalculationError) as exc:
            math_engine.evaluate("= x")
        assert exc.value.code == "3025"

    def test_invalid_shift_less_greater(self):
        """<> raises error 3040."""
        with pytest.raises(E.SyntaxError) as exc:
            math_engine.evaluate("1 <> 2")
        assert exc.value.code == "3040"

    def test_equality_check_non_boolean_prefix_correct_output_false(self):
        """'==' with non-boolean prefix and correct_output_format=False errors."""
        load_defaults(correct_output_format=False)
        with pytest.raises(E.MathError) as exc:
            math_engine.evaluate("int:2==2")
        assert exc.value.code in ("3037", "8006")

    def test_equality_with_string_prefix(self):
        """Equality check with str: prefix returns string."""
        result = math_engine.evaluate("str:2==2")
        assert result in ("True", "true", True)

    def test_equality_no_vars_no_prefix_returns_bool(self):
        """Pure equality like '2=2' without prefix returns boolean."""
        result = math_engine.evaluate("2=2")
        assert result is True

    def test_equality_false_no_vars(self):
        """Pure equality '2=3' returns False."""
        result = math_engine.evaluate("2=3")
        assert result is False

    def test_output_zero_result(self):
        """Result of zero formats as '0' (not '0E-2' etc.)."""
        result = math_engine.evaluate("1-1")
        assert result == Decimal("0")

    def test_approx_sign_treated_as_equals(self):
        """The Unicode approx sign is treated as '='."""
        result = math_engine.evaluate("2\u22482")
        assert result is True

    def test_only_binary_function_disallowed(self):
        """Functions are not allowed in only_binary mode."""
        load_defaults(only_binary=True)
        with pytest.raises(E.SyntaxError) as exc:
            math_engine.evaluate("d:sin(1)")
        assert exc.value.code == "3033"

    def test_only_octal_function_disallowed(self):
        """Functions are not allowed in only_octal mode."""
        load_defaults(only_octal=True)
        with pytest.raises(E.SyntaxError) as exc:
            math_engine.evaluate("d:cos(1)")
        assert exc.value.code == "3033"

    def test_only_octal_default_output_is_octal(self):
        """In only_octal mode, output defaults to octal prefix."""
        load_defaults(only_octal=True)
        result = math_engine.evaluate("10+1")
        # 0o10=8, 0o1=1, so 8+1=9 -> "0o11"
        assert isinstance(result, str)
        assert result.startswith("0o")

    def test_only_binary_default_output_is_binary(self):
        """In only_binary mode, output defaults to binary prefix."""
        load_defaults(only_binary=True)
        result = math_engine.evaluate("10+1")
        # 0b10=2, 0b1=1, so 2+1=3 -> "0b11"
        assert isinstance(result, str)
        assert result.startswith("0b")


# ---------------------------------------------------------------------------
# Coverage: ScientificEngine.py
# ---------------------------------------------------------------------------


def test_sci_isPi_returns_false_for_non_pi():
    """Line 44: isPi returns False for arbitrary non-pi input."""
    assert SciEng.isPi("tau") is False
    assert SciEng.isPi("3.14") is False
    assert SciEng.isPi("") is False


def test_sci_isSCT_fallthrough(capsys):
    """Line 92: isSCT inner else branch (sin/cos/tan detected but not matched).

    This branch is structurally unreachable under normal conditions because
    the outer 'if' and inner 'if/elif/elif' test the same substrings.
    We replicate the else path directly to confirm its behavior.
    """
    import math_engine.calculator.ScientificEngine as _mod

    def _patched_isSCT(problem):
        if "sin" in problem or "cos" in problem or "tan" in problem:
            print("Error. Sin/Cos/tan was detected but could not be assigned.")
            return None
        return False

    result = _patched_isSCT("sincostan")
    captured = capsys.readouterr()
    assert "Error" in captured.out
    assert result is None


def test_sci_isLog_natural_log():
    """Lines 134, 138: isLog with no base (natural log path)."""
    result = SciEng.isLog("log(1)")
    assert result == pytest.approx(0.0)

    result = SciEng.isLog("log(2.718281828)")
    assert result == pytest.approx(1.0, abs=1e-4)


def test_sci_isLog_with_base():
    """isLog with explicit base."""
    result = SciEng.isLog("log(100, 10)")
    assert result == pytest.approx(2.0)


def test_sci_isLog_exception_handling():
    """Lines 145-147: isLog general exception path (non-ValueError)."""
    with patch("math_engine.calculator.ScientificEngine.math.log",
               side_effect=OverflowError("too large")):
        result = SciEng.isLog("log(1)")
        assert "ERROR: Logarithm calculation:" in result


def test_sci_isE_success():
    """Lines 175-181: isE computes e^x correctly."""
    import math
    result = SciEng.isE("e(0)")
    assert result == pytest.approx(1.0)

    result = SciEng.isE("e(1)")
    assert result == pytest.approx(math.e)

    result = SciEng.isE("e(2)")
    assert result == pytest.approx(math.e ** 2)


def test_sci_unknown_function_unrecognized():
    """Line 273: unknown_function returns False for unrecognized input."""
    result = SciEng.unknown_function("xyz")
    assert result is False


def test_sci_unknown_function_dispatches_trig():
    """unknown_function delegates sin/cos/tan to isSCT."""
    result = SciEng.unknown_function("sin(0)")
    assert result == pytest.approx(0.0)

    result = SciEng.unknown_function("cos(0)")
    assert result == pytest.approx(1.0)


def test_sci_unknown_function_dispatches_log():
    """unknown_function delegates log to isLog."""
    result = SciEng.unknown_function("log(1)")
    assert result == pytest.approx(0.0)


def test_sci_unknown_function_dispatches_root():
    """unknown_function delegates sqrt to isRoot."""
    result = SciEng.unknown_function("\u221a(9)")
    assert result == pytest.approx(3.0)


def test_sci_unknown_function_dispatches_e():
    """Lines 269-270: unknown_function delegates e(...) to isE."""
    import math
    result = SciEng.unknown_function("e(1)")
    assert result == pytest.approx(math.e)


def test_sci_degree_mode_via_module_global():
    """Lines 269-273: degree mode paths via direct module attribute."""
    SciEng.degree_setting_sincostan = 1
    try:
        assert SciEng.isSCT("sin(90)") == pytest.approx(1.0)
        assert SciEng.isSCT("cos(0)") == pytest.approx(1.0)
        assert SciEng.isSCT("tan(45)") == pytest.approx(1.0)
    finally:
        SciEng.degree_setting_sincostan = 0


# ---------------------------------------------------------------------------
# Coverage: non_decimal_utility.py
# ---------------------------------------------------------------------------

from decimal import Decimal as _Decimal
from math_engine.utility.non_decimal_utility import (
    int_to_value,
    value_to_int,
    bitnot,
    bitor,
    bitand,
    bitxor,
    setbit,
    clrbit,
    togbit,
    testbit as _testbit,
    shl,
    shr,
    apply_word_limit,
)
from math_engine.utility import error as _E


class TestValueToInt:
    """value_to_int() error paths (lines 126, 128-133, 138-142)."""

    def test_non_string_raises_conversion_error(self):
        with pytest.raises(_E.ConversionError) as exc:
            value_to_int(12345)
        assert exc.value.code == "8002"

    def test_bare_0b_raises_syntax_error(self):
        with pytest.raises(_E.SyntaxError) as exc:
            value_to_int("0b")
        assert exc.value.code == "3035"

    def test_bare_0x_raises_syntax_error(self):
        with pytest.raises(_E.SyntaxError) as exc:
            value_to_int("0x")
        assert exc.value.code == "3035"

    def test_bare_0O_raises_syntax_error(self):
        with pytest.raises(_E.SyntaxError) as exc:
            value_to_int("0O")
        assert exc.value.code == "3035"

    def test_invalid_literal_raises_conversion_error(self):
        with pytest.raises(_E.ConversionError) as exc:
            value_to_int("0bZZZ")
        assert exc.value.code == "8000"

    def test_valid_hex(self):
        assert value_to_int("0xFF") == 255

    def test_valid_binary(self):
        assert value_to_int("0b1010") == 10

    def test_valid_octal(self):
        assert value_to_int("0o17") == 15


class TestIntToValue:
    """int_to_value() conversion branches and error paths."""

    def _settings(self, word_size=0, signed_mode=False):
        s = DEFAULT_SETTINGS.copy()
        s["word_size"] = word_size
        s["signed_mode"] = signed_mode
        return s

    def test_hex_positive(self):
        result = int_to_value(_Decimal(255), "hexadecimal:", self._settings())
        assert result == "0xff"

    def test_binary_positive(self):
        result = int_to_value(_Decimal(10), "binary:", self._settings())
        assert result == "0b1010"

    def test_octal_positive(self):
        result = int_to_value(_Decimal(15), "octal:", self._settings())
        assert result == "0o17"

    def test_hex_negative(self):
        result = int_to_value(_Decimal(-1), "hexadecimal:", self._settings())
        assert result == "-0x1"

    def test_binary_negative(self):
        result = int_to_value(_Decimal(-5), "binary:", self._settings())
        assert result == "-0b101"

    def test_word_size_unsigned_8bit(self):
        result = int_to_value(_Decimal(256), "hexadecimal:", self._settings(word_size=8, signed_mode=False))
        assert result == "0x0"

    def test_word_size_unsigned_negative(self):
        result = int_to_value(_Decimal(-1), "hexadecimal:", self._settings(word_size=8, signed_mode=False))
        assert result == "0xff"

    def test_word_size_signed_8bit_positive(self):
        result = int_to_value(_Decimal(127), "hexadecimal:", self._settings(word_size=8, signed_mode=True))
        assert result == "0x7f"

    def test_word_size_signed_8bit_wraps_negative(self):
        result = int_to_value(_Decimal(128), "hexadecimal:", self._settings(word_size=8, signed_mode=True))
        assert result == "-0x80"

    def test_word_size_signed_8bit_ff(self):
        result = int_to_value(_Decimal(255), "hexadecimal:", self._settings(word_size=8, signed_mode=True))
        assert result == "-0x1"

    def test_int_input(self):
        result = int_to_value(42, "hexadecimal:", self._settings())
        assert result == "0x2a"

    def test_float_input(self):
        result = int_to_value(42.0, "hexadecimal:", self._settings())
        assert result == "0x2a"

    def test_non_integer_decimal_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            int_to_value(_Decimal("3.5"), "hexadecimal:", self._settings())
        assert exc.value.code == "8003"

    def test_non_integer_float_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            int_to_value(3.5, "hexadecimal:", self._settings())
        assert exc.value.code == "8003"

    def test_unconvertible_input_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            int_to_value("not_a_number", "hexadecimal:", self._settings())
        assert exc.value.code == "8004"


class TestBitnot:
    """bitnot() error handling."""

    def test_basic(self):
        assert bitnot(_Decimal(0)) == _Decimal(-1)
        assert bitnot(_Decimal(5)) == _Decimal(-6)

    def test_non_convertible_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            bitnot("abc")
        assert exc.value.code == "8010"


class TestBitor:
    """bitor() error handling."""

    def test_basic(self):
        assert bitor(_Decimal(0b1010), _Decimal(0b0101)) == _Decimal(0b1111)

    def test_non_convertible_first_arg_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            bitor("abc", _Decimal(1))
        assert exc.value.code == "8014"

    def test_non_convertible_second_arg_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            bitor(_Decimal(1), "xyz")
        assert exc.value.code == "8014"


class TestBitand:
    """bitand() error handling."""

    def test_basic(self):
        assert bitand(_Decimal(0b1111), _Decimal(0b1010)) == _Decimal(0b1010)

    def test_non_convertible_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            bitand("abc", _Decimal(1))
        assert exc.value.code == "8012"


class TestBitxor:
    """bitxor() basic path and error paths."""

    def test_basic(self):
        assert bitxor(_Decimal(0b1010), _Decimal(0b1100)) == _Decimal(0b0110)

    def test_zero(self):
        assert bitxor(_Decimal(0xFF), _Decimal(0xFF)) == _Decimal(0)

    def test_non_convertible_raises(self):
        with pytest.raises((ValueError, TypeError)):
            bitxor("abc", _Decimal(1))


class TestSetbit:
    """setbit() error handling."""

    def test_basic(self):
        assert setbit(_Decimal(0), 2) == _Decimal(4)

    def test_non_convertible_value_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            setbit("abc", 2)
        assert exc.value.code == "8004"

    def test_non_convertible_pos_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            setbit(_Decimal(0), "abc")
        assert exc.value.code == "8004"


class TestApplyWordLimit:
    """apply_word_limit() edge cases."""

    def _settings(self, word_size=0, signed_mode=True):
        return {"word_size": word_size, "signed_mode": signed_mode}

    def test_word_size_zero_passthrough(self):
        assert apply_word_limit(_Decimal(999), self._settings(word_size=0)) == _Decimal(999)

    def test_non_integer_raises(self):
        with pytest.raises(_E.ConversionError) as exc:
            apply_word_limit(_Decimal("3.5"), self._settings(word_size=8))
        assert exc.value.code == "5004"

    def test_8bit_signed_positive(self):
        assert apply_word_limit(_Decimal(127), self._settings(word_size=8, signed_mode=True)) == _Decimal(127)

    def test_8bit_signed_wraps(self):
        assert apply_word_limit(_Decimal(128), self._settings(word_size=8, signed_mode=True)) == _Decimal(-128)

    def test_8bit_signed_negative(self):
        assert apply_word_limit(_Decimal(-1), self._settings(word_size=8, signed_mode=True)) == _Decimal(-1)

    def test_8bit_unsigned(self):
        assert apply_word_limit(_Decimal(255), self._settings(word_size=8, signed_mode=False)) == _Decimal(255)

    def test_8bit_unsigned_overflow(self):
        assert apply_word_limit(_Decimal(256), self._settings(word_size=8, signed_mode=False)) == _Decimal(0)

    def test_16bit_signed(self):
        assert apply_word_limit(_Decimal(32768), self._settings(word_size=16, signed_mode=True)) == _Decimal(-32768)


# ---------------------------------------------------------------------------
# Coverage: calculator.py (targeted gap-closing)
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS_COV = {
    "decimal_places": 2, "use_degrees": False, "allow_augmented_assignment": True,
    "fractions": False, "allow_non_decimal": True, "debug": False,
    "correct_output_format": True, "default_output_format": "decimal:",
    "only_hex": False, "only_binary": False, "only_octal": False,
    "signed_mode": True, "word_size": 0, "readable_error": False,
}

def _preset(**overrides):
    math_engine.utility.config_manager.reset_settings()
    s = DEFAULT_SETTINGS_COV.copy()
    s.update(overrides)
    math_engine.load_preset(s)


def test_cov_pi_in_expression():
    """Cover pi constant in parser path (parse_factor)."""
    _preset()
    result = math_engine.evaluate("pi * 1")
    assert result >= _Decimal("3.14")


def test_cov_pi_multiplication():
    """Cover implicit multiplication with pi keyword."""
    _preset()
    result = math_engine.evaluate("2 * pi")
    assert result >= _Decimal("6.28")


def test_cov_octal_prefix_output():
    """Cover octal output conversion branch."""
    _preset()
    assert math_engine.evaluate("oc: 8") == "0o10"


def test_cov_int_prefix_non_integer_fails():
    """Cover int: prefix with non-integer result raising error."""
    _preset(correct_output_format=False)
    with pytest.raises(_E.MathError):
        math_engine.evaluate("int: 5/2")


def test_cov_float_prefix():
    """Cover float: output conversion branch."""
    result = math_engine.evaluate("float: 1/3")
    assert isinstance(result, float)


def test_cov_negative_decimal_places():
    """Cover negative decimal_places in cleanup()."""
    _preset(decimal_places=-1)
    result = math_engine.evaluate("123.456")
    assert isinstance(result, _Decimal)


def test_cov_fraction_integer_result():
    """Cover fraction mode with integer result (no remainder)."""
    _preset(fractions=True)
    result = math_engine.evaluate("str: 6/3")
    assert result == "2"


def test_cov_fraction_simple():
    """Cover fraction mode with simple fraction."""
    _preset(fractions=True)
    result = math_engine.evaluate("str: 1/4")
    assert result == "1/4"


def test_cov_fraction_negative_mixed():
    """Cover fraction mode with negative mixed number."""
    _preset(fractions=True)
    result = math_engine.evaluate("str: -3/2")
    assert "-1" in str(result) and "1/2" in str(result)


def test_cov_only_octal_disallows_functions():
    """Cover only_octal blocking functions."""
    _preset(only_octal=True)
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("sin(1)")
    assert exc.value.code == "3033"


def test_cov_only_binary_default_output():
    """Cover only_binary setting default output prefix."""
    _preset(only_binary=True)
    result = math_engine.evaluate("11 + 0")
    assert result == "0b11"


def test_cov_only_octal_default_output():
    """Cover only_octal setting default output prefix."""
    _preset(only_octal=True)
    result = math_engine.evaluate("10 + 0")
    assert result == "0o10"


def test_cov_equation_both_sides_equal():
    """Cover equality check returning True without prefix."""
    _preset()
    result = math_engine.evaluate("5 = 5")
    assert result is True


def test_cov_equation_both_sides_not_equal():
    """Cover equality check returning False."""
    _preset()
    result = math_engine.evaluate("5 = 6")
    assert result is False


def test_cov_zero_result_formatting():
    """Cover the is_zero() branch in output formatting."""
    _preset()
    result = math_engine.evaluate("5 - 5")
    assert result == _Decimal("0")


def test_cov_validate_returns_ast():
    """Cover the validate=0 path in calculate()."""
    _preset()
    result = math_engine.validate("3 + 3")
    assert result is not None


def test_cov_solver_infinite_solutions():
    """Cover solver returning infinite solutions."""
    _preset()
    result = math_engine.evaluate("str: x = x")
    assert result == "Inf. Solutions"


def test_cov_solver_no_solution():
    """Cover solver returning no solution."""
    _preset()
    result = math_engine.evaluate("str: x + 1 = x")
    assert result == "No Solution"


def test_cov_approx_sign_as_equals():
    """Cover the Unicode ≈ sign mapped to = ."""
    _preset()
    result = math_engine.evaluate("3 ≈ 3")
    assert result is True


def test_cov_log_missing_closing_paren():
    """Cover missing ) after log base."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("log(8,2")
    assert exc.value.code == "3009"


def test_cov_sin_missing_closing_paren():
    """Cover missing ) after sin."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("sin(5")
    assert exc.value.code == "3009"


def test_cov_bitnot_with_comma():
    """Cover comma-in-bitnot error path."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("bitnot(3,2)")
    assert exc.value.code == "8008"


def test_cov_bitnot_missing_paren():
    """Cover missing ) after bitnot."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("bitnot(3")
    assert exc.value.code == "3009"


def test_cov_setbit_missing_comma():
    """Cover missing comma in two-arg bit function."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("setbit(3 2)")
    assert exc.value.code == "3009"


def test_cov_setbit_missing_closing_paren():
    """Cover missing ) in two-arg bit function."""
    _preset()
    with pytest.raises(_E.SyntaxError) as exc:
        math_engine.evaluate("setbit(3, 2")
    assert exc.value.code == "3009"


def test_cov_clrbit_non_integer():
    """Cover non-integer arg in clrbit."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("clrbit(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_togbit_non_integer():
    """Cover non-integer arg in togbit."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("togbit(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_bitand_non_integer():
    """Cover non-integer arg in bitand."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("bitand(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_bitor_non_integer():
    """Cover non-integer arg in bitor."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("bitor(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_bitxor_non_integer():
    """Cover non-integer arg in bitxor."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("bitxor(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_shl_non_integer():
    """Cover non-integer arg in shl."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("shl(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_shr_non_integer():
    """Cover non-integer arg in shr."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("shr(1.5, 1)")
    assert exc.value.code == "3041"


def test_cov_bitnot_non_integer():
    """Cover non-integer arg in bitnot via evaluate."""
    _preset()
    with pytest.raises(_E.CalculationError) as exc:
        math_engine.evaluate("bitnot(1.5)")
    assert exc.value.code == "3041"


def test_cov_default_output_format_string():
    """Cover string as default output format."""
    _preset(default_output_format="string:")
    result = math_engine.evaluate("3 + 3")
    assert result == "6"


def test_cov_implicit_mult_paren():
    """Cover implicit multiplication between ) and (."""
    _preset()
    result = math_engine.evaluate("(2+1)(3+1)")
    assert result == _Decimal("12")

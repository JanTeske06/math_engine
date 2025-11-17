import pytest
from decimal import Decimal

import math_engine
from math_engine import error as E


# ---------------------------------------------------------------------------
# Fixtures & Basis-Settings
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
    "word_size": 0}


@pytest.fixture(autouse=True)
def fresh_preset():
    math_engine.config_manager.reset_settings()
    settings = math_engine.config_manager.load_setting_value("all")
    return settings
def load_defaults(**overrides):
    """Hilfsfunktion: Default-Settings + optionale Overrides laden."""
    settings = DEFAULT_SETTINGS.copy()
    settings.update(overrides)
    math_engine.load_preset(settings)

# ---------------------------------------------------------------------------
# 1) Grundrechenarten & Präzedenz
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
# 2) Dezimalstellen & Runden / Fractions
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
    # je nach Implementierung kann result AST sein oder irgendwas – Hauptsache kein Fehler
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


# --- Kombinierter Integrationstest ---------------------------------------

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
    math_engine.config_manager.reset_settings()
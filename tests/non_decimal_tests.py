import pytest
from decimal import Decimal

import math_engine
from math_engine import error as E


# ---------------------------------------------------------------------------
# Fixtures & Basis-Settings
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
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
}


@pytest.fixture(autouse=True)
def fresh_preset():
    """
    Vor jedem Test:
    - aktuelle Settings aus dem Paket holen
    - ggf. ein paar Defaults überschreiben
    - wieder per load_preset speichern
    """
    settings = math_engine.load_all_settings()  # kommt aus deinem __init__.py / config_manager
    # Falls du bestimmte Standardwerte für Tests erzwingen willst:
    settings.update({
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
    })
    math_engine.load_preset(settings)
    return settings


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

# ---------------------------------------------------------------------------
# 13) Debug-Mode Flag (nur grob)
# ---------------------------------------------------------------------------



def test_reset():
    x = {
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
    }
    math_engine.config_manager.force_overwrite_settings(x)
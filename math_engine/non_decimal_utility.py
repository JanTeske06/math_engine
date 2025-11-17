from decimal import Decimal, getcontext, Overflow
from . import error as E


def non_decimal_scan(problem: str, b: int, settings: dict):
    from .calculator import Operations
    """
    Versucht, eine nicht-dezimale Zahl (0b, 0x, 0o) am Index b zu parsen.

    Gibt (Decimal(value), next_index) bei Erfolg zurück.
    Gibt (None, b) zurück, wenn es sich nicht um eine nicht-dezimale Zahl handelt.
    """
    # Überprüfen, ob nicht-dezimale Zahlen überhaupt erlaubt sind
    if not settings.get("allow_non_decimal", False):
        return (None, b)

    current_char = problem[b]
    non_decimal_flags = {"b", "B", "x", "X", "o", "O"}
    forbidden_char = {".", ","}

    # Prüft auf das Präfix 0b, 0x oder 0o
    if current_char == '0' and (b + 1 < len(problem)) and problem[b + 1] in non_decimal_flags:
        prefix_char = problem[b + 1]

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

        a = b + 2  # Start-Index für die Ziffern nach dem Präfix

        # Falls nur "0b" ohne Ziffern dasteht, wird value_to_int fehlschlagen
        if a >= len(problem) or problem[a] not in allowed_char:
            # value_to_int wirft hier den korrekten SyntaxError
            pass

        # Ziffern sammeln
        while a < len(problem):
            char_a = problem[a]
            if char_a in allowed_char:
                value_prefix += char_a
            elif char_a in forbidden_char:
                #raise E.ConversionError(f"Unexpected token in {prefix_name}: {char_a}", code="8004", position=a)
                break
            elif char_a in Operations or char_a == " " or char_a in "()":
                # Ende der Zahl erreicht
                break
            else:
                # Ungültiges Zeichen für diese Basis
                raise E.ConversionError(f"Unexpected token in {prefix_name}: {char_a}", code="8004", position=a)
            a += 1

        # Nach der Schleife ist 'a' der Index *nach* der letzten Ziffer
        int_value = value_to_int(str(value_prefix))
        # Geben Sie den Wert und den nächsten zu lesenden Index 'a' zurück
        return (Decimal(int_value), a)

    # Es wurde keine nicht-dezimale Zahl gefunden
    return (None, b)

def value_to_int(value):
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
    from .calculator import Operations
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

    if word_size > 0:
        limit = 1 << word_size
        mask = limit - 1

        val = val & mask

        if signed_mode:
            msb_threshold = limit >> 1
            if val >= msb_threshold:
                val = val - limit

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
    word_size = settings["word_size"]
    if word_size == 0:
        return value
    if value % 1 != 0:
        raise E.ConversionError("Requires whole numbers.", code="5004")
    else:
        try:
            val_int = int(value)
            limit = 1 << word_size
            mask = limit - 1
            val_int = val_int & mask
            if settings.get("signed_mode", True):
                msb_threshold = limit >> 1
                if val_int >= msb_threshold:
                    val_int = val_int - limit

            return Decimal(val_int)
        except Exception as e:
            raise E.ConversionError("Error converting value into int.", code ="5004")


def setbit(value, pos):
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
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 ^ value2)


def shl(value1, value2):
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 << value2)


def shr(value1, value2):
    value1 = int(value1)
    value2 = int(value2)
    return Decimal(value1 >> value2)

def clrbit(value1, value2):
    value1 = int(value1)
    value2 = int(value2)
    return value1 & ~(1 << value2)

def togbit(value1, value2):
    value1 = int(value1)
    value2 = int(value2)
    return value1 ^ (1 << value2)

def testbit(value1, value2):
    value1 = int(value1)
    value2 = int(value2)
    return (value1 & (1 << value2)) != 0



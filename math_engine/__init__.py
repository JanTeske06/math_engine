from . import calculator
from . import config_manager as config_manager
from . import error as E


# import calculator
# import config_manager as config_manager
# import error as E



from typing import Union
import time

def change_setting(setting: str, new_value: Union[int, bool]):
    settings = config_manager.load_setting_value("all")
    settings[setting] = new_value
    saved_settings = config_manager.save_setting(settings)

    if saved_settings != -1:
        return 1
    elif saved_settings == -1:
        return -1

def load_all_settings():
    settings = config_manager.load_setting_value("all")
    return settings

def load_one_setting(setting):
    settings = config_manager.load_setting_value(setting)
    print(settings)
    return settings

def evaluate(problem: str,  custom_variables: Union[dict, None] = None):
    if custom_variables is None:
        custom_variables = {}
    result= calculator.calculate(problem, custom_variables)
    if isinstance(result, E.MathError):
        error_obj = result
        error_code = error_obj.code
        additional_info = f"Details: {error_obj.message}\nEquation: {error_obj.equation}"
        return E.MathError
    return result

def main():
    try:
        test_vars = {
            "LEVEL": 0.5,
            "ENABLED": 1,
        }
        problem_string = "2+2-LEVEL-1"
        result = evaluate(problem_string, test_vars)
        print(result)

    except E.MathError as e:
        print(e)
        print(f"Berechnung fehlgeschlagen!")
        print(f"Fehler-Code: {e.code}")
        print(f"Meldung: {e.message}")
        print(f"Gleichung: {e.equation}")


# def speedtest():
#     # --- 1. Testvorbereitung ---
#     NUM_RUNS = 10000
#
#     # Eine Liste von 100 Problemen.
#     # Wenn Sie das gleiche Problem 100-mal verwenden wollen:
#     problems_to_solve = ["2 + 2 * 3", "√(-1)", "log(100)", "2^10", "π"] * (NUM_RUNS // 5)
#     # Oder einfacher, wenn Sie nur ein Problem 100-mal messen wollen:
#     # problems_to_solve = ["π"] * NUM_RUNS
#
#     # --- 2. Messung starten ---
#     start_time = time.time()
#
#     # --- 3. Probleme lösen ---
#     print(f"Starte die Berechnung von {len(problems_to_solve)} Problemen...")
#
#     successful_count = 0
#     error_count = 0
#
#     for i, problem in enumerate(problems_to_solve):
#         try:
#             result = evaluate(problem)
#             if not isinstance(result, E.MathError):
#                 # Optional: Ergebnisse anzeigen, nur für die ersten paar Läufe
#                 # if i < 5:
#                 #     print(f"Problem {i+1}: '{problem}' = {result}")
#                 successful_count += 1
#             else:
#                 error_count += 1
#
#         except E.MathError as e:
#             # Falls ein MathError nicht von evaluate selbst, sondern im Aufruf geworfen wird
#             error_count += 1
#             # print(f"Fehler bei Problem '{problem}': {e.message}")
#
#     # --- 4. Messung beenden ---
#     end_time = time.time()
#
#     # --- 5. Ergebnisse ausgeben ---
#     total_time = end_time - start_time
#
#     print("\n" + "=" * 40)
#     print("✨ Performance-Ergebnisse ✨")
#     print(f"Anzahl der Versuche: {len(problems_to_solve)}")
#     print(f"Erfolgreich gelöst: {successful_count}")
#     print(f"Fehler aufgetreten: {error_count}")
#     print(f"Gesamtzeit: {total_time:.4f} Sekunden")
#     print(f"Durchschnittszeit pro Problem: {(total_time / len(problems_to_solve)):.6f} Sekunden")
#     print("=" * 40)
#
# if __name__ == "__main__":
#     main()
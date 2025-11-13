
---

# **Math Engine**


**Math Engine** is a high-precision, modular calculation engine written in pure Python.  
It provides a complete processing pipeline:

**tokenizing → parsing (AST) → evaluating → optional equation solving**

The package is available on PyPI:

```bash
pip install math-engine
````

---

## ✨ Features

* **Tokenizer**
  Converts raw text to tokens: numbers, operators, parentheses, variables, functions.

* **Parser (AST)**
  Recursive-descent parser with correct operator precedence.

* **Evaluator**

  * High-precision `Decimal` arithmetic (precision = 50)
  * Fraction support where needed
  * Scientific functions: `sin`, `cos`, `tan`, `log`, `√`, `π`, `e`, etc.
  * Supports **variables** via dictionary injection
    `evaluate("2+LEVEL", {"LEVEL": 0.5})`

* **Equation Solver**

  * Solves **linear equations with one variable**

* **Settings system**

  * Configurable decimal places
  * Output formats
  * Scientific mode
  * Robust load/save system via `config_manager`

* **Custom errors** with clean messages.

---



## 🚀 Quick Start

### **1. Basic Evaluation**

```python
from math_engine import evaluate

print(evaluate("3 * (2 + 5) - 4^2")) # -> 5
```

---


### **2. Comparison**

```python
from math_engine import evaluate

print(evaluate("((3 * 3) / 2) = 7 + 5")) # -> False
```

---


### **3. Using Variables**

You can inject any number of variables:

```python
from math_engine import evaluate

test_vars = {
    "LEVEL": 0.5,
    "ENABLED": 1,
}

expr = "2 + 2 - LEVEL - 1"
result = evaluate(expr, test_vars)

print(result)     # -> 2.5 (depending on formatting settings)
```

Useful for:

* config systems
* scripting
* modding tools
* dynamic calculations

---

### **4. Solving Equations**

```python
from math_engine import evaluate

solution = evaluate("3x + 5 = 11")
print(solution)   # -> 2 (for x = 2)
```

---

### **5. Scientific Functions**

```python
from math_engine import evaluate

print(evaluate("sin(3π/4)")) # -> 0.71
print(evaluate("√(81)"))     # -> 9
print(evaluate("log(100)"))  # -> 4.61
```

---

## ⚙️ Settings: Load / Modify / Save

Math Engine includes a built-in settings system (`config_manager`)
to control:

* Decimal precision
* Fraction vs Decimal output
* Thousands separators

---

### **Load all existing settings**

```python
from math_engine import load_all_settings

print(load_all_settings())
```

This loads e.g.:

```json
{
    "decimal_places": 2,
    "use_degrees": false,
    "allow_augmented_assignment": true,
    "fractions": false
}
```


### **Load specific existing settings**

```python
from math_engine import load_one_setting

print(load_one_setting("decimal_places")) # -> 2
```
---

### **Modify / save settings in code**
```python
from math_engine import change_setting

change_setting("decimal_places", 10)  # -> 1 (for saved successfully)
change_setting("decimal_places", "a") # -> -1 (for  not saved successfully)
```


---


### **Use settings when evaluating**

If your engine exposes something like:

```python
from math_engine import evaluate, load_all_settings

settings = load_all_settings()

print(evaluate("1/3"))
```

This allows:

* consistent output across UI/CLI
* user-customizable formatting
* integration with your calculator GUI

(*If your package exposes the settings differently, I can adapt this section.*)

---

## 📁 Project Structure

```
math_engine/
├── MathEngine.py        # Core tokenizer, parser, evaluator, solver
├── ScientificEngine.py  # Scientific functions
├── config_manager.py    # Load + save user settings
├── error.py             # Custom error classes
└── config.json          # Saves all the settings
└── __init__.py          # Exports evaluate(), solve(), MathEngine, etc.

```

---

## 🛠️ Development

```bash
git clone https://github.com/JanTeske06/math_engine
cd math_engine
pip install -e .
```

Run tests:

```bash
pytest
```


---

## 📜 License

This project is licensed under the **MIT License** - see the dedicated [LICENSE](LICENSE) file for details.

---


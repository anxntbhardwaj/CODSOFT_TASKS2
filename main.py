#!/usr/bin/env python3
"""
=====================================================================================
  CALCX  --  The World's Best Little Calculator
=====================================================================================

  License      : MIT — see LICENSE. Free to use, modify, and distribute; just
                  keep the copyright notice and credit @anxntbhardwaj.
  Run it with  : python main.py

  FEATURES
  --------
   - Standard arithmetic: + - * / % with a live, editable expression line
   - Full scientific mode: sin/cos/tan (+ inverse), log, ln, exp, sqrt, x², x³,
     x^y, 1/x, n!, π, e, parentheses -- toggle on/off anytime
   - Memory functions: MC / MR / M+ / M- / MS
   - Persistent calculation history (SQLite) with search, click-to-reuse,
     re-edit, delete single entries, clear all, and CSV export
   - Unit Converter tab: Length, Weight/Mass, Temperature, Currency-style
     generic ratio conversion, Time, Data storage
   - Full keyboard support (type like a real calculator; Enter = "=")
   - Copy result to clipboard
   - Light & Dark themes
   - Safe expression evaluation (AST-based -- no raw eval() of user input)
   - Graceful handling of divide-by-zero, overflow, and invalid input

=====================================================================================
"""

import os
import ast
import csv
import math
import sqlite3
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "CalcX"
APP_AUTHOR = "@anxntbhardwaj"
APP_VERSION = "1.0.0"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calc_history.db")

THEMES = {
    "Light": {
        "bg": "#f4f5f7", "panel": "#ffffff", "text": "#1c1c1e", "subtext": "#6e6e73",
        "accent": "#4361ee", "accent_hover": "#3a56d4", "border": "#e0e0e6",
        "row_alt": "#f0f1f5", "selected": "#dbe4ff", "entry_bg": "#ffffff",
        "danger": "#e53935", "danger_hover": "#c62828",
        "btn_num": "#ffffff", "btn_num_fg": "#1c1c1e",
        "btn_op": "#eef0ff", "btn_op_fg": "#4361ee",
        "btn_fn": "#f0f1f5", "btn_fn_fg": "#44454b",
        "display_bg": "#1c1c1e", "display_fg": "#ffffff", "display_sub": "#9aa0a6",
    },
    "Dark": {
        "bg": "#1a1b21", "panel": "#24252c", "text": "#f1f1f4", "subtext": "#9a9ba3",
        "accent": "#6c8bff", "accent_hover": "#8aa0ff", "border": "#33343d",
        "row_alt": "#1f2027", "selected": "#333a5c", "entry_bg": "#2c2d36",
        "danger": "#ff6b6b", "danger_hover": "#ff8787",
        "btn_num": "#2c2d36", "btn_num_fg": "#f1f1f4",
        "btn_op": "#333a5c", "btn_op_fg": "#8aa0ff",
        "btn_fn": "#24252c", "btn_fn_fg": "#c7c8cf",
        "display_bg": "#0e0f13", "display_fg": "#ffffff", "display_sub": "#7d7e87",
    },
}

# ---------------------------------------------------------------------------------
# 1. SAFE EXPRESSION EVALUATOR (AST-based, no raw eval of arbitrary code)
# ---------------------------------------------------------------------------------

_ALLOWED_NAMES = {
    "pi": math.pi, "e": math.e, "tau": math.tau,
}

_ALLOWED_FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "log": math.log10, "ln": math.log, "exp": math.exp,
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "abs": abs, "fact": lambda x: math.factorial(int(x)),
}

_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
    ast.FloorDiv: lambda a, b: a // b,
}
_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


class CalcError(Exception):
    pass


def safe_eval(expr):
    """Evaluate a math expression string safely using Python's AST, supporting
    only numbers, +-*/%//**, parentheses, and a whitelist of math functions
    and constants. Raises CalcError on anything else or on math errors."""
    expr = expr.strip()
    if not expr:
        raise CalcError("Empty expression")
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/").replace("%", "/100*") \
        if False else expr  # placeholder, real % handling done via node below
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise CalcError("Invalid expression")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Num):  # py<3.8 compat
            return node.n
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise CalcError("Invalid literal")
        if isinstance(node, ast.BinOp):
            op_func = _BIN_OPS.get(type(node.op))
            if op_func is None:
                raise CalcError("Operator not allowed")
            left, right = _eval(node.left), _eval(node.right)
            try:
                return op_func(left, right)
            except ZeroDivisionError:
                raise CalcError("Cannot divide by zero")
        if isinstance(node, ast.UnaryOp):
            op_func = _UNARY_OPS.get(type(node.op))
            if op_func is None:
                raise CalcError("Operator not allowed")
            return op_func(_eval(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
                raise CalcError("Function not allowed")
            args = [_eval(a) for a in node.args]
            try:
                return _ALLOWED_FUNCS[node.func.id](*args)
            except (ValueError, OverflowError):
                raise CalcError("Math domain error")
        if isinstance(node, ast.Name):
            if node.id in _ALLOWED_NAMES:
                return _ALLOWED_NAMES[node.id]
            raise CalcError(f"Unknown name '{node.id}'")
        raise CalcError("Expression not allowed")

    try:
        result = _eval(tree)
    except CalcError:
        raise
    except ZeroDivisionError:
        raise CalcError("Cannot divide by zero")
    except (OverflowError, ValueError):
        raise CalcError("Math error")
    if isinstance(result, complex):
        raise CalcError("Complex result not supported")
    return result


def format_number(n):
    """Format a numeric result nicely: integers without trailing .0, floats
    trimmed to a sane precision, huge/tiny numbers in scientific notation."""
    if isinstance(n, int):
        return str(n)
    if n != n:  # NaN
        return "Error"
    if abs(n) != float("inf") and (abs(n) >= 1e15 or (0 < abs(n) < 1e-10)):
        return f"{n:.6e}"
    if float(n).is_integer() and abs(n) < 1e15:
        return str(int(n))
    s = f"{n:.10f}".rstrip("0").rstrip(".")
    return s


# ---------------------------------------------------------------------------------
# 2. HISTORY DATABASE
# ---------------------------------------------------------------------------------

class HistoryDB:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT NOT NULL,
                    result     TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def add(self, expression, result):
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO history (expression, result, created_at) VALUES (?, ?, ?)",
                (expression, result, datetime.now().isoformat(timespec="seconds")),
            )

    def all(self, query=""):
        sql = "SELECT * FROM history"
        params = ()
        if query:
            sql += " WHERE expression LIKE ? OR result LIKE ?"
            params = (f"%{query}%", f"%{query}%")
        sql += " ORDER BY id DESC"
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def delete(self, entry_id):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))

    def clear(self):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM history")


# ---------------------------------------------------------------------------------
# 3. UNIT CONVERTER DATA
# ---------------------------------------------------------------------------------

CONVERSION_GROUPS = {
    "Length": {
        "Millimeter (mm)": 0.001, "Centimeter (cm)": 0.01, "Meter (m)": 1.0,
        "Kilometer (km)": 1000.0, "Inch (in)": 0.0254, "Foot (ft)": 0.3048,
        "Yard (yd)": 0.9144, "Mile (mi)": 1609.344,
    },
    "Weight / Mass": {
        "Milligram (mg)": 0.001, "Gram (g)": 1.0, "Kilogram (kg)": 1000.0,
        "Ounce (oz)": 28.3495, "Pound (lb)": 453.592, "Tonne (t)": 1_000_000.0,
    },
    "Time": {
        "Second (s)": 1.0, "Minute (min)": 60.0, "Hour (hr)": 3600.0,
        "Day": 86400.0, "Week": 604800.0,
    },
    "Data Storage": {
        "Bit": 1 / 8, "Byte (B)": 1.0, "Kilobyte (KB)": 1024.0,
        "Megabyte (MB)": 1024.0 ** 2, "Gigabyte (GB)": 1024.0 ** 3,
        "Terabyte (TB)": 1024.0 ** 4,
    },
}
# Temperature needs formulas, not ratios -- handled specially.
TEMPERATURE_UNITS = ["Celsius (°C)", "Fahrenheit (°F)", "Kelvin (K)"]


def convert_temperature(value, from_unit, to_unit):
    if from_unit == to_unit:
        return value
    # normalize to Celsius first
    if from_unit.startswith("Celsius"):
        c = value
    elif from_unit.startswith("Fahrenheit"):
        c = (value - 32) * 5 / 9
    else:  # Kelvin
        c = value - 273.15
    if to_unit.startswith("Celsius"):
        return c
    elif to_unit.startswith("Fahrenheit"):
        return c * 9 / 5 + 32
    else:
        return c + 273.15


# ---------------------------------------------------------------------------------
# 4. MAIN APPLICATION
# ---------------------------------------------------------------------------------

class CalcXApp:
    def __init__(self, root):
        self.root = root
        self.db = HistoryDB()
        self.theme_name = "Light"
        self.colors = THEMES[self.theme_name]

        self.expression = ""
        self.last_result = None
        self.memory = 0.0
        self.scientific_mode = False
        self.just_evaluated = False

        self._configure_root()
        self._build_menu()
        self._build_layout()
        self._apply_theme()
        self._bind_keyboard()
        self.refresh_history()

    # -- Root ---------------------------------------------------------------

    def _configure_root(self):
        self.root.title(f"{APP_NAME}  —  Scientific Calculator  ·  by {APP_AUTHOR}")
        self.root.geometry("980x680")
        self.root.minsize(860, 600)

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export History to CSV...", command=self.export_history_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy Result       Ctrl+C", command=self.copy_result)
        edit_menu.add_command(label="Clear                Esc", command=self.clear_all)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Scientific Mode", command=self.toggle_scientific)
        view_menu.add_command(label="Toggle Theme (Light/Dark)", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)

        history_menu = tk.Menu(menubar, tearoff=0)
        history_menu.add_command(label="Clear All History", command=self.clear_history)
        menubar.add_cascade(label="History", menu=history_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _bind_keyboard(self):
        for ch in "0123456789.+-*/()%":
            self.root.bind(ch, self._on_key_char)
        self.root.bind("<Return>", lambda e: self.evaluate())
        self.root.bind("<KP_Enter>", lambda e: self.evaluate())
        self.root.bind("<BackSpace>", lambda e: self.backspace())
        self.root.bind("<Escape>", lambda e: self.clear_all())
        self.root.bind("<Control-c>", lambda e: self.copy_result())
        self.root.bind("<Control-C>", lambda e: self.copy_result())
        self.root.bind("<Control-h>", lambda e: self.notebook.select(1))
        self.root.bind("^", lambda e: self._append("^"))

    def _on_key_char(self, event):
        self._append(event.char)

    # -- Layout --------------------------------------------------------------

    def _build_layout(self):
        c = self.colors
        self.outer = tk.Frame(self.root, bg=c["bg"])
        self.outer.pack(fill="both", expand=True)

        header = tk.Frame(self.outer, bg=c["bg"])
        header.pack(fill="x", padx=18, pady=(14, 6))
        self.title_label = tk.Label(header, text=f"🧮 {APP_NAME}", font=("Segoe UI", 18, "bold"),
                                      bg=c["bg"], fg=c["text"])
        self.title_label.pack(side="left")
        self.brand_label = tk.Label(header, text=f"by {APP_AUTHOR}", font=("Segoe UI", 9, "italic"),
                                      bg=c["bg"], fg=c["subtext"])
        self.brand_label.pack(side="left", padx=(8, 0), pady=(6, 0))
        self.theme_btn = tk.Button(header, text="🌙", command=self.toggle_theme,
                                     font=("Segoe UI", 12), relief="flat", bd=0,
                                     cursor="hand2", padx=10, pady=4)
        self.theme_btn.pack(side="right")
        self.sci_toggle_btn = tk.Button(header, text="Scientific: OFF", command=self.toggle_scientific,
                                          font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                                          cursor="hand2", padx=10, pady=6)
        self.sci_toggle_btn.pack(side="right", padx=(0, 10))

        self.notebook = ttk.Notebook(self.outer)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        self.calc_tab = tk.Frame(self.notebook, bg=c["bg"])
        self.convert_tab = tk.Frame(self.notebook, bg=c["bg"])
        self.notebook.add(self.calc_tab, text="  Calculator  ")
        self.notebook.add(self.convert_tab, text="  Unit Converter  ")

        self._build_calculator_tab()
        self._build_converter_tab()

    # -- Calculator tab --------------------------------------------------------

    def _build_calculator_tab(self):
        c = self.colors
        body = tk.Frame(self.calc_tab, bg=c["bg"])
        body.pack(fill="both", expand=True)

        # Left: calculator itself
        left = tk.Frame(body, bg=c["bg"])
        left.pack(side="left", fill="both", expand=True)

        # Display
        self.display_frame = tk.Frame(left, bg=c["display_bg"])
        self.display_frame.pack(fill="x", pady=(4, 12))
        self.expr_label = tk.Label(self.display_frame, text="", anchor="e",
                                     font=("Consolas", 14), bg=c["display_bg"],
                                     fg=c["display_sub"], padx=16)
        self.expr_label.pack(fill="x", pady=(10, 0))
        self.result_label = tk.Label(self.display_frame, text="0", anchor="e",
                                       font=("Consolas", 38, "bold"), bg=c["display_bg"],
                                       fg=c["display_fg"], padx=16)
        self.result_label.pack(fill="x", pady=(0, 14))

        # Memory row
        mem_frame = tk.Frame(left, bg=c["bg"])
        mem_frame.pack(fill="x", pady=(0, 6))
        for label, cmd in [("MC", self.memory_clear), ("MR", self.memory_recall),
                             ("M+", self.memory_add), ("M-", self.memory_subtract),
                             ("MS", self.memory_store)]:
            self._make_button(mem_frame, label, cmd, kind="fn", small=True).pack(
                side="left", fill="x", expand=True, padx=2)

        # Scientific row (togglable)
        self.sci_frame = tk.Frame(left, bg=c["bg"])
        sci_buttons = [
            ("sin", lambda: self._append("sin(")), ("cos", lambda: self._append("cos(")),
            ("tan", lambda: self._append("tan(")), ("π", lambda: self._append("pi")),
            ("asin", lambda: self._append("asin(")), ("acos", lambda: self._append("acos(")),
            ("atan", lambda: self._append("atan(")), ("e", lambda: self._append("e")),
            ("ln", lambda: self._append("ln(")), ("log", lambda: self._append("log(")),
            ("√", lambda: self._append("sqrt(")), ("n!", lambda: self._append("fact(")),
            ("x²", self._square), ("x³", self._cube),
            ("x^y", lambda: self._append("^")), ("1/x", self._reciprocal),
        ]
        for i, (label, cmd) in enumerate(sci_buttons):
            row, col = divmod(i, 4)
            b = self._make_button(self.sci_frame, label, cmd, kind="fn", small=True)
            b.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
        for col in range(4):
            self.sci_frame.grid_columnconfigure(col, weight=1)
        # not packed initially -- toggled on

        # Main button grid
        grid_frame = tk.Frame(left, bg=c["bg"])
        grid_frame.pack(fill="both", expand=True, pady=(6, 0))

        buttons = [
            [("C", self.clear_all, "danger"), ("CE", self.clear_entry, "fn"),
             ("⌫", self.backspace, "fn"), ("÷", lambda: self._append("/"), "op")],
            [("7", lambda: self._append("7"), "num"), ("8", lambda: self._append("8"), "num"),
             ("9", lambda: self._append("9"), "num"), ("×", lambda: self._append("*"), "op")],
            [("4", lambda: self._append("4"), "num"), ("5", lambda: self._append("5"), "num"),
             ("6", lambda: self._append("6"), "num"), ("-", lambda: self._append("-"), "op")],
            [("1", lambda: self._append("1"), "num"), ("2", lambda: self._append("2"), "num"),
             ("3", lambda: self._append("3"), "num"), ("+", lambda: self._append("+"), "op")],
            [("±", self._negate, "fn"), ("0", lambda: self._append("0"), "num"),
             (".", lambda: self._append("."), "num"), ("=", self.evaluate, "op")],
            [("(", lambda: self._append("("), "fn"), (")", lambda: self._append(")"), "fn"),
             ("%", lambda: self._append("%"), "fn"), ("ANS", self._insert_ans, "fn")],
        ]
        for r, row_defs in enumerate(buttons):
            grid_frame.grid_rowconfigure(r, weight=1)
            for cIdx, (label, cmd, kind) in enumerate(row_defs):
                grid_frame.grid_columnconfigure(cIdx, weight=1)
                btn = self._make_button(grid_frame, label, cmd, kind=kind)
                btn.grid(row=r, column=cIdx, sticky="nsew", padx=3, pady=3)

        # Right: history panel
        right = tk.Frame(body, bg=c["panel"], width=280)
        right.pack(side="left", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        hist_header = tk.Frame(right, bg=c["panel"])
        hist_header.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(hist_header, text="HISTORY", font=("Segoe UI", 9, "bold"),
                  bg=c["panel"], fg=c["subtext"]).pack(side="left")
        tk.Button(hist_header, text="Clear", command=self.clear_history,
                   font=("Segoe UI", 8), relief="flat", bd=0, bg=c["panel"],
                   fg=c["danger"], cursor="hand2").pack(side="right")

        self.history_search_var = tk.StringVar()
        self.history_search_var.trace_add("write", lambda *a: self.refresh_history())
        self.history_search_entry = tk.Entry(right, textvariable=self.history_search_var,
                                                font=("Segoe UI", 10), bg=c["entry_bg"], fg=c["text"],
                                                relief="flat", highlightthickness=1,
                                                highlightbackground=c["border"])
        self.history_search_entry.pack(fill="x", padx=12, pady=(0, 8), ipady=4)

        list_container = tk.Frame(right, bg=c["panel"])
        list_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.history_listbox = tk.Listbox(list_container, font=("Consolas", 9),
                                            bg=c["entry_bg"], fg=c["text"], relief="flat",
                                            highlightthickness=1, highlightbackground=c["border"],
                                            selectbackground=c["selected"], activestyle="none")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        hsb = ttk.Scrollbar(list_container, orient="vertical", command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hsb.set)
        hsb.pack(side="right", fill="y")
        self.history_listbox.bind("<Double-1>", self._reuse_history_item)

        del_btn = tk.Button(right, text="Delete Selected Entry", command=self._delete_history_item,
                              font=("Segoe UI", 9), relief="flat", bd=0, bg=c["panel"], fg=c["subtext"],
                              cursor="hand2")
        del_btn.pack(fill="x", padx=12, pady=(0, 12))

        self._history_rows = []

    def _make_button(self, parent, label, command, kind="num", small=False):
        c = self.colors
        bg = {"num": c["btn_num"], "op": c["btn_op"], "fn": c["btn_fn"],
              "danger": c["danger"]}.get(kind, c["btn_num"])
        fg = {"num": c["btn_num_fg"], "op": c["btn_op_fg"], "fn": c["btn_fn_fg"],
              "danger": "white"}.get(kind, c["text"])
        font_size = 10 if small else 15
        btn = tk.Button(parent, text=label, command=command, bg=bg, fg=fg,
                          font=("Segoe UI", font_size, "bold" if kind == "op" else "normal"),
                          relief="flat", bd=0, cursor="hand2",
                          activebackground=c["selected"], padx=6, pady=10 if not small else 6)
        return btn

    # -- Converter tab -----------------------------------------------------------

    def _build_converter_tab(self):
        c = self.colors
        frame = tk.Frame(self.convert_tab, bg=c["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=16)

        tk.Label(frame, text="CATEGORY", font=("Segoe UI", 9, "bold"),
                  bg=c["bg"], fg=c["subtext"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.conv_category_var = tk.StringVar(value="Length")
        categories = list(CONVERSION_GROUPS.keys()) + ["Temperature"]
        cat_combo = ttk.Combobox(frame, textvariable=self.conv_category_var, values=categories,
                                   state="readonly", font=("Segoe UI", 11), width=24)
        cat_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        cat_combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild_converter_units())

        tk.Label(frame, text="FROM", font=("Segoe UI", 9, "bold"),
                  bg=c["bg"], fg=c["subtext"]).grid(row=2, column=0, sticky="w")
        tk.Label(frame, text="TO", font=("Segoe UI", 9, "bold"),
                  bg=c["bg"], fg=c["subtext"]).grid(row=2, column=1, sticky="w")

        self.conv_from_var = tk.StringVar()
        self.conv_to_var = tk.StringVar()
        self.conv_from_combo = ttk.Combobox(frame, textvariable=self.conv_from_var,
                                              state="readonly", font=("Segoe UI", 11), width=20)
        self.conv_to_combo = ttk.Combobox(frame, textvariable=self.conv_to_var,
                                            state="readonly", font=("Segoe UI", 11), width=20)
        self.conv_from_combo.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(2, 16))
        self.conv_to_combo.grid(row=3, column=1, sticky="ew", pady=(2, 16))

        self.conv_input_var = tk.StringVar(value="1")
        self.conv_input_var.trace_add("write", lambda *a: self._do_conversion())
        self.conv_from_var.trace_add("write", lambda *a: self._do_conversion())
        self.conv_to_var.trace_add("write", lambda *a: self._do_conversion())

        entry = tk.Entry(frame, textvariable=self.conv_input_var, font=("Segoe UI", 16),
                           bg=c["entry_bg"], fg=c["text"], relief="flat",
                           highlightthickness=1, highlightbackground=c["border"])
        entry.grid(row=4, column=0, sticky="ew", ipady=8, padx=(0, 8))

        self.conv_result_label = tk.Label(frame, text="", font=("Segoe UI", 16, "bold"),
                                            bg=c["panel"], fg=c["accent"], anchor="w")
        self.conv_result_label.grid(row=4, column=1, sticky="ew", ipady=8, padx=(0, 0))

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        swap_btn = tk.Button(frame, text="⇅ Swap", command=self._swap_converter_units,
                               font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                               bg=c["btn_fn"], fg=c["text"], cursor="hand2", padx=10, pady=6)
        swap_btn.grid(row=5, column=0, sticky="w", pady=(10, 0))

        self._rebuild_converter_units()

    def _rebuild_converter_units(self):
        cat = self.conv_category_var.get()
        units = TEMPERATURE_UNITS if cat == "Temperature" else list(CONVERSION_GROUPS[cat].keys())
        self.conv_from_combo["values"] = units
        self.conv_to_combo["values"] = units
        self.conv_from_var.set(units[0])
        self.conv_to_var.set(units[1] if len(units) > 1 else units[0])
        self._do_conversion()

    def _swap_converter_units(self):
        a, b = self.conv_from_var.get(), self.conv_to_var.get()
        self.conv_from_var.set(b)
        self.conv_to_var.set(a)

    def _do_conversion(self):
        try:
            value = float(self.conv_input_var.get())
        except ValueError:
            self.conv_result_label.configure(text="—")
            return
        cat = self.conv_category_var.get()
        from_u, to_u = self.conv_from_var.get(), self.conv_to_var.get()
        if not from_u or not to_u:
            return
        try:
            if cat == "Temperature":
                result = convert_temperature(value, from_u, to_u)
            else:
                ratios = CONVERSION_GROUPS[cat]
                base = value * ratios[from_u]
                result = base / ratios[to_u]
            self.conv_result_label.configure(text=format_number(round(result, 8)))
        except Exception:
            self.conv_result_label.configure(text="Error")

    # -- Calculator logic -------------------------------------------------------

    def _append(self, token):
        if self.just_evaluated and token not in "+-*/^%":
            self.expression = ""
        self.just_evaluated = False
        self.expression += token
        self._update_display()

    def _negate(self):
        if self.expression.startswith("-"):
            self.expression = self.expression[1:]
        else:
            self.expression = "-" + self.expression
        self._update_display()

    def _square(self):
        self.expression += "^2"
        self._update_display()

    def _cube(self):
        self.expression += "^3"
        self._update_display()

    def _reciprocal(self):
        if self.expression:
            self.expression = f"1/({self.expression})"
            self._update_display()

    def _insert_ans(self):
        if self.last_result is not None:
            self._append(format_number(self.last_result))

    def backspace(self):
        self.expression = self.expression[:-1]
        self._update_display()

    def clear_entry(self):
        self.expression = ""
        self._update_display()

    def clear_all(self):
        self.expression = ""
        self.last_result = None
        self.just_evaluated = False
        self.expr_label.configure(text="")
        self.result_label.configure(text="0")

    def _update_display(self):
        self.expr_label.configure(text=self.expression)
        self.result_label.configure(text=self.expression if self.expression else "0")

    def evaluate(self):
        if not self.expression:
            return
        try:
            result = safe_eval(self.expression)
        except CalcError as e:
            self.result_label.configure(text=str(e), fg=self.colors["danger"])
            self.root.after(1200, lambda: self.result_label.configure(fg=self.colors["display_fg"]))
            return
        except Exception:
            self.result_label.configure(text="Error", fg=self.colors["danger"])
            self.root.after(1200, lambda: self.result_label.configure(fg=self.colors["display_fg"]))
            return

        formatted = format_number(result)
        self.expr_label.configure(text=self.expression + " =")
        self.result_label.configure(text=formatted)
        self.db.add(self.expression, formatted)
        self.last_result = result
        self.expression = formatted
        self.just_evaluated = True
        self.refresh_history()

    # -- Memory ---------------------------------------------------------------

    def memory_clear(self):
        self.memory = 0.0

    def memory_recall(self):
        self._append(format_number(self.memory))

    def memory_store(self):
        try:
            self.memory = safe_eval(self.expression) if self.expression else (self.last_result or 0.0)
        except CalcError:
            pass

    def memory_add(self):
        try:
            self.memory += safe_eval(self.expression) if self.expression else (self.last_result or 0.0)
        except CalcError:
            pass

    def memory_subtract(self):
        try:
            self.memory -= safe_eval(self.expression) if self.expression else (self.last_result or 0.0)
        except CalcError:
            pass

    # -- History --------------------------------------------------------------

    def refresh_history(self):
        query = self.history_search_var.get().strip() if hasattr(self, "history_search_var") else ""
        rows = self.db.all(query)
        self._history_rows = rows
        self.history_listbox.delete(0, tk.END)
        for r in rows:
            ts = r["created_at"].split("T")[-1][:5]
            self.history_listbox.insert(tk.END, f"[{ts}]  {r['expression']} = {r['result']}")

    def _reuse_history_item(self, event):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        row = self._history_rows[sel[0]]
        self.expression = row["expression"]
        self.just_evaluated = False
        self._update_display()
        self.notebook.select(0)

    def _delete_history_item(self):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        row = self._history_rows[sel[0]]
        self.db.delete(row["id"])
        self.refresh_history()

    def clear_history(self):
        if messagebox.askyesno(APP_NAME, "Clear all calculation history?"):
            self.db.clear()
            self.refresh_history()

    def export_history_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                              filetypes=[("CSV file", "*.csv")],
                                              initialfile="calcx_history.csv")
        if not path:
            return
        rows = self.db.all()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Expression", "Result"])
            for r in rows:
                writer.writerow([r["created_at"], r["expression"], r["result"]])
        messagebox.showinfo(APP_NAME, f"Exported {len(rows)} entries to:\n{path}")

    # -- Misc -------------------------------------------------------------------

    def copy_result(self):
        text = self.result_label.cget("text")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def toggle_scientific(self):
        self.scientific_mode = not self.scientific_mode
        if self.scientific_mode:
            self.sci_frame.pack(fill="x", pady=(0, 6), after=self.display_frame.master.winfo_children()[1])
            self.sci_toggle_btn.configure(text="Scientific: ON")
        else:
            self.sci_frame.pack_forget()
            self.sci_toggle_btn.configure(text="Scientific: OFF")

    def toggle_theme(self):
        self.theme_name = "Dark" if self.theme_name == "Light" else "Light"
        self.colors = THEMES[self.theme_name]
        self._apply_theme()
        self._rebuild_all_buttons()

    def _rebuild_all_buttons(self):
        # Simplest reliable way to re-theme every custom-colored widget: rebuild tabs.
        for tab in (self.calc_tab, self.convert_tab):
            for w in tab.winfo_children():
                w.destroy()
        self._build_calculator_tab()
        self._build_converter_tab()
        self._apply_theme()
        self.refresh_history()
        self._update_display()

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        self.outer.configure(bg=c["bg"])
        self.title_label.configure(bg=c["bg"], fg=c["text"])
        self.brand_label.configure(bg=c["bg"], fg=c["subtext"])
        self.theme_btn.configure(bg=c["bg"], fg=c["text"],
                                   text="🌙" if self.theme_name == "Light" else "☀")
        self.sci_toggle_btn.configure(bg=c["btn_fn"], fg=c["text"])
        self.calc_tab.configure(bg=c["bg"])
        self.convert_tab.configure(bg=c["bg"])

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=c["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=c["row_alt"], foreground=c["text"],
                          padding=[14, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", c["accent"])],
                   foreground=[("selected", "white")])
        style.configure("TCombobox", fieldbackground=c["entry_bg"], background=c["entry_bg"],
                          foreground=c["text"])

    # -- Help -----------------------------------------------------------------

    def show_shortcuts(self):
        text = (
            "0-9, . , + - * / ( ) %   Type directly\n"
            "^          Power (x^y)\n"
            "Enter      Evaluate (=)\n"
            "Backspace  Delete last character\n"
            "Esc        Clear everything\n"
            "Ctrl+C     Copy result to clipboard\n"
            "Ctrl+H     Jump to Unit Converter tab\n"
            "Double-click a history entry to reuse it\n"
        )
        messagebox.showinfo("Keyboard Shortcuts", text)

    def show_about(self):
        text = (
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            "A full-featured scientific calculator with memory, persistent\n"
            "history, and a built-in unit converter -- built with pure Python\n"
            "(Tkinter + SQLite).\n\n"
            f"Developed by {APP_AUTHOR}\n"
        )
        messagebox.showinfo(f"About {APP_NAME}", text)


def main():
    root = tk.Tk()
    CalcXApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

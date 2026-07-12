# 🧮 CalcX — The World's Best Little Calculator

**Developed by [@anxntbhardwaj](https://github.com/anxntbhardwaj)**

A pure-Python, single-file, desktop calculator built with Tkinter (GUI) and
SQLite (history storage) from the standard library. No external services,
fully offline.

## ✨ Features

- **Standard arithmetic**: `+ − × ÷ %` with a live, editable expression line
- **Scientific mode** (toggle anytime): `sin cos tan asin acos atan log ln
  sqrt x² x³ x^y 1/x n! π e`, parentheses
- **Memory**: `MC` `MR` `M+` `M-` `MS`
- **Persistent history** (SQLite): every calculation is saved, searchable,
  double-click to reuse, delete single entries, clear all, export to CSV
- **Unit Converter tab**: Length, Weight/Mass, Time, Data Storage, Temperature
- **Full keyboard support**: type numbers/operators directly, `Enter` = `=`,
  `Backspace`, `Esc` to clear, `Ctrl+C` to copy the result
- **Safe evaluation**: expressions are parsed with Python's `ast` module and
  checked against a strict whitelist — never a raw `eval()` of your input
- **Light & Dark themes**
- Handles divide-by-zero, invalid syntax, and math-domain errors gracefully

## 🚀 Getting Started

Requires **Python 3.8+** with Tkinter (bundled with most Python installs; on
Debian/Ubuntu: `sudo apt install python3-tk`). No extra packages needed.

```bash
python main.py
```

Your calculation history is stored locally in `calc_history.db`, created
automatically next to the script the first time you run it.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `0-9 . + - * / ( ) %` | Type directly into the expression |
| `^` | Power (`x^y`) |
| `Enter` | Evaluate (`=`) |
| `Backspace` | Delete last character |
| `Esc` | Clear everything |
| `Ctrl+C` | Copy result to clipboard |
| `Ctrl+H` | Jump to Unit Converter tab |
| Double-click a history row | Reuse that expression |

## 📄 License

Released under the **MIT License** — see [`LICENSE`](LICENSE). Free to use,
modify, and distribute; just keep the copyright notice and credit
**@anxntbhardwaj**.

---

Made with ☕ and Tkinter by **@anxntbhardwaj**

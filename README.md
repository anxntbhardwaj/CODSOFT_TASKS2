# 🧮 CalcX — The World's Best Little Calculator
<img width="1920" height="966" alt="CalcX  —  Scientific Calculator  ·  by @anxntbhardwaj 12-07-2026 07_50_08" src="https://github.com/user-attachments/assets/a5f8e39c-14f3-4a94-894c-81704a919296" />

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

<img width="1920" height="966" alt="CalcX  —  Scientific Calculator  ·  by @anxntbhardwaj 12-07-2026 07_50_20" src="https://github.com/user-attachments/assets/78f760ce-ac7c-4549-826c-0197a6519020" />
<img width="1920" height="966" alt="CalcX  —  Scientific Calculator  ·  by @anxntbhardwaj 12-07-2026 07_50_02" src="https://github.com/user-attachments/assets/6c84d507-1ff8-4da8-b44c-7197677c2190" />
<img width="1920" height="966" alt="CalcX  —  Scientific Calculator  ·  by @anxntbhardwaj 12-07-2026 07_50_32" src="https://github.com/user-attachments/assets/324c43a4-0e1d-4cad-b2a3-a31006df5330" />
<img width="1920" height="966" alt="CalcX  —  Scientific Calculator  ·  by @anxntbhardwaj 12-07-2026 07_50_27" src="https://github.com/user-attachments/assets/569004c6-bc68-40fb-9b2f-d61a11f42d0d" />

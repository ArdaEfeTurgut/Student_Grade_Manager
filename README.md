# Student Grade Manager

A desktop GUI application for managing students and their grades, built with Python and Tkinter as a final project for **OOP in Python (2026)**.

## Features

- Add / delete students (unique IDs generated automatically)
- Add, view and delete grades per subject (validated to the 0–100 range)
- Sortable, searchable student table with live average and letter grade
- Statistics tab: class average, top/bottom student, grade distribution chart
- Save / Open / New via a File menu — the whole class persists to a JSON file

## OOP concepts demonstrated

| Concept | Where |
|---|---|
| Inheritance | `Person` → `Student`; `tk.Toplevel` → `BaseDialog` → dialog classes |
| Encapsulation | Protected attributes + `@property` accessors |
| Abstraction | `Person` is an `ABC` with an abstract `get_role()` |
| Polymorphism | `get_role()` overridden by `Student` |
| Constructors | `__init__` + `super().__init__()` in every class |
| Decorators | `@property`/`@setter`, `@classmethod`, `@staticmethod` |
| Composition | `GradeManager` "has-a" list of `Student`; `App` "has-a" `GradeManager` |
| Custom exceptions | `InvalidGradeError`, `DuplicateStudentError` |

## Requirements

- Python 3.10+
- `tkinter` (included with most Python installations; on Linux: `sudo apt install python3-tk`)

No third-party packages are required.

## How to run

```bash
python student_grade_manager.py
```

## Data format

Class data is saved as a JSON file, e.g.:

```json
[
  {
    "first_name": "Alice",
    "last_name": "Wonderland",
    "student_id": "S1001",
    "grades": [
      {"subject": "Math", "value": 95.0, "date": "2026-06-19"}
    ]
  }
]
```

## Author

`Arda Efe Turgut` — OOP in Python, final project, 2026

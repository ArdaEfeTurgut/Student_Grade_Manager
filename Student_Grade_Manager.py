"""
================================================================================
 STUDENT GRADE MANAGER
 Final project - OOP in Python - 2026
================================================================================

Author      : Arda Efe Turgut
Index code  : 110051

DESCRIPTION
-----------
A desktop application (Tkinter GUI) that lets a teacher manage a list of
students and their grades: add/remove students, record grades per subject,
browse everyone in a sortable table, search by name, see class statistics
(average, top/bottom student, grade distribution chart) and save/load the
whole class to/from a JSON file.

ORIGINALITY / SOURCES
----------------------
The overall architecture (Person/Student/GradeManager + a Tkinter front end)
was designed for this assignment. Standard-library documentation
(docs.python.org for `tkinter`, `abc`, `json`) was used as reference for API
usage. No external tutorial code was copied. >>> Replace this paragraph with
your own honest account of what you used, as required by the assignment. <<<

HOW TO RUN
----------
    python student_grade_manager.py

No third-party packages are required - only the Python standard library
(tkinter is included with most standard Python installations).

OOP CONCEPTS DEMONSTRATED (see report for details)
----------------------------------------------------
- Encapsulation      : protected attributes (single underscore) + @property
- Inheritance         : Person -> Student ; tk.Toplevel -> BaseDialog -> *Dialog
- Constructors        : __init__ in every class, use of super().__init__()
- Abstraction         : Person is an ABC with an abstract method
- Decorators          : @property / @x.setter, @classmethod, @staticmethod
- Polymorphism        : get_role() overridden by Student, __str__ overrides
- Composition         : GradeManager "has-a" collection of Student objects;
                         App "has-a" GradeManager (favoured over inheritance)
- Custom exceptions   : InvalidGradeError, DuplicateStudentError
================================================================================
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict


# ==============================================================================
# CUSTOM EXCEPTIONS
# ==============================================================================
class InvalidGradeError(Exception):
    """Raised when a grade value is missing, non-numeric or out of range."""
    pass


class DuplicateStudentError(Exception):
    """Raised when trying to register a student ID that already exists."""
    pass


# ==============================================================================
# DOMAIN MODEL
# ==============================================================================
class Person(ABC):
    """Abstract base class for any person tracked by the system.

    Demonstrates encapsulation (protected attributes exposed only through
    validated properties) and abstraction (an abstract method that forces
    every concrete subclass to declare its role).
    """

    def __init__(self, first_name: str, last_name: str):
        # Constructor: validate and store data through the setters below,
        # so invalid data can never enter the object even at creation time.
        self._first_name = self._validate_name(first_name, "First name")
        self._last_name = self._validate_name(last_name, "Last name")

    @staticmethod
    def _validate_name(value: str, field_name: str) -> str:
        """Static method: a pure helper that needs neither instance (self)
        nor class (cls) state - it just validates input."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value.strip().title()

    @property
    def first_name(self) -> str:
        return self._first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self._first_name = self._validate_name(value, "First name")

    @property
    def last_name(self) -> str:
        return self._last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self._last_name = self._validate_name(value, "Last name")

    @property
    def full_name(self) -> str:
        """Read-only computed property - there is intentionally no setter,
        because full_name is derived from first/last name, not stored."""
        return f"{self._first_name} {self._last_name}"

    @abstractmethod
    def get_role(self) -> str:
        """Every subclass must say what kind of person it represents."""
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.get_role()}: {self.full_name}"


class Grade:
    """A single grade entry for one subject (0-100 percentage scale)."""

    MIN_VALUE = 0.0
    MAX_VALUE = 100.0

    def __init__(self, subject: str, value: float, date: Optional[str] = None):
        self._subject = subject.strip().title() if subject and subject.strip() else "General"
        self.value = value  # goes through the validating setter/property below
        self._date = date or datetime.now().strftime("%Y-%m-%d")

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, new_value) -> None:
        if not Grade.is_valid(new_value):
            raise InvalidGradeError(
                f"Grade must be a number between {Grade.MIN_VALUE:.0f} "
                f"and {Grade.MAX_VALUE:.0f}."
            )
        self._value = float(new_value)

    @property
    def date(self) -> str:
        return self._date

    @staticmethod
    def is_valid(value) -> bool:
        """Static method: validation logic that belongs to the Grade concept
        but does not need any particular Grade instance to run."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        return Grade.MIN_VALUE <= v <= Grade.MAX_VALUE

    @staticmethod
    def value_to_letter(value: float) -> str:
        """Static utility shared by Grade and Student to turn a number into
        a letter grade, without needing any instance."""
        if value >= 90:
            return "A"
        if value >= 80:
            return "B"
        if value >= 70:
            return "C"
        if value >= 60:
            return "D"
        return "F"

    def to_dict(self) -> dict:
        return {"subject": self._subject, "value": self._value, "date": self._date}

    @classmethod
    def from_dict(cls, data: dict) -> "Grade":
        """Classmethod alternative constructor: rebuild a Grade from the
        dictionary shape produced by to_dict() / loaded from JSON."""
        return cls(data["subject"], data["value"], data.get("date"))

    def __str__(self) -> str:
        return f"{self._subject}: {self._value:.1f} ({Grade.value_to_letter(self._value)})"


class Student(Person):
    """A student: inherits identity (name) from Person and adds grades.

    Demonstrates inheritance (extends Person), use of a class attribute
    shared by every instance (_id_counter) and a classmethod that mutates
    that shared state to hand out unique IDs.
    """

    _id_counter = 1000  # class attribute: shared "next free id" counter

    def __init__(self, first_name: str, last_name: str, student_id: Optional[str] = None):
        super().__init__(first_name, last_name)  # reuse Person's constructor
        self._student_id = student_id or Student._generate_id()
        self._grades: List[Grade] = []

    @classmethod
    def _generate_id(cls) -> str:
        """Classmethod: operates on class-level state (cls._id_counter),
        not on any single instance - exactly what @classmethod is for."""
        cls._id_counter += 1
        return f"S{cls._id_counter}"

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """Classmethod alternative constructor used when loading a saved
        class list back from a JSON file."""
        student = cls(data["first_name"], data["last_name"], data["student_id"])
        for g in data.get("grades", []):
            student._grades.append(Grade.from_dict(g))
        # Keep the shared id counter ahead of whatever was loaded, so newly
        # created students never collide with ids coming from a file.
        try:
            num = int(str(data["student_id"]).lstrip("S"))
            cls._id_counter = max(cls._id_counter, num)
        except (ValueError, KeyError):
            pass
        return student

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def grades(self) -> List[Grade]:
        """Returns a *copy* of the internal list - callers cannot mutate the
        student's real grade list directly, only through add_grade /
        remove_grade. This is the encapsulation principle in action."""
        return list(self._grades)

    def add_grade(self, subject: str, value: float) -> None:
        self._grades.append(Grade(subject, value))

    def remove_grade(self, index: int) -> None:
        if 0 <= index < len(self._grades):
            del self._grades[index]

    @property
    def average(self) -> float:
        """Computed, read-only property - intentionally has no setter,
        since the average must always be derived from the grade list."""
        if not self._grades:
            return 0.0
        return sum(g.value for g in self._grades) / len(self._grades)

    @property
    def letter_grade(self) -> str:
        return Grade.value_to_letter(self.average) if self._grades else "-"

    def get_role(self) -> str:
        """Overrides Person.get_role() -> polymorphism: code that calls
        person.get_role() works the same way for any Person subclass."""
        return "Student"

    def to_dict(self) -> dict:
        return {
            "first_name": self._first_name,
            "last_name": self._last_name,
            "student_id": self._student_id,
            "grades": [g.to_dict() for g in self._grades],
        }


class GradeManager:
    """Owns and manages the whole collection of students.

    This class demonstrates composition ("has-a" relationship): a
    GradeManager *has* students, rather than *being* a student - composition
    was chosen over inheritance here because a manager is not a kind of
    student, it just coordinates a group of them.
    """

    def __init__(self):
        self._students: Dict[str, Student] = {}

    def add_student(self, student: Student) -> None:
        if student.student_id in self._students:
            raise DuplicateStudentError(f"Student ID {student.student_id} already exists.")
        self._students[student.student_id] = student

    def remove_student(self, student_id: str) -> None:
        self._students.pop(student_id, None)

    def get_student(self, student_id: str) -> Optional[Student]:
        return self._students.get(student_id)

    @property
    def students(self) -> List[Student]:
        return list(self._students.values())

    @property
    def student_count(self) -> int:
        return len(self._students)

    @property
    def class_average(self) -> float:
        active = [s for s in self._students.values() if s.grades]
        if not active:
            return 0.0
        return sum(s.average for s in active) / len(active)

    def top_student(self) -> Optional[Student]:
        active = [s for s in self._students.values() if s.grades]
        return max(active, key=lambda s: s.average) if active else None

    def bottom_student(self) -> Optional[Student]:
        active = [s for s in self._students.values() if s.grades]
        return min(active, key=lambda s: s.average) if active else None

    def grade_distribution(self) -> Dict[str, int]:
        """Counts how many grades fall in each letter grade band."""
        dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for s in self._students.values():
            for g in s.grades:
                dist[Grade.value_to_letter(g.value)] += 1
        return dist

    def save_to_file(self, path: str) -> None:
        data = [s.to_dict() for s in self._students.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, path: str) -> "GradeManager":
        """Classmethod alternative constructor: build a manager that is
        already populated with the students/grades stored in a JSON file."""
        manager = cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            manager.add_student(Student.from_dict(item))
        return manager


# ==============================================================================
# GUI - THEME CONSTANTS
# ==============================================================================
class Theme:
    """Small namespace of shared style constants for the whole GUI.
    Using a class here (instead of loose module-level variables) keeps all
    visual constants grouped under one importable name: Theme.XXX."""

    BG = "#1e2530"
    PANEL = "#262f3d"
    PANEL_ALT = "#2d3748"
    ACCENT = "#4f9dde"
    ACCENT_DARK = "#3a7cb5"
    TEXT = "#e8edf4"
    TEXT_DIM = "#9aa7b8"
    SUCCESS = "#4caf7d"
    DANGER = "#e0654f"
    WARNING = "#e0a83f"
    FONT = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_HEADING = ("Segoe UI", 12, "bold")
    GRADE_COLORS = {"A": "#4caf7d", "B": "#7fb3e0", "C": "#e0a83f", "D": "#e08a3f", "F": "#e0654f"}


def configure_styles(root: tk.Tk) -> None:
    """Configures the ttk theme once, at application start-up."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass  # 'clam' should always be available, but fail gracefully

    style.configure("TFrame", background=Theme.BG)
    style.configure("Panel.TFrame", background=Theme.PANEL)
    style.configure("TLabel", background=Theme.BG, foreground=Theme.TEXT, font=Theme.FONT)
    style.configure("Panel.TLabel", background=Theme.PANEL, foreground=Theme.TEXT, font=Theme.FONT)
    style.configure("Title.TLabel", background=Theme.BG, foreground=Theme.TEXT, font=Theme.FONT_TITLE)
    style.configure("Heading.TLabel", background=Theme.PANEL, foreground=Theme.TEXT, font=Theme.FONT_HEADING)
    style.configure("Dim.TLabel", background=Theme.PANEL, foreground=Theme.TEXT_DIM, font=Theme.FONT)
    style.configure("Stat.TLabel", background=Theme.PANEL, foreground=Theme.ACCENT, font=("Segoe UI", 20, "bold"))

    style.configure("TNotebook", background=Theme.BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=Theme.PANEL, foreground=Theme.TEXT_DIM,
                     padding=(16, 8), font=Theme.FONT_BOLD)
    style.map("TNotebook.Tab",
              background=[("selected", Theme.ACCENT)],
              foreground=[("selected", "#ffffff")])

    style.configure("TButton", background=Theme.ACCENT, foreground="#ffffff",
                     font=Theme.FONT_BOLD, padding=(10, 6), borderwidth=0)
    style.map("TButton", background=[("active", Theme.ACCENT_DARK)])

    style.configure("Danger.TButton", background=Theme.DANGER, foreground="#ffffff",
                     font=Theme.FONT_BOLD, padding=(10, 6), borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#c2503d")])

    style.configure("TEntry", fieldbackground=Theme.PANEL_ALT, foreground=Theme.TEXT,
                     insertcolor=Theme.TEXT, borderwidth=1, padding=6)

    style.configure("Treeview", background=Theme.PANEL_ALT, fieldbackground=Theme.PANEL_ALT,
                     foreground=Theme.TEXT, rowheight=26, font=Theme.FONT, borderwidth=0)
    style.configure("Treeview.Heading", background=Theme.PANEL, foreground=Theme.TEXT,
                     font=Theme.FONT_BOLD, borderwidth=0)
    style.map("Treeview", background=[("selected", Theme.ACCENT)],
              foreground=[("selected", "#ffffff")])


# ==============================================================================
# GUI - REUSABLE DIALOG BASE CLASS
# ==============================================================================
class BaseDialog(tk.Toplevel):
    """Common behaviour shared by every modal dialog in this app: centred
    over its parent, fixed size, grabs focus until closed.

    Demonstrates a second, GUI-side inheritance hierarchy on top of the
    domain-model one: BaseDialog extends tk.Toplevel, and every concrete
    dialog below extends BaseDialog.
    """

    def __init__(self, parent: tk.Misc, title: str, width: int = 360, height: int = 260):
        super().__init__(parent)
        self.result = None  # subclasses set this when the user confirms
        self.configure(bg=Theme.PANEL)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self._build_geometry(parent, width, height)
        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build_geometry(self, parent: tk.Misc, width: int, height: int) -> None:
        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    def labeled_entry(self, parent: tk.Misc, label_text: str) -> tk.Entry:
        """Small helper reused by subclasses to build a consistent
        label + entry row."""
        ttk.Label(parent, text=label_text, style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        entry = tk.Entry(parent, font=Theme.FONT, bg=Theme.PANEL_ALT, fg=Theme.TEXT,
                          insertbackground=Theme.TEXT, relief="flat")
        entry.pack(fill="x", ipady=5)
        return entry


class AddStudentDialog(BaseDialog):
    """Collects a first and last name and validates them before closing."""

    def __init__(self, parent: tk.Misc):
        super().__init__(parent, "Add Student", 360, 240)
        body = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        self.first_entry = self.labeled_entry(body, "First name")
        self.last_entry = self.labeled_entry(body, "Last name")
        self.first_entry.focus_set()

        btn_row = tk.Frame(body, bg=Theme.PANEL)
        btn_row.pack(fill="x", pady=(18, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="Add", command=self._confirm).pack(side="right")
        self.bind("<Return>", lambda _e: self._confirm())

    def _confirm(self) -> None:
        first, last = self.first_entry.get().strip(), self.last_entry.get().strip()
        if not first or not last:
            messagebox.showwarning("Missing data", "Please fill in both first and last name.", parent=self)
            return
        self.result = (first, last)
        self.destroy()


class AddGradeDialog(BaseDialog):
    """Collects a subject name and a numeric grade (0-100) for a student."""

    COMMON_SUBJECTS = ["Math", "Physics", "Programming", "English", "History", "Chemistry", "Biology"]

    def __init__(self, parent: tk.Misc, student_name: str):
        super().__init__(parent, f"Add Grade - {student_name}", 360, 280)
        body = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Subject", style="Panel.TLabel").pack(anchor="w", pady=(0, 2))
        self.subject_var = tk.StringVar()
        subject_box = ttk.Combobox(body, textvariable=self.subject_var,
                                    values=self.COMMON_SUBJECTS, font=Theme.FONT)
        subject_box.pack(fill="x", ipady=3)

        self.value_entry = self.labeled_entry(body, "Grade (0-100)")

        btn_row = tk.Frame(body, bg=Theme.PANEL)
        btn_row.pack(fill="x", pady=(18, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="Add", command=self._confirm).pack(side="right")
        self.bind("<Return>", lambda _e: self._confirm())
        subject_box.focus_set()

    def _confirm(self) -> None:
        subject = self.subject_var.get().strip()
        raw_value = self.value_entry.get().strip()
        if not subject:
            messagebox.showwarning("Missing data", "Please enter a subject.", parent=self)
            return
        if not Grade.is_valid(raw_value):
            messagebox.showwarning(
                "Invalid grade",
                f"Grade must be a number between {Grade.MIN_VALUE:.0f} and {Grade.MAX_VALUE:.0f}.",
                parent=self,
            )
            return
        self.result = (subject, float(raw_value))
        self.destroy()


class ViewGradesDialog(BaseDialog):
    """Shows every grade recorded for one student, with a delete option."""

    def __init__(self, parent: "StudentGradeApp", student: Student):
        super().__init__(parent, f"Grades - {student.full_name}", 420, 380)
        self.app = parent
        self.student = student

        header = tk.Frame(self, bg=Theme.PANEL, padx=20)
        header.pack(fill="x", pady=(16, 8))
        ttk.Label(header, text=student.full_name, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header, text=f"ID: {student.student_id}   |   Average: {student.average:.1f}  "
                                f"({student.letter_grade})",
                  style="Dim.TLabel").pack(anchor="w")

        list_frame = tk.Frame(self, bg=Theme.PANEL, padx=20)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame, bg=Theme.PANEL_ALT, fg=Theme.TEXT,
                                   font=Theme.FONT, relief="flat", selectbackground=Theme.ACCENT,
                                   activestyle="none")
        self.listbox.pack(fill="both", expand=True, pady=(4, 8))
        self._refresh_list()

        btn_row = tk.Frame(self, bg=Theme.PANEL, padx=20)
        btn_row.pack(fill="x", pady=(0, 16))
        ttk.Button(btn_row, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(btn_row, text="Delete Selected", style="Danger.TButton",
                   command=self._delete_selected).pack(side="right", padx=(0, 8))

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for g in self.student.grades:
            self.listbox.insert(tk.END, f"  {str(g)}   -   {g.date}")

    def _delete_selected(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("No selection", "Select a grade to delete first.", parent=self)
            return
        self.student.remove_grade(selection[0])
        self._refresh_list()
        self.app.refresh_table()
        self.app.refresh_statistics()


# ==============================================================================
# GUI - MAIN APPLICATION WINDOW
# ==============================================================================
class StudentGradeApp(tk.Tk):
    """Main application window.

    Holds a GradeManager by composition ("has-a"), keeping the GUI layer and
    the domain-logic layer cleanly separated: this class never stores grade
    data itself, it only displays/edits what GradeManager owns.
    """

    def __init__(self):
        super().__init__()
        self.title("Student Grade Manager")
        self.geometry("980x620")
        self.minsize(820, 540)
        self.configure(bg=Theme.BG)
        configure_styles(self)

        self.manager = GradeManager()
        self.current_file: Optional[str] = None

        self._build_menu()
        self._build_layout()
        self.refresh_table()
        self.refresh_statistics()

    # ---------------------------------------------------------------- menu
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "Student Grade Manager\nFinal project - OOP in Python - 2026\n\n"
            "Manage students and grades with a simple GUI.",
        )

    # -------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        header = tk.Frame(self, bg=Theme.BG, padx=20, pady=16)
        header.pack(fill="x")
        ttk.Label(header, text="Student Grade Manager", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Track students, record grades, review class statistics.",
                  style="TLabel").pack(anchor="w")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        students_tab = tk.Frame(notebook, bg=Theme.BG)
        stats_tab = tk.Frame(notebook, bg=Theme.BG)
        notebook.add(students_tab, text="  Students  ")
        notebook.add(stats_tab, text="  Statistics  ")

        self._build_students_tab(students_tab)
        self._build_statistics_tab(stats_tab)

        self.status_var = tk.StringVar(value="Ready.")
        status_bar = tk.Label(self, textvariable=self.status_var, bg=Theme.PANEL, fg=Theme.TEXT_DIM,
                               anchor="w", padx=12, pady=4, font=Theme.FONT)
        status_bar.pack(fill="x", side="bottom")

    # ------------------------------------------------------- students tab
    def _build_students_tab(self, parent: tk.Frame) -> None:
        toolbar = tk.Frame(parent, bg=Theme.BG, pady=10)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="+ Add Student", command=self.add_student).pack(side="left")
        ttk.Button(toolbar, text="+ Add Grade", command=self.add_grade_to_selected).pack(side="left", padx=8)
        ttk.Button(toolbar, text="View Grades", command=self.view_selected_grades).pack(side="left")
        ttk.Button(toolbar, text="Delete Student", style="Danger.TButton",
                   command=self.delete_selected_student).pack(side="left", padx=8)

        search_frame = tk.Frame(toolbar, bg=Theme.BG)
        search_frame.pack(side="right")
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_table())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=Theme.FONT,
                                 bg=Theme.PANEL_ALT, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                 relief="flat", width=20)
        search_entry.pack(side="left", ipady=4)

        table_frame = tk.Frame(parent, bg=Theme.BG)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "name", "count", "average", "letter")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"id": "ID", "name": "Name", "count": "# Grades", "average": "Average", "letter": "Letter"}
        widths = {"id": 90, "name": 240, "count": 100, "average": 110, "letter": 90}
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=widths[col], anchor="center" if col != "name" else "w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self.view_selected_grades())

        self._sort_state = {"column": None, "reverse": False}

    def _sort_by(self, column: str) -> None:
        reverse = self._sort_state["column"] == column and not self._sort_state["reverse"]
        self._sort_state = {"column": column, "reverse": reverse}
        self.refresh_table()

    # ------------------------------------------------------ statistics tab
    def _build_statistics_tab(self, parent: tk.Frame) -> None:
        cards = tk.Frame(parent, bg=Theme.BG, pady=10)
        cards.pack(fill="x")

        self.stat_count_var = tk.StringVar(value="0")
        self.stat_avg_var = tk.StringVar(value="0.0")
        self.stat_top_var = tk.StringVar(value="-")
        self.stat_bottom_var = tk.StringVar(value="-")

        self._build_stat_card(cards, "Students", self.stat_count_var)
        self._build_stat_card(cards, "Class Average", self.stat_avg_var)
        self._build_stat_card(cards, "Top Student", self.stat_top_var, big=False)
        self._build_stat_card(cards, "Needs Support", self.stat_bottom_var, big=False)

        chart_panel = tk.Frame(parent, bg=Theme.PANEL, padx=20, pady=16)
        chart_panel.pack(fill="both", expand=True, pady=(16, 0))
        ttk.Label(chart_panel, text="Grade Distribution", style="Heading.TLabel").pack(anchor="w")
        self.chart_canvas = tk.Canvas(chart_panel, bg=Theme.PANEL, highlightthickness=0, height=260)
        self.chart_canvas.pack(fill="both", expand=True, pady=(12, 0))
        self.chart_canvas.bind("<Configure>", lambda _e: self.refresh_statistics())

    def _build_stat_card(self, parent: tk.Frame, label: str, var: tk.StringVar, big: bool = True) -> None:
        card = tk.Frame(parent, bg=Theme.PANEL, padx=16, pady=12)
        card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ttk.Label(card, text=label, style="Dim.TLabel").pack(anchor="w")
        style_name = "Stat.TLabel" if big else "Heading.TLabel"
        ttk.Label(card, textvariable=var, style=style_name).pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------- actions
    def add_student(self) -> None:
        dialog = AddStudentDialog(self)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        first, last = dialog.result
        student = Student(first, last)
        self.manager.add_student(student)  # ids are auto-generated -> no collision possible
        self.refresh_table()
        self.refresh_statistics()
        self.status_var.set(f"Added student {student.full_name} ({student.student_id}).")

    def _get_selected_student(self) -> Optional[Student]:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please select a student first.")
            return None
        student_id = selection[0]
        return self.manager.get_student(student_id)

    def add_grade_to_selected(self) -> None:
        student = self._get_selected_student()
        if student is None:
            return
        dialog = AddGradeDialog(self, student.full_name)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        subject, value = dialog.result
        try:
            student.add_grade(subject, value)
        except InvalidGradeError as exc:
            messagebox.showerror("Invalid grade", str(exc))
            return
        self.refresh_table()
        self.refresh_statistics()
        self.status_var.set(f"Added {subject} grade ({value:.1f}) for {student.full_name}.")

    def view_selected_grades(self) -> None:
        student = self._get_selected_student()
        if student is None:
            return
        dialog = ViewGradesDialog(self, student)
        self.wait_window(dialog)
        self.refresh_table()
        self.refresh_statistics()

    def delete_selected_student(self) -> None:
        student = self._get_selected_student()
        if student is None:
            return
        if not messagebox.askyesno("Confirm delete", f"Remove {student.full_name} and all their grades?"):
            return
        self.manager.remove_student(student.student_id)
        self.refresh_table()
        self.refresh_statistics()
        self.status_var.set(f"Removed student {student.full_name}.")

    # --------------------------------------------------------------- file
    def new_file(self) -> None:
        if not messagebox.askyesno("New file", "Discard the current class list and start a new one?"):
            return
        self.manager = GradeManager()
        self.current_file = None
        self.refresh_table()
        self.refresh_statistics()
        self.status_var.set("Started a new, empty class list.")

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            self.manager = GradeManager.load_from_file(path)
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            messagebox.showerror("Could not open file", f"This file could not be loaded:\n{exc}")
            return
        self.current_file = path
        self.refresh_table()
        self.refresh_statistics()
        self.status_var.set(f"Loaded {self.manager.student_count} students from {os.path.basename(path)}.")

    def save_file(self) -> None:
        if not self.current_file:
            self.save_file_as()
            return
        self.manager.save_to_file(self.current_file)
        self.status_var.set(f"Saved to {os.path.basename(self.current_file)}.")

    def save_file_as(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        self.current_file = path
        self.manager.save_to_file(path)
        self.status_var.set(f"Saved to {os.path.basename(path)}.")

    # ----------------------------------------------------------- refresh
    def refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        rows = [s for s in self.manager.students if query in s.full_name.lower()]

        col = self._sort_state["column"] if hasattr(self, "_sort_state") else None
        if col:
            key_funcs = {
                "id": lambda s: s.student_id,
                "name": lambda s: s.full_name.lower(),
                "count": lambda s: len(s.grades),
                "average": lambda s: s.average,
                "letter": lambda s: s.letter_grade,
            }
            rows.sort(key=key_funcs[col], reverse=self._sort_state["reverse"])

        for s in rows:
            self.tree.insert("", tk.END, iid=s.student_id,
                              values=(s.student_id, s.full_name, len(s.grades),
                                      f"{s.average:.1f}", s.letter_grade))

    def refresh_statistics(self) -> None:
        self.stat_count_var.set(str(self.manager.student_count))
        self.stat_avg_var.set(f"{self.manager.class_average:.1f}")
        top = self.manager.top_student()
        bottom = self.manager.bottom_student()
        self.stat_top_var.set(f"{top.full_name} ({top.average:.1f})" if top else "-")
        self.stat_bottom_var.set(f"{bottom.full_name} ({bottom.average:.1f})" if bottom else "-")
        self._draw_distribution_chart()

    def _draw_distribution_chart(self) -> None:
        """Hand-drawn bar chart on a tk.Canvas - no external charting library
        needed, while still giving a genuinely graphical statistics view."""
        canvas = self.chart_canvas
        canvas.delete("all")
        width = canvas.winfo_width() or 600
        height = canvas.winfo_height() or 260
        dist = self.manager.grade_distribution()
        labels = ["A", "B", "C", "D", "F"]
        max_count = max(dist.values()) if any(dist.values()) else 1

        margin_bottom = 30
        margin_top = 10
        usable_height = height - margin_bottom - margin_top
        bar_area_width = width - 40
        bar_width = bar_area_width / (len(labels) * 2)

        for i, label in enumerate(labels):
            count = dist[label]
            bar_height = (count / max_count) * usable_height if max_count else 0
            x0 = 20 + i * 2 * bar_width + bar_width * 0.25
            x1 = x0 + bar_width * 1.5
            y1 = height - margin_bottom
            y0 = y1 - bar_height
            canvas.create_rectangle(x0, y0, x1, y1, fill=Theme.GRADE_COLORS[label], width=0)
            canvas.create_text((x0 + x1) / 2, y1 + 14, text=label, fill=Theme.TEXT, font=Theme.FONT_BOLD)
            canvas.create_text((x0 + x1) / 2, y0 - 10, text=str(count), fill=Theme.TEXT_DIM, font=Theme.FONT)


# ==============================================================================
# ENTRY POINT
# ==============================================================================
def main() -> None:
    app = StudentGradeApp()
    app.mainloop()


if __name__ == "__main__":
    main()

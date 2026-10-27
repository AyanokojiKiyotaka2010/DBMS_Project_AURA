"""Marks -> grade-point conversion (10-point scale, percentage based).

Edit GRADE_SCALE / PASS_PERCENT to match your institution's regulations.
Anything below the lowest band is an 'F' (grade point 0, status FAIL == backlog).
"""

# (minimum percentage, grade point, letter)  — checked top to bottom
GRADE_SCALE = [
    (90, 10, "O"),
    (80, 9, "A+"),
    (70, 8, "A"),
    (60, 7, "B+"),
    (50, 6, "B"),
    (45, 5, "C"),
    (40, 4, "P"),
]
PASS_PERCENT = 40


def grade_for(marks: float, max_marks: float) -> dict:
    """Return percentage, grade_point, grade_letter and PASS/FAIL for a mark."""
    if max_marks <= 0:
        raise ValueError("max_marks must be positive")
    if marks < 0 or marks > max_marks:
        raise ValueError(f"marks must be between 0 and {max_marks:g}")
    pct = round(marks * 100.0 / max_marks, 2)
    for lo, gp, letter in GRADE_SCALE:
        if pct >= lo and pct >= PASS_PERCENT:
            return {"percentage": pct, "grade_point": gp, "grade_letter": letter, "status": "PASS"}
    return {"percentage": pct, "grade_point": 0, "grade_letter": "F", "status": "FAIL"}

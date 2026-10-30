"""Administrator-only endpoint that loads one parsed result sheet (see importer/).

The PDFs never leave the admin's computer: `import_results.py --upload` parses them locally and posts
the parsed sheet here, so the (fast, stable) server-to-database link does the thousands of inserts.
"""
import re
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from common import get_user, require_role
from importer.loader import load
from importer.result_sheets import GRADE_POINTS

router = APIRouter()
_LETTERS = set(GRADE_POINTS) | {"II", "NA", "XX"}
_ADM = re.compile(r"^[UI]\d{2}[A-Z]{2}\d{3}$")


class StudentIn(BaseModel):
    admission_no: str
    name: str = Field(min_length=1, max_length=120)
    semester: int = Field(ge=1, le=14)
    grades: Dict[str, str]
    reg_credit: float = Field(ge=0, le=100)
    earned_credit: float = Field(ge=0, le=100)
    sgpa: float = Field(ge=0, le=10)
    cgpa: float = Field(ge=0, le=10)


class SheetIn(BaseModel):
    kind: str = "regular"
    branch: str = Field(min_length=1, max_length=200)
    semester_name: str
    courses: Dict[str, float]
    course_names: Dict[str, str] = {}
    students: List[StudentIn] = Field(max_length=600)


class ImportIn(BaseModel):
    folder_year: int = Field(ge=1, le=4)
    graduates: str = "alumni"
    sheet: SheetIn


@router.post("/admin/import-sheet")
async def import_sheet(inp: ImportIn, user=Depends(get_user)):
    require_role(user, ["Administrator"])
    sh = inp.sheet.model_dump()
    if inp.graduates not in ("alumni", "skip"):
        raise HTTPException(400, "graduates must be 'alumni' or 'skip'")
    for c, cr in sh["courses"].items():
        if not (0 <= cr <= 20) or len(c) > 20:
            raise HTTPException(400, f"bad course {c!r}")
    for st in sh["students"]:
        if not _ADM.match(st["admission_no"]):
            raise HTTPException(400, f"bad admission number {st['admission_no']!r}")
        for code, letter in st["grades"].items():
            if code not in sh["courses"] or letter not in _LETTERS:
                raise HTTPException(400, f"bad grade {code!r}={letter!r} for {st['admission_no']}")
    stats = await load([(inp.folder_year, sh)], graduates=inp.graduates, log=lambda *a: None)
    return {"ok": True, "stats": stats}

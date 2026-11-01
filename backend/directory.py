"""Read-only faculty directory (official names and office extensions only)."""
from typing import Optional

from fastapi import APIRouter, Depends

import db
from common import get_user

router = APIRouter(prefix="/faculty")


@router.get("")
async def list_faculty(q: str = "", department: Optional[str] = None, user=Depends(get_user)):
    where, args = [], []
    if q.strip():
        where.append("(LOWER(name) LIKE %s OR LOWER(department) LIKE %s)")
        like = f"%{q.strip().lower()}%"
        args += [like, like]
    if department:
        where.append("department = %s")
        args.append(department)
    rows = await db.all("SELECT id, department, name, extension, is_hod, affiliation, note, source_url FROM faculty "
                        + ("WHERE " + " AND ".join(where) + " " if where else "")
                        + "ORDER BY department, is_hod DESC, name LIMIT 500", tuple(args))
    depts = [r["department"] for r in await db.all("SELECT DISTINCT department FROM faculty ORDER BY department")]
    return {"departments": depts,
            "faculty": [{**r, "is_hod": bool(r["is_hod"])} for r in rows]}

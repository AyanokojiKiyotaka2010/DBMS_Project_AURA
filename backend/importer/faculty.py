"""Faculty directory import + linking club faculty-coordinators to directory entries."""
import db
from .names import best_unique


async def load_faculty(items) -> dict:
    stats = {"faculty_new": 0, "faculty_updated": 0}
    for f in items:
        row = await db.one("SELECT id FROM faculty WHERE department=%s AND name=%s", (f["department"], f["name"]))
        vals = (f.get("extension", ""), 1 if f.get("is_hod") else 0, f.get("affiliation", ""), f.get("note", ""), f.get("source_url", ""))
        if row:
            await db.run("UPDATE faculty SET extension=%s, is_hod=%s, affiliation=%s, note=%s, source_url=%s WHERE id=%s", vals + (row["id"],))
            stats["faculty_updated"] += 1
        else:
            await db.run("INSERT INTO faculty (department,name,extension,is_hod,affiliation,note,source_url) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                         (f["department"], f["name"]) + vals)
            stats["faculty_new"] += 1
    return stats


async def link_club_faculty() -> dict:
    """Set club_people.faculty_id for faculty coordinators whose name matches exactly one directory entry.
    If two different coordinator names would claim the same entry (e.g. 'Alok Kumar' and 'Amit Kumar' vs 'A. Kumar')
    neither is linked — better no details than someone else's extension."""
    fac = [(r["id"], r["name"]) for r in await db.all("SELECT id, name FROM faculty")]
    names = [r["person_name"] for r in await db.all("SELECT DISTINCT person_name FROM club_people WHERE person_type='Faculty'")]
    if not fac or not names:
        return {"linked_names": 0, "unlinked_names": len(names)}
    pick = {n: best_unique(n, fac) for n in names}
    claims = {}
    for n, fid in pick.items():
        if fid is not None:
            claims.setdefault(fid, []).append(n)
    linked = 0
    for n, fid in pick.items():
        ok = fid is not None and len(claims[fid]) == 1
        await db.run("UPDATE club_people SET faculty_id=%s WHERE person_type='Faculty' AND person_name=%s", (fid if ok else None, n))
        linked += 1 if ok else 0
    return {"linked_names": linked, "unlinked_names": len(names) - linked}

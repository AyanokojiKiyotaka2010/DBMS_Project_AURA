"""Upsert clubs (+ their leaders / coordinators) — used by POST /api/admin/import-clubs."""
import db
from common_time import now_db


async def load_clubs(items, created_by=None):
    stats = {"clubs_new": 0, "clubs_updated": 0, "people_new": 0}
    for it in items:
        row = await db.one("SELECT id FROM clubs WHERE name=%s", (it["name"],))
        fields = (it.get("category", ""), it.get("entity_type", ""), it.get("description", ""),
                  it.get("website", ""), it.get("instagram", ""), it.get("linkedin", ""))
        if row:
            cid = row["id"]
            await db.run("UPDATE clubs SET category=%s, entity_type=%s, description=%s, website=%s, instagram=%s, linkedin=%s WHERE id=%s",
                         fields + (cid,))
            stats["clubs_updated"] += 1
        else:
            cid = await db.run(
                "INSERT INTO clubs (name,category,entity_type,description,website,instagram,linkedin,cover,created_by,created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'',%s,%s)", (it["name"],) + fields + (created_by, now_db()))
            stats["clubs_new"] += 1
        have = {(r["person_name"], r["title"], r["person_type"]) for r in
                await db.all("SELECT person_name, title, person_type FROM club_people WHERE club_id=%s", (cid,))}
        new = []
        for p in it.get("people", []):
            key = (p["person_name"], p["title"], p.get("person_type", "Student"))
            if key not in have:
                have.add(key)
                new.append((cid,) + key + (p.get("academic_year", ""),))
        if new:
            await db.many("INSERT INTO club_people (club_id,person_name,title,person_type,academic_year) VALUES (%s,%s,%s,%s,%s)", new)
        stats["people_new"] += len(new)
    return stats

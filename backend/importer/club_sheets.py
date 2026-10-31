"""Read SVNIT_Clubs_Chapters_Directory.xlsx -> list of club dicts (needs `pip install openpyxl`)."""
import re

LEADERSHIP = {"ACM": "C001", "DRISHTI": "C007", "ChES / AIChE": "C002", "CES": "C014", "IIW": "C012"}
PUBLISHED = {"IIW": "C012"}
FACULTY = {
    "ACM": "C001", "Centre for Human Resource Development (CHRD)": "C004", "Chemical Engineering Society (CHES)": "C002",
    "Chintan Pratishthan": "C005", "Civil Engineering Society (CES)": "C014",
    "Coordination Committee \u2013 Ministry-supported Programmes": "C031", "Cutting Edge Visionaries (CEV)": "C006",
    "DRISHTI": "C007", "Dasvidaniya \u2013 Farewell": "C029", "E-Cell": "C008", "Electrical Engineering Society (EES)": "C015",
    "Finance & Students\u2019 Welfare Committee": "C030", "GDSC": "C009", "IEEE": "C011", "IETE": "C010", "IIIE": "C013",
    "Indian Institute of Welding (IIW)": "C012", "Kashish \u2013 Freshers\u2019 Welcome": "C028",
    "Literary & Debating Committee (LAC)": "C016", "MINDBEND \u2013 Technical Event": "C026",
    "Magazine Committee / RENESA": "C019", "NIRVANA": "C017", "National Service Scheme (NSS)": "C032", "Physics Club": "C018",
    "SCOSH": "C021", "SPIC MACAY": "C022", "Social & Cultural Activities Committee": "C027",
    "Society of Automotive Engineers (SAE)": "C020", "Sports Committee": "C025", "Student Wellness Club": "C024",
    "Think India": "C023",
}


def _clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def parse_clubs(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    clubs, by_id = [], {}
    for r in wb["Club Directory"].iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        c = {"name": _clean(r[1])[:160], "entity_type": _clean(r[2])[:120], "category": _clean(r[3])[:80],
             "description": _clean(r[4]), "website": _clean(r[7])[:500], "instagram": _clean(r[8])[:500],
             "linkedin": _clean(r[9])[:500], "people": []}
        clubs.append(c)
        by_id[_clean(r[0])] = c
    unmatched = []

    def add(label, table, name, title, ptype, ay):
        cid = table.get(_clean(label))
        if not cid or cid not in by_id:
            unmatched.append(_clean(label))
            return
        if name and title:
            by_id[cid]["people"].append({"person_name": _clean(name)[:120], "title": _clean(title)[:120],
                                         "person_type": ptype, "academic_year": _clean(ay)[:40]})

    for r in wb["Leadership & Core Team"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            add(r[0], LEADERSHIP, r[1], r[2], "Student", r[3])
    for r in wb["Published Members"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            add(r[0], PUBLISHED, r[1], "Member", "Student", r[2])
    for r in wb["Faculty Coordinators"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            add(r[0], FACULTY, r[2], r[1], "Faculty", r[3])
    return clubs, sorted(set(unmatched))

"""HTTP layer for the role-scoped reports (the logic and SQL live in report_service.py).

GET /api/reports/scope             what the caller is locked to (pre-fills / disables filters in the UI)
GET /api/reports/cgpa              ?group_by=student|department|year|department_year|division
                                    &department_id&year_id&division_id&semester&cgpa_below&cgpa_above
GET /api/reports/course-average    ?semester | ?course_id  [&department_id&year_id&division_id]
GET /api/reports/backlogs          ?department_id&year_id&division_id&semester&course_id&min_backlogs
GET /api/reports/attendance-below  ?threshold=<0-100>&mode=overall|per_course
                                    &department_id&year_id&division_id&semester&course_id&date_from&date_to
"""
from fastapi import APIRouter, Depends, HTTPException, Request

import report_service as rs
from common import get_user

router = APIRouter(prefix="/reports")


async def _run(fn, user: dict, request: Request):
    try:
        return await fn(user, dict(request.query_params))
    except rs.ReportError as e:
        raise HTTPException(e.status, e.message)


@router.get("/scope")
async def scope(user=Depends(get_user)):
    try:
        s = rs.resolve_scope(user, {})
    except rs.ReportError as e:
        raise HTTPException(e.status, e.message)
    return {"role": user["role"], "scope": s, "locked": {k: v is not None for k, v in s.items()}}


@router.get("/cgpa")
async def cgpa(request: Request, user=Depends(get_user)):
    return await _run(rs.cgpa_report, user, request)


@router.get("/course-average")
async def course_average(request: Request, user=Depends(get_user)):
    return await _run(rs.course_average_report, user, request)


@router.get("/backlogs")
async def backlogs(request: Request, user=Depends(get_user)):
    return await _run(rs.backlog_report, user, request)


@router.get("/attendance-below")
async def attendance_below(request: Request, user=Depends(get_user)):
    return await _run(rs.attendance_below_report, user, request)

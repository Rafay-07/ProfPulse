"""The pages anyone can read: home, search, a professor and a course.

No login is needed for anything in this file.
"""

from flask import Blueprint, abort, jsonify, render_template, request, url_for

from . import config, stats
from .db import get_db

bp = Blueprint("browse", __name__)


@bp.route("/")
def home():
    db = get_db()
    return render_template(
        "home.html",
        top_tags=stats.tag_counts(limit=10),
        recent=stats.recent_reviews(),
        courses=db.execute("SELECT code, title FROM courses ORDER BY code").fetchall(),
        counts=db.execute(
            "SELECT (SELECT COUNT(*) FROM professors) AS professors, "
            "(SELECT COUNT(*) FROM courses) AS courses, "
            "(SELECT COUNT(*) FROM reviews WHERE is_hidden = 0) AS reviews"
        ).fetchone(),
    )


@bp.route("/search")
def search():
    """The full results page. Filters: text, department and tag."""
    query = request.args.get("q", "").strip()[:80]
    department = request.args.get("dept") or None
    tag = request.args.get("tag") or None
    if tag not in config.TAGS:      # ignore tags that are not on the list
        tag = None

    departments = [row["department"] for row in get_db().execute(
        "SELECT DISTINCT department FROM professors ORDER BY department")]
    if department not in departments:
        department = None

    return render_template(
        "search.html",
        query=query, department=department, tag=tag,
        departments=departments, all_tags=config.TAGS,
        results=stats.search_professors(query, department, tag),
    )


@bp.route("/api/search")
def api_search():
    """Live search. The search box calls this as you type and gets JSON back."""
    query = request.args.get("q", "").strip()[:80]
    if len(query) < 2:
        return jsonify(results=[])
    results = [
        {
            "name": professor["name"],
            "department": professor["department"],
            "courses": professor["courses"],
            "overall": None if professor["overall"] is None else round(professor["overall"], 1),
            "reviews": professor["n"],
            "url": url_for("browse.professor", professor_id=professor["id"]),
        }
        for professor in stats.search_professors(query, limit=6)
    ]
    return jsonify(results=results)


@bp.route("/professors/<int:professor_id>")
def professor(professor_id):
    """One professor. ?course= narrows the numbers to one course,
    ?tag= narrows the review list to one tag, ?sort= reorders the list."""
    db = get_db()
    person = db.execute("SELECT * FROM professors WHERE id = ?", (professor_id,)).fetchone()
    if person is None:
        abort(404)

    courses = db.execute(
        "SELECT c.id, c.code, c.title FROM teaches te JOIN courses c ON c.id = te.course_id "
        "WHERE te.professor_id = ? ORDER BY c.code",
        (professor_id,),
    ).fetchall()

    # Read the filters, ignoring anything that is not a real option.
    course = next((c for c in courses if c["code"] == request.args.get("course")), None)
    course_id = course["id"] if course else None
    tag = request.args.get("tag")
    if tag not in config.TAGS:
        tag = None
    sort = request.args.get("sort", "newest")
    if sort not in ("newest", "highest", "lowest"):
        sort = "newest"

    trend = stats.term_trend(professor_id, course_id)
    return render_template(
        "professor.html",
        person=person, courses=courses, course=course, tag=tag, sort=sort,
        summary=stats.summary(professor_id, course_id),
        tags=stats.tag_counts(professor_id, course_id),
        chart=stats.trend_chart(trend) if trend else None,
        reviews=stats.reviews_for(professor_id, course_id, tag, sort),
        report_reasons=config.REPORT_REASONS,
    )


@bp.route("/courses/<code>")
def course(code):
    """One course: everyone who teaches it, ranked by their score for it."""
    row = get_db().execute("SELECT * FROM courses WHERE code = ?", (code,)).fetchone()
    if row is None:
        abort(404)
    return render_template("course.html", course=row, ranking=stats.course_ranking(row["id"]))

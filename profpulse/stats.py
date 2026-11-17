"""The queries behind the numbers: averages, tag counts, trends and search.

Kept apart from the page code so each query can be read, and tested, alone.

A note on the f-strings below: the only things placed into the SQL text are
column names taken from config.CATEGORY_KEYS, a fixed list in this project.
Anything a visitor typed always goes in through "?" parameters.
"""

from . import config
from .db import get_db

# The overall score of one review: the mean of its five category scores.
OVERALL = "(" + " + ".join(f"r.{key}" for key in config.CATEGORY_KEYS) + f") / {len(config.CATEGORY_KEYS)}.0"

# Reused by the queries that filter reviews by a tag name.
HAS_TAG = (
    "r.id IN (SELECT rt.review_id FROM review_tags rt "
    "JOIN tags t ON t.id = rt.tag_id WHERE t.name = ?)"
)


def _where(professor_id=None, course_id=None, tag=None):
    """Builds the WHERE clause shared by the queries below.

    Hidden (reported) reviews are always left out.
    Returns the SQL text and the list of values for its "?" marks.
    """
    parts, values = ["r.is_hidden = 0"], []
    if professor_id is not None:
        parts.append("r.professor_id = ?")
        values.append(professor_id)
    if course_id is not None:
        parts.append("r.course_id = ?")
        values.append(course_id)
    if tag:
        parts.append(HAS_TAG)
        values.append(tag)
    return " AND ".join(parts), values


def summary(professor_id, course_id=None):
    """Review count, overall average and the five category averages.

    With course_id, only reviews for that course are counted. This is the
    course-specific rating.
    """
    where, values = _where(professor_id, course_id)
    category_columns = ", ".join(f"AVG(r.{key}) AS {key}" for key in config.CATEGORY_KEYS)
    return get_db().execute(
        f"SELECT COUNT(*) AS n, AVG({OVERALL}) AS overall, {category_columns} "
        f"FROM reviews r WHERE {where}",
        values,
    ).fetchone()


def tag_counts(professor_id=None, course_id=None, limit=None):
    """How often each tag was used, most used first.

    Each tag also gets a size from 1 to 4 for the tag cloud.
    """
    where, values = _where(professor_id, course_id)
    sql = (
        "SELECT t.name, COUNT(*) AS n FROM review_tags rt "
        "JOIN tags t ON t.id = rt.tag_id "
        "JOIN reviews r ON r.id = rt.review_id "
        f"WHERE {where} GROUP BY t.name ORDER BY n DESC, t.name"
    )
    if limit:
        sql += " LIMIT ?"
        values.append(limit)
    rows = get_db().execute(sql, values).fetchall()
    biggest = rows[0]["n"] if rows else 1
    return [
        {"name": row["name"], "n": row["n"], "size": 1 + round(3 * row["n"] / biggest)}
        for row in rows
    ]


def term_trend(professor_id, course_id=None):
    """Average overall score per term, oldest term first."""
    where, values = _where(professor_id, course_id)
    rows = get_db().execute(
        f"SELECT r.term, COUNT(*) AS n, AVG({OVERALL}) AS overall "
        f"FROM reviews r WHERE {where} GROUP BY r.term",
        values,
    ).fetchall()
    return sorted(rows, key=lambda row: config.term_sort_key(row["term"]))


def trend_chart(trend, width=340, height=130):
    """Turns the trend rows into coordinates for a small SVG line chart.

    The y axis always runs from 1 to 5 so charts for different professors
    can be compared by eye.
    """
    left, right, top, bottom = 28, 14, 14, 26
    usable_w, usable_h = width - left - right, height - top - bottom
    points = []
    for index, row in enumerate(trend):
        # Spread the terms evenly. A single term sits in the middle.
        x = left + (usable_w / 2 if len(trend) == 1 else usable_w * index / (len(trend) - 1))
        y = top + usable_h * (5 - row["overall"]) / 4
        points.append({"x": round(x, 1), "y": round(y, 1), "term": row["term"],
                       "overall": row["overall"], "n": row["n"]})
    gridlines = [{"score": score, "y": round(top + usable_h * (5 - score) / 4, 1)} for score in (1, 3, 5)]
    return {
        "width": width, "height": height, "left": left, "right": width - right,
        "label_y": height - 8, "points": points, "gridlines": gridlines,
        "line": " ".join(f"{p['x']},{p['y']}" for p in points),
    }


def reviews_for(professor_id, course_id=None, tag=None, sort="newest"):
    """The visible reviews for a professor, each with its list of tags."""
    where, values = _where(professor_id, course_id, tag)
    # The sort choice picks one of three fixed strings. It is never placed
    # into the SQL directly.
    order = {
        "newest": "r.created_at DESC, r.id DESC",
        "highest": "overall DESC, r.created_at DESC",
        "lowest": "overall ASC, r.created_at DESC",
    }.get(sort, "r.created_at DESC, r.id DESC")
    db = get_db()
    rows = db.execute(
        f"SELECT r.*, {OVERALL} AS overall, c.code AS course_code "
        f"FROM reviews r JOIN courses c ON c.id = r.course_id "
        f"WHERE {where} ORDER BY {order}",
        values,
    ).fetchall()

    # Fetch the tags for all of these reviews in one query, then group them.
    tags_by_review = {}
    if rows:
        marks = ", ".join("?" for _ in rows)
        for tag_row in db.execute(
            f"SELECT rt.review_id, t.name FROM review_tags rt JOIN tags t ON t.id = rt.tag_id "
            f"WHERE rt.review_id IN ({marks}) ORDER BY t.name",
            [row["id"] for row in rows],
        ):
            tags_by_review.setdefault(tag_row["review_id"], []).append(tag_row["name"])

    return [dict(row, tags=tags_by_review.get(row["id"], [])) for row in rows]


def _escape_like(text):
    """Escapes the characters LIKE treats as wildcards, so they match themselves."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _anywhere(text):
    """LIKE pattern: the text appears anywhere."""
    return f"%{_escape_like(text)}%"


def _word_start(text):
    """Two LIKE patterns: the text starts the value, or starts a later word in it.

    Used for departments and course titles. Matching anywhere would be too
    loose there: "cs" would match "Mathematics" and "Statistics".
    """
    escaped = _escape_like(text)
    return [f"{escaped}%", f"% {escaped}%"]


def search_professors(query="", department=None, tag=None, limit=None):
    """Finds professors by name, department, course code or course title.

    Results carry the review count and overall average, most reviewed first.
    "cs110" and "CS 110" both match the course code "CS 110".
    """
    parts, values = [], []
    query = (query or "").strip()
    if query:
        parts.append(
            "(p.name LIKE ? ESCAPE '\\' "
            "OR p.department LIKE ? ESCAPE '\\' OR p.department LIKE ? ESCAPE '\\' "
            "OR p.id IN ("
            "SELECT te.professor_id FROM teaches te JOIN courses c ON c.id = te.course_id "
            "WHERE REPLACE(c.code, ' ', '') LIKE ? ESCAPE '\\' "
            "OR c.title LIKE ? ESCAPE '\\' OR c.title LIKE ? ESCAPE '\\'))"
        )
        values += (
            [_anywhere(query)] + _word_start(query)
            + [_anywhere(query.replace(" ", ""))] + _word_start(query)
        )
    if department:
        parts.append("p.department = ?")
        values.append(department)
    if tag:
        parts.append(f"p.id IN (SELECT r.professor_id FROM reviews r WHERE r.is_hidden = 0 AND {HAS_TAG})")
        values.append(tag)

    sql = (
        "SELECT p.id, p.name, p.department, "
        "(SELECT COUNT(*) FROM reviews r WHERE r.professor_id = p.id AND r.is_hidden = 0) AS n, "
        f"(SELECT AVG({OVERALL}) FROM reviews r WHERE r.professor_id = p.id AND r.is_hidden = 0) AS overall "
        "FROM professors p"
    )
    if parts:
        sql += " WHERE " + " AND ".join(parts)
    sql += " ORDER BY n DESC, p.name"
    if limit:
        sql += " LIMIT ?"
        values.append(limit)

    db = get_db()
    professors = [dict(row) for row in db.execute(sql, values).fetchall()]

    # Attach each professor's course codes with one extra query.
    courses_by_professor = {}
    for row in db.execute(
        "SELECT te.professor_id, c.code FROM teaches te JOIN courses c ON c.id = te.course_id ORDER BY c.code"
    ):
        courses_by_professor.setdefault(row["professor_id"], []).append(row["code"])
    for professor in professors:
        professor["courses"] = courses_by_professor.get(professor["id"], [])
    return professors


def course_ranking(course_id):
    """Everyone who teaches a course, with their scores for that course only."""
    category_columns = ", ".join(f"AVG(r.{key}) AS {key}" for key in config.CATEGORY_KEYS)
    return get_db().execute(
        f"SELECT p.id, p.name, p.department, COUNT(r.id) AS n, AVG({OVERALL}) AS overall, {category_columns} "
        "FROM teaches te JOIN professors p ON p.id = te.professor_id "
        "LEFT JOIN reviews r ON r.professor_id = p.id AND r.course_id = te.course_id AND r.is_hidden = 0 "
        "WHERE te.course_id = ? GROUP BY p.id "
        "ORDER BY overall IS NULL, overall DESC, p.name",
        (course_id,),
    ).fetchall()


def recent_reviews(limit=4):
    """The newest visible reviews across the whole site, for the home page."""
    return get_db().execute(
        f"SELECT r.id, r.body, r.term, {OVERALL} AS overall, p.id AS professor_id, "
        "p.name AS professor_name, c.code AS course_code "
        "FROM reviews r JOIN professors p ON p.id = r.professor_id "
        "JOIN courses c ON c.id = r.course_id "
        "WHERE r.is_hidden = 0 ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
        (limit,),
    ).fetchall()

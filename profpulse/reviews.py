"""Writing a review, and reporting one.

Both need a logged-in user with a verified school email.
The browser also checks the form (see static/js/review.js), but that is only
for convenience. Every rule is checked again here, because anything sent
from a browser can be faked.
"""

import sqlite3

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import config
from .db import get_db
from .security import record_event, too_many, verified_required

bp = Blueprint("reviews", __name__)


def _read_review_form(form, course_ids):
    """Checks the submitted review. Returns (clean_values, list_of_errors)."""
    errors = []

    course_id = form.get("course_id", type=int)
    if course_id not in course_ids:
        errors.append("Pick one of the courses this professor teaches.")

    term = form.get("term", "")
    if term not in config.TERMS:
        errors.append("Pick the term you took the course.")

    scores = {}
    for key, label, _question in config.CATEGORIES:
        value = form.get(key, type=int)
        if value is None or not 1 <= value <= 5:
            errors.append(f"Give a score from 1 to 5 for {label}.")
        scores[key] = value

    # Keep only tags that are on the list, without repeats.
    tags = [tag for tag in dict.fromkeys(form.getlist("tags")) if tag in config.TAGS]
    if len(tags) > config.MAX_TAGS_PER_REVIEW:
        errors.append(f"Pick at most {config.MAX_TAGS_PER_REVIEW} tags.")

    body = " ".join(form.get("body", "").split())    # collapse runs of spaces and newlines
    if not config.REVIEW_MIN_CHARS <= len(body) <= config.REVIEW_MAX_CHARS:
        errors.append(
            f"The review needs between {config.REVIEW_MIN_CHARS} and {config.REVIEW_MAX_CHARS} characters."
        )

    return {"course_id": course_id, "term": term, "scores": scores, "tags": tags, "body": body}, errors


@bp.route("/professors/<int:professor_id>/review", methods=("GET", "POST"))
@verified_required
def write(professor_id):
    db = get_db()
    person = db.execute("SELECT * FROM professors WHERE id = ?", (professor_id,)).fetchone()
    if person is None:
        abort(404)
    courses = db.execute(
        "SELECT c.id, c.code, c.title FROM teaches te JOIN courses c ON c.id = te.course_id "
        "WHERE te.professor_id = ? ORDER BY c.code",
        (professor_id,),
    ).fetchall()

    # What the form shows. On a GET it is empty, apart from a course picked
    # on the professor page (?course=CS 110).
    picked = next((c["id"] for c in courses if c["code"] == request.args.get("course")), None)
    values = {"course_id": picked, "term": config.TERMS[0], "scores": {}, "tags": [], "body": ""}

    if request.method == "POST":
        values, errors = _read_review_form(request.form, {c["id"] for c in courses})
        if not errors and too_many("review", g.user["id"], config.REVIEW_LIMIT):
            errors.append("You have posted several reviews today. Try again tomorrow.")

        if not errors:
            try:
                score_columns = ", ".join(config.CATEGORY_KEYS)
                score_marks = ", ".join("?" for _ in config.CATEGORY_KEYS)
                cursor = db.execute(
                    f"INSERT INTO reviews (professor_id, course_id, user_id, term, {score_columns}, body) "
                    f"VALUES (?, ?, ?, ?, {score_marks}, ?)",
                    [professor_id, values["course_id"], g.user["id"], values["term"]]
                    + [values["scores"][key] for key in config.CATEGORY_KEYS]
                    + [values["body"]],
                )
                for tag in values["tags"]:
                    db.execute(
                        "INSERT INTO review_tags (review_id, tag_id) "
                        "SELECT ?, id FROM tags WHERE name = ?",
                        (cursor.lastrowid, tag),
                    )
                db.commit()
            except sqlite3.IntegrityError:
                # The UNIQUE rule in schema.sql fired.
                db.rollback()
                errors.append("You already reviewed this professor for that course and term.")
            else:
                record_event("review", g.user["id"])
                flash("Your review is posted. Thank you.", "ok")
                return redirect(url_for("browse.professor", professor_id=professor_id))

        for error in errors:
            flash(error, "error")

    return render_template(
        "review_form.html",
        person=person, courses=courses, values=values,
        terms=config.TERMS, all_tags=config.TAGS,
        max_tags=config.MAX_TAGS_PER_REVIEW,
        min_chars=config.REVIEW_MIN_CHARS, max_chars=config.REVIEW_MAX_CHARS,
    )


@bp.route("/reviews/<int:review_id>/report", methods=("POST",))
@verified_required
def report(review_id):
    """Flags a review. After enough different students flag it, it is hidden."""
    db = get_db()
    review = db.execute("SELECT id, professor_id FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if review is None:
        abort(404)

    reason = request.form.get("reason", "")
    if reason not in dict(config.REPORT_REASONS):
        flash("Pick a reason for the report.", "error")
    elif too_many("report", g.user["id"], config.REPORT_LIMIT):
        flash("You have sent many reports today. Try again tomorrow.", "error")
    else:
        # OR IGNORE: reporting the same review twice counts once.
        db.execute(
            "INSERT OR IGNORE INTO reports (review_id, user_id, reason) VALUES (?, ?, ?)",
            (review_id, g.user["id"], reason),
        )
        count = db.execute("SELECT COUNT(*) FROM reports WHERE review_id = ?", (review_id,)).fetchone()[0]
        if count >= config.REPORTS_TO_HIDE:
            db.execute("UPDATE reviews SET is_hidden = 1 WHERE id = ?", (review_id,))
        db.commit()
        record_event("report", g.user["id"])
        flash("Thanks. The review has been flagged.", "ok")

    return redirect(url_for("browse.professor", professor_id=review["professor_id"]))

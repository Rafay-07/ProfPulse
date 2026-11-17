"""Posting and reporting reviews."""

from conftest import first_course_id, login, make_verified_user, post, register, review_form

from profpulse import stats
from profpulse.db import get_db

FORM = "/professors/1/review"


def count_reviews(app, professor_id=1):
    with app.app_context():
        return stats.summary(professor_id)["n"]


def test_must_be_logged_in(client):
    response = client.get(FORM)
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_unverified_account_cannot_post(app, client):
    register(client)
    login(client)                      # logged in, but the email is not verified
    before = count_reviews(app)
    response = client.get(FORM)
    assert response.status_code == 302 and response.headers["Location"].endswith("/verify-sent")
    assert count_reviews(app) == before


def test_verified_user_can_post_and_averages_update(app, client):
    make_verified_user(client)
    course_id = first_course_id(app)
    with app.app_context():
        before = stats.summary(1, course_id)

    response = post(client, FORM, review_form(course_id), token_from=FORM)
    assert response.status_code == 302

    with app.app_context():
        after = stats.summary(1, course_id)
        newest = stats.reviews_for(1, course_id)[0]
    assert after["n"] == before["n"] + 1
    # The new clarity average is the old total plus the new score of 5.
    expected = (before["clarity"] * before["n"] + 5) / after["n"]
    assert abs(after["clarity"] - expected) < 1e-9
    assert newest["overall"] == (5 + 4 + 3 + 4 + 4) / 5
    assert newest["tags"] == ["clear lectures", "fair exams"]


def test_review_page_does_not_show_the_author(app, client):
    make_verified_user(client, "private.person@uoguelph.ca")
    post(client, FORM, review_form(first_course_id(app)), token_from=FORM)
    post(client, "/logout", token_from="/")
    page = client.get("/professors/1").get_data(as_text=True)
    assert "private.person" not in page


def test_same_course_and_term_twice_is_refused(app, client):
    make_verified_user(client)
    course_id = first_course_id(app)
    post(client, FORM, review_form(course_id), token_from=FORM)
    before = count_reviews(app)
    page = post(client, FORM, review_form(course_id), token_from=FORM).get_data(as_text=True)
    assert "You already reviewed this professor" in page
    assert count_reviews(app) == before


def test_bad_input_is_refused(app, client):
    make_verified_user(client)
    course_id = first_course_id(app)
    before = count_reviews(app)
    bad_forms = [
        review_form(course_id, clarity=6),                          # score out of range
        review_form(course_id, fairness="lots"),                    # not a number
        review_form(course_id, body="Too short."),                  # under the minimum
        review_form(course_id, term="X99"),                         # not a real term
        review_form(8),                                             # a course this professor does not teach
        review_form(course_id, tags=["clear lectures", "fair exams", "engaging", "group projects", "tough grader"]),
    ]
    for form in bad_forms:
        post(client, FORM, form, token_from=FORM)
    assert count_reviews(app) == before


def test_unknown_tags_are_dropped(app, client):
    make_verified_user(client)
    course_id = first_course_id(app)
    post(client, FORM, review_form(course_id, tags=["engaging", "<script>alert(1)</script>"]), token_from=FORM)
    with app.app_context():
        assert stats.reviews_for(1, course_id)[0]["tags"] == ["engaging"]


def test_review_text_is_escaped(app, client):
    """HTML typed into a review is shown as text, never run."""
    make_verified_user(client)
    body = "<script>alert('x')</script> This professor explains every topic clearly."
    post(client, FORM, review_form(first_course_id(app), body=body), token_from=FORM)
    page = client.get("/professors/1").get_data(as_text=True)
    assert "<script>alert" not in page
    assert "&lt;script&gt;alert" in page


def test_review_is_hidden_after_three_reports(app, client):
    with app.app_context():
        review_id = stats.reviews_for(1)[0]["id"]
    before = count_reviews(app)

    for number in range(3):
        make_verified_user(client, f"reporter{number}@uoguelph.ca")
        post(client, f"/reviews/{review_id}/report", {"reason": "personal"}, token_from="/")
        # Reporting twice from one account still counts once.
        post(client, f"/reviews/{review_id}/report", {"reason": "personal"}, token_from="/")
        post(client, "/logout", token_from="/")
        if number < 2:
            assert count_reviews(app) == before

    assert count_reviews(app) == before - 1
    with app.app_context():
        assert get_db().execute("SELECT is_hidden FROM reviews WHERE id = ?", (review_id,)).fetchone()[0] == 1

"""The public pages: home, search, tag filtering, a professor, a course."""

from profpulse import stats


def test_pages_load(client):
    for path in ("/", "/search", "/professors/1", "/courses/CS 110", "/login", "/register"):
        assert client.get(path).status_code == 200, path


def test_professor_page_shows_all_five_categories(client):
    page = client.get("/professors/1").get_data(as_text=True)
    panel = page.split('class="cats"')[1].split("</dl>")[0]
    for label in ("Clarity", "Helpfulness", "Fair grading", "Engagement", "Organization"):
        assert label in panel


def test_unknown_pages_are_404(client):
    assert client.get("/professors/9999").status_code == 404
    assert client.get("/courses/NOPE 000").status_code == 404


def test_search_by_name(client):
    page = client.get("/search?q=vasquez").get_data(as_text=True)
    assert "Dr. Imani Vasquez-Holt" in page
    assert "Dr. Tobias Renwick" not in page


def test_search_by_course_code_ignores_spaces(client):
    """Typing "cs110" finds everyone who teaches CS 110."""
    page = client.get("/search?q=cs110").get_data(as_text=True)
    assert "Dr. Imani Vasquez-Holt" in page
    assert "Dr. Tobias Renwick" in page
    assert "Dr. Samuel Achterberg" not in page     # teaches STAT 205 only


def test_search_matches_departments_and_titles_by_word(client):
    """"cs" finds CS courses, but not "Mathematics" or "Statistics" by accident."""
    page = client.get("/search?q=cs").get_data(as_text=True)
    assert "Dr. Imani Vasquez-Holt" in page
    assert "Dr. Henrik Oyelaran" not in page       # Mathematics, MATH courses only
    assert "Dr. Samuel Achterberg" not in page     # Statistics, STAT 205 only
    # A word in the middle of a title still matches.
    assert "Dr. Priya Nakagawa" in client.get("/search?q=design").get_data(as_text=True)


def test_search_treats_wildcards_as_plain_text(client):
    """A "%" in the search box must not match everything."""
    page = client.get("/search?q=%25").get_data(as_text=True)
    assert "0 professors found" in page


def test_search_filters_by_tag(app, client):
    page = client.get("/search?tag=reads the slides").get_data(as_text=True)
    assert "Dr. Tobias Renwick" in page
    assert "Dr. Samuel Achterberg" not in page


def test_live_search_returns_json(client):
    data = client.get("/api/search?q=calc").get_json()
    names = [result["name"] for result in data["results"]]
    assert "Dr. Henrik Oyelaran" in names             # teaches Calculus I
    assert all(result["url"].startswith("/professors/") for result in data["results"])
    assert client.get("/api/search?q=a").get_json() == {"results": []}   # too short


def test_ratings_are_course_specific(app):
    """The numbers for one course only count reviews for that course."""
    with app.app_context():
        everything = stats.summary(1)
        one_course = stats.summary(1, course_id=1)
        other_course = stats.summary(1, course_id=2)
    assert one_course["n"] + other_course["n"] == everything["n"]
    assert one_course["n"] > 0 and other_course["n"] > 0


def test_tag_filter_on_professor_page(app, client):
    """?tag= narrows the review list to reviews carrying that tag."""
    with app.app_context():
        all_reviews = stats.reviews_for(1)
        tagged = stats.reviews_for(1, tag="engaging")
    assert 0 < len(tagged) < len(all_reviews)
    assert all("engaging" in review["tags"] for review in tagged)
    page = client.get("/professors/1?tag=engaging").get_data(as_text=True)
    assert "Showing only reviews tagged" in page


def test_trend_is_in_term_order(app):
    with app.app_context():
        terms = [row["term"] for row in stats.term_trend(1)]
    assert terms == sorted(terms, key=lambda code: (int(code[1:]), "WSF".index(code[0])))


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"


def test_behind_proxy_uses_the_forwarded_address(tmp_path):
    """On a host, the rate limits must see each visitor's address, not the proxy's."""
    from flask import request

    from profpulse import create_app

    app = create_app({"TESTING": True, "SECRET_KEY": "x", "BEHIND_PROXY": True,
                      "DATABASE": str(tmp_path / "proxy.sqlite")})

    @app.route("/whoami-test")
    def whoami_test():
        return request.remote_addr + " " + request.scheme

    reply = app.test_client().get("/whoami-test", headers={
        "X-Forwarded-For": "203.0.113.5", "X-Forwarded-Proto": "https"})
    assert reply.get_data(as_text=True) == "203.0.113.5 https"
    assert app.config["SESSION_COOKIE_SECURE"] is True

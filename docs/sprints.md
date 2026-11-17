# Sprints

The project moves from a front-end prototype to a working backend in four sprints after Sprint 0. Each sprint has one goal and a short list of what it delivers.

## Sprint 0: prototype

**Goal:** check the user flows before writing any backend.

- One HTML file with several views, in plain HTML, CSS and JavaScript
- Real-time search, five-category ratings, a tag cloud and a review form
- No backend. The data lived in the page.

## Sprint 1: backend foundation

**Goal:** the pages read from a database instead of data in the page.

- Flask app structure
- SQLite schema: professors, courses, teaches, reviews, tags, review_tags
- Professor page and course page served from the database
- Sample data script

## Sprint 2: accounts and posting

**Goal:** only verified students at the school can post.

- Sign up limited to the school email domain
- Passwords stored as salted hashes
- Verification link with an expiring, single-use token
- Review form, with every rule checked on the server

## Sprint 3: search, tags and trends

**Goal:** make the ratings easy to find and to read.

- Search by name, department, course code and title, on the server
- Live results through a small JSON endpoint
- Tag cloud, and filtering reviews by tag
- Averages per category and a trend by term

## Sprint 4: hardening

**Goal:** make it safe to put in front of strangers, and documented.

- CSRF tokens, security headers, rate limits
- Reporting, with automatic hiding after three reports
- Automated tests
- README, design notes, this file

## Next

The remaining work is in the "To do" table of [backlog.md](backlog.md). Real email and hosting come first.

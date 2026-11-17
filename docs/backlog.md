# Product backlog

Ordered by priority. Story numbers refer to [user-stories.md](user-stories.md). Sprints are described in [sprints.md](sprints.md).

## Done

| Item | Story | Sprint |
| --- | --- | --- |
| Front-end prototype: search, five-category ratings, tag cloud, review form | US-1, US-4, US-6, US-9 | 0 |
| Flask app and SQLite schema for professors, courses, reviews and tags | US-4, US-5 | 1 |
| Professor page reading from the database | US-4 | 1 |
| Course-specific numbers and the course ranking page | US-3, US-5 | 1 |
| Sample data script | | 1 |
| Sign up limited to the school email domain | US-8 | 2 |
| Password hashing | US-8 | 2 |
| Email verification link (token, expiry, single use) | US-8 | 2 |
| Posting restricted to verified accounts | US-8, US-9 | 2 |
| Review form with server-side checks | US-9 | 2 |
| Search on the server, with a live-search endpoint | US-1, US-2 | 3 |
| Tag cloud and tag filtering | US-6 | 3 |
| Per-category averages and overall score | US-4 | 3 |
| Trend by term | US-7 | 3 |
| CSRF tokens on every form | US-12 | 4 |
| Rate limits on login, sign-up, reviews and reports | US-12 | 4 |
| Reporting, and hiding a review after three reports | US-11 | 4 |
| Automated tests | | 4 |
| README and design notes | | 4 |

## To do

| Priority | Item | Notes |
| --- | --- | --- |
| 1 | Send the verification email through a real mail service | One function to replace in `auth.py` |
| 2 | Host the site | Needs a production server and HTTPS |
| 3 | Admin page to review reports and restore or remove reviews | Reports are stored already |
| 4 | Let students suggest a missing professor or course | Needs approval before it shows |
| 5 | Edit or delete your own review | |
| 6 | Password reset by email | Depends on item 1 |
| 7 | Sort search results by score | |
| 8 | Add the Sprint 0 prototype file to the repository | See `prototype/README.md` |

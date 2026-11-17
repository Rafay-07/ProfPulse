# Design notes

Why ProfPulse is built the way it is. Each section is one decision and the reason for it.

## A review belongs to a professor and a course

This is the idea the whole project rests on. The `reviews` table has both a `professor_id` and a `course_id`. Because of that:

- the professor page can show one set of numbers for all courses, or for one course
- the course page can rank everyone who teaches that course by how they do in it

The `teaches` table lists which professor teaches which course. The review form only offers those courses, and the server checks the choice again.

## Five scores as five columns

Each review stores five whole numbers from 1 to 5, one column per category. The alternative was a separate table with one row per score. Five columns won because the queries stay simple: an average is `AVG(clarity)`.

The cost is that replacing a category means changing a column name in `schema.sql`. The category names and labels live in one list in `config.py`, and the queries are built from that list, so nothing else needs to change.

All five run the same way, 1 is worst and 5 is best. That is what makes it fair to average them into one overall score. A category like "difficulty" was left out for this reason: a high number there is not clearly good or bad.

## Tags come from a fixed list

Reviewers tick tags from a list of twelve. They cannot type their own. This keeps the tag cloud readable, makes filtering exact, and removes a place where someone could write an insult.

## Server-rendered pages, with a little JavaScript

Flask builds each page as HTML. JavaScript is used in two places:

- the live search on the home page, which calls `/api/search` and lists the matches
- the review form, for a character count and the tag limit

Both still work with JavaScript off: the search box submits to the results page, and the server enforces every form rule. Filters are plain links and GET forms, so any filtered view has its own address that can be bookmarked or shared.

## Charts without a library

The score bars and the trend chart are small SVGs. The server works out the coordinates in `stats.trend_chart()` and the template draws them. This avoided a chart library, and it also means no inline styles, which keeps the content security policy strict.

## School email verification

The rule is that only students at the school can post. The app checks this in two steps:

1. The email must end in the school's domain. The check is `endswith("@uoguelph.ca")`, not "contains", so `someone@uoguelph.ca.evil.com` is refused.
2. The account must open a link sent to that address before it can post. This proves the person can read the inbox.

The link holds a random token. The database stores a hash of the token, so a copy of the database could not be used to verify accounts. The token expires after 24 hours and is cleared when used.

Sending real email is the one part not connected. It is isolated in a single function so it can be added without touching the rest.

## Reviews are anonymous to readers, not to the system

A review is stored with the account that wrote it. That is needed to enforce one review per course per term, and to rate limit. The pages never show the author.

## Rate limits in the database

Each limited action writes a row to `rate_events`. Checking a limit is a count of recent rows. This is simple and survives a restart. A larger site would use something faster, but for one SQLite file this is enough.

## Reports hide a review automatically

After three different students report a review, it is marked hidden and dropped from every page and every average. There is no admin page yet to look at the reports, which is on the backlog.

## What was reused

The account code follows the same approach as my `secure-auth-api` project: scrypt password hashes and rate limits on login.

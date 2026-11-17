# User stories

Each story is written from the point of view of the person using the site. The "done when" lines are the acceptance criteria.

## Finding a professor

**US-1. Search.** As a student, I want to search by a professor's name or a course code, so that I can find who I am looking for quickly.
- Done when: typing part of a name, a department, a course code or a course title lists the matching professors.
- Done when: "cs110" and "CS 110" give the same results.

**US-2. Live results.** As a student, I want results to appear while I type, so that I do not have to submit the search first.
- Done when: results show under the search box after two characters, and pressing Enter still opens the full results page.

**US-3. Browse by course.** As a student choosing a section, I want to see everyone who teaches a course side by side, so that I can compare them for that course.
- Done when: the course page ranks its professors by their score in that course only.

## Reading ratings

**US-4. Five categories.** As a student, I want ratings split into five categories, so that I can tell a clear lecturer from a fair marker.
- Done when: a professor page shows the average for each of the five categories and an overall score.

**US-5. Course-specific ratings.** As a student, I want to see a professor's ratings for one course, so that reviews from a different course do not mislead me.
- Done when: picking a course on the professor page changes the numbers, the tags and the review list to that course.

**US-6. Tag filtering.** As a student, I want to filter reviews by a tag, so that I can read only the ones about what I care about.
- Done when: clicking a tag in the tag cloud shows only reviews with that tag, and one click clears the filter.
- Done when: the search page can list the professors who have reviews with a chosen tag.

**US-7. Trend.** As a student, I want to see how a professor's ratings changed over terms, so that I know whether old reviews still apply.
- Done when: the professor page charts the average overall score per term, in term order.

## Writing reviews

**US-8. School accounts.** As a student, I want only verified students at my school to post, so that I can trust the reviews.
- Done when: an account needs an email at the school's domain.
- Done when: an account cannot post until it has opened the verification link.

**US-9. Post a review.** As a verified student, I want to rate a professor for a course I took, so that others can benefit.
- Done when: the form takes a course, a term, five scores, up to four tags and a written review.
- Done when: a second review for the same professor, course and term is refused.

**US-10. Anonymous.** As a reviewer, I want my name hidden, so that I can be honest.
- Done when: no page shows who wrote a review.

## Keeping it clean

**US-11. Report.** As a student, I want to report a review that attacks someone, so that it gets taken down.
- Done when: a verified student can report a review with a reason.
- Done when: a review reported by three different students is hidden from pages and averages.

**US-12. Limits.** As the site owner, I want limits on logins and posting, so that one person cannot flood the site or guess passwords.
- Done when: repeated failed logins, sign-ups, reviews and reports are refused after a set number.

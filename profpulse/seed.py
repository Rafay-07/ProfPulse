"""Made-up sample data, so the site has something to show.

Every professor, course and review here is invented. Nothing was copied
from Rate My Professors or from any real course list.

The same data is produced every time, because the random generator is
started from a fixed number.
"""

import random

from . import config
from .db import get_db

COURSES = [
    ("CS 110", "Introduction to Programming"),
    ("CS 215", "Data Structures"),
    ("CS 240", "Computer Organization"),
    ("CS 330", "Software Design"),
    ("MATH 120", "Calculus I"),
    ("MATH 221", "Linear Algebra"),
    ("STAT 205", "Statistics for Science"),
    ("ENGR 150", "Engineering Design"),
]

# name, department, courses taught, typical score for each of the five
# categories (in the order of config.CATEGORIES), and the tags students
# tend to give them.
PROFESSORS = [
    ("Dr. Imani Vasquez-Holt", "Computer Science", ["CS 110", "CS 215"],
     [5, 5, 4, 5, 4], ["clear lectures", "helpful office hours", "practical examples", "engaging"]),
    ("Dr. Tobias Renwick", "Computer Science", ["CS 110", "CS 240"],
     [3, 2, 3, 2, 4], ["reads the slides", "tough grader", "attendance matters"]),
    ("Dr. Priya Nakagawa", "Computer Science", ["CS 215", "CS 330"],
     [4, 4, 3, 4, 5], ["group projects", "heavy workload", "practical examples", "fast feedback"]),
    ("Dr. Wendell Fairbanks", "Computer Science", ["CS 330", "CS 110"],
     [4, 3, 4, 3, 3], ["fair exams", "lots of homework", "clear lectures"]),
    ("Dr. Henrik Oyelaran", "Mathematics", ["MATH 120", "MATH 221"],
     [4, 4, 5, 3, 5], ["fair exams", "clear lectures", "fast feedback"]),
    ("Dr. Lucia Brandvold", "Mathematics", ["MATH 120", "STAT 205"],
     [2, 3, 2, 2, 3], ["tough grader", "heavy workload", "lots of homework"]),
    ("Dr. Samuel Achterberg", "Statistics", ["STAT 205"],
     [5, 4, 4, 4, 4], ["practical examples", "engaging", "fair exams"]),
    ("Dr. Noor Castellanos", "Engineering", ["ENGR 150", "CS 240"],
     [3, 5, 4, 4, 3], ["group projects", "helpful office hours", "attendance matters"]),
]

# Review sentences, grouped by how the reviewer felt overall.
SENTENCES = {
    "good": [
        "Explains each idea twice in different ways, which helped a lot before the midterm.",
        "The examples in lecture matched what showed up on the assignments.",
        "Office hours were worth going to. I left every time knowing what to fix.",
        "Posted the rubric ahead of time, so the marking never came as a surprise.",
        "Answered questions on the course forum within a day.",
        "Would take another course with this professor.",
    ],
    "mixed": [
        "Lectures were fine, but the pace picked up a lot after the midterm.",
        "The assignments taught me more than the lectures did.",
        "Fair overall, though feedback on labs took a few weeks.",
        "Knows the material well. The slides could be clearer.",
        "Go to the tutorials. That is where most of it clicked for me.",
    ],
    "poor": [
        "Mostly read from the slides, so I ended up learning from the textbook.",
        "Marks came off for small things that were not in the instructions.",
        "It was hard to get a straight answer about what the exam would cover.",
        "The workload was heavy for a course at this level.",
        "Start the assignments early. The instructions leave a lot out.",
    ],
}


def _clamp(score):
    """Keeps a score inside 1 to 5."""
    return max(1, min(5, score))


def seed():
    db = get_db()
    rng = random.Random(2026)     # fixed starting point: the same data every run

    # Twelve stand-in students. Their password hash is "!", which matches no
    # password, so nobody can log in as them.
    user_ids = []
    for number in range(1, 13):
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, is_verified) VALUES (?, '!', 1)",
            (f"sample-student-{number}@sample.invalid",),
        )
        user_ids.append(cursor.lastrowid)

    for name in config.TAGS:
        db.execute("INSERT INTO tags (name) VALUES (?)", (name,))

    course_ids = {}
    for code, title in COURSES:
        course_ids[code] = db.execute(
            "INSERT INTO courses (code, title) VALUES (?, ?)", (code, title)
        ).lastrowid

    # Oldest term first, so reviews can be dated in order.
    terms = sorted(config.TERMS, key=config.term_sort_key)

    for name, department, codes, typical, liked_tags in PROFESSORS:
        professor_id = db.execute(
            "INSERT INTO professors (name, department) VALUES (?, ?)", (name, department)
        ).lastrowid

        for code in codes:
            db.execute(
                "INSERT INTO teaches (professor_id, course_id) VALUES (?, ?)",
                (professor_id, course_ids[code]),
            )
            # Four to seven reviews per course, each from a different student.
            for user_id in rng.sample(user_ids, rng.randint(4, 7)):
                term = rng.choice(terms)
                # Nudge each typical score up or down by at most one.
                scores = [_clamp(base + rng.choice([-1, 0, 0, 1])) for base in typical]
                average = sum(scores) / len(scores)
                mood = "good" if average >= 4 else "mixed" if average >= 3 else "poor"
                body = " ".join(rng.sample(SENTENCES[mood], 2))
                # Date the review inside its term: a later term gives a later date.
                # Early months are used so sample reviews are never dated after
                # a real review posted in the same term.
                year = 2000 + int(term[1:])
                month = {"W": 2, "S": 6, "F": 10}[term[0]]
                created = f"{year}-{month:02d}-{rng.randint(1, 28):02d} 12:00:00"

                columns = ", ".join(config.CATEGORY_KEYS)
                marks = ", ".join("?" for _ in config.CATEGORY_KEYS)
                review_id = db.execute(
                    f"INSERT INTO reviews (professor_id, course_id, user_id, term, {columns}, body, created_at) "
                    f"VALUES (?, ?, ?, ?, {marks}, ?, ?)",
                    [professor_id, course_ids[code], user_id, term] + scores + [body, created],
                ).lastrowid

                for tag in rng.sample(liked_tags, rng.randint(1, min(3, len(liked_tags)))):
                    db.execute(
                        "INSERT INTO review_tags (review_id, tag_id) SELECT ?, id FROM tags WHERE name = ?",
                        (review_id, tag),
                    )

    db.commit()

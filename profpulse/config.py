"""Settings for ProfPulse, all in one place.

This is the file to edit when you want to change how the app behaves:
the school, the five rating categories, the tag list, the terms and the
limits. Nothing in here is secret, so it is safe in a public repository.
"""

# --- The school -------------------------------------------------------------

SCHOOL_NAME = "University of Guelph"

# Only addresses that end in this domain can make an account.
SCHOOL_EMAIL_DOMAIN = "uoguelph.ca"


# --- The five rating categories ---------------------------------------------
#
# Each entry is (key, label, question).
#   key       the column name in the reviews table (see schema.sql)
#   label     what the pages show
#   question  the prompt on the review form
#
# Every score runs from 1 (worst) to 5 (best), so the five can be averaged
# into one overall score.
#
# To rename a category, change its label here.
# To replace one, change its key here AND the matching column in schema.sql,
# then delete instance/profpulse.sqlite so the database is rebuilt.
CATEGORIES = [
    ("clarity", "Clarity", "How clearly were ideas explained?"),
    ("helpfulness", "Helpfulness", "How helpful was the professor outside of lectures?"),
    ("fairness", "Fair grading", "How fair were the marking and the exams?"),
    ("engagement", "Engagement", "How well did the lectures hold your attention?"),
    ("organization", "Organization", "How organized were the course and its materials?"),
]

CATEGORY_KEYS = [key for key, _label, _question in CATEGORIES]


# --- Tags ---------------------------------------------------------------------
#
# Reviewers pick tags from this list. Free typing is not allowed, which keeps
# the tag cloud tidy and stops people writing insults as tags.
TAGS = [
    "clear lectures",
    "practical examples",
    "engaging",
    "reads the slides",
    "helpful office hours",
    "fast feedback",
    "fair exams",
    "tough grader",
    "heavy workload",
    "lots of homework",
    "group projects",
    "attendance matters",
]

MAX_TAGS_PER_REVIEW = 4


# --- Terms --------------------------------------------------------------------
#
# Newest first. A code is a season letter plus a two-digit year:
# W = Winter, S = Summer, F = Fall. Add a new term at the top each semester.
TERMS = ["F26", "S26", "W26", "F25", "S25", "W25", "F24"]

SEASON_NAMES = {"W": "Winter", "S": "Summer", "F": "Fall"}
SEASON_ORDER = {"W": 1, "S": 2, "F": 3}


def term_label(code):
    """Turns "F26" into "Fall 2026"."""
    return f"{SEASON_NAMES[code[0]]} 20{code[1:]}"


def term_sort_key(code):
    """Sorts terms in calendar order: (year, season)."""
    return (int(code[1:]), SEASON_ORDER[code[0]])


# --- Limits -------------------------------------------------------------------

PASSWORD_MIN_CHARS = 10
PASSWORD_MAX_CHARS = 200

REVIEW_MIN_CHARS = 40
REVIEW_MAX_CHARS = 1500

# How long the link in the verification email works.
VERIFY_LINK_HOURS = 24

# Rate limits, written as (how many, in how many seconds).
LOGIN_LIMIT = (5, 15 * 60)            # failed logins from one address
REGISTER_LIMIT = (5, 60 * 60)         # sign-ups from one address
REVIEW_LIMIT = (5, 24 * 60 * 60)      # reviews from one account
REPORT_LIMIT = (10, 24 * 60 * 60)     # reports from one account

# A review is hidden once this many different students have reported it.
REPORTS_TO_HIDE = 3

REPORT_REASONS = [
    ("personal", "Personal attack or insult"),
    ("private", "Shares private information"),
    ("offtopic", "Not about the teaching"),
]

-- ProfPulse database layout (SQLite).
--
-- The main idea: a review belongs to a professor AND a course. That is what
-- lets the site show how someone teaches one specific class.
--
-- Running this file wipes the database and builds it again from nothing.

DROP TABLE IF EXISTS rate_events;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS review_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS teaches;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS professors;
DROP TABLE IF EXISTS users;

-- One row per student account.
-- The password is never stored, only a salted hash of it.
-- verify_token holds a hash of the emailed token, not the token itself.
CREATE TABLE users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT    NOT NULL UNIQUE,
    password_hash  TEXT    NOT NULL,
    is_verified    INTEGER NOT NULL DEFAULT 0,
    verify_token   TEXT,
    verify_expires TEXT,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE professors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    department TEXT NOT NULL
);

CREATE TABLE courses (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code  TEXT NOT NULL UNIQUE,      -- for example "CS 110"
    title TEXT NOT NULL
);

-- Which professor teaches which course. Many to many.
CREATE TABLE teaches (
    professor_id INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE,
    course_id    INTEGER NOT NULL REFERENCES courses(id)    ON DELETE CASCADE,
    PRIMARY KEY (professor_id, course_id)
);

-- One review. The five score columns match CATEGORIES in config.py.
-- The UNIQUE rule means one student can review one professor once per
-- course per term.
CREATE TABLE reviews (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    professor_id INTEGER NOT NULL REFERENCES professors(id) ON DELETE CASCADE,
    course_id    INTEGER NOT NULL REFERENCES courses(id)    ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    term         TEXT    NOT NULL,   -- for example "F26"
    clarity      INTEGER NOT NULL CHECK (clarity      BETWEEN 1 AND 5),
    helpfulness  INTEGER NOT NULL CHECK (helpfulness  BETWEEN 1 AND 5),
    fairness     INTEGER NOT NULL CHECK (fairness     BETWEEN 1 AND 5),
    engagement   INTEGER NOT NULL CHECK (engagement   BETWEEN 1 AND 5),
    organization INTEGER NOT NULL CHECK (organization BETWEEN 1 AND 5),
    body         TEXT    NOT NULL,
    is_hidden    INTEGER NOT NULL DEFAULT 0,   -- set to 1 after enough reports
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, professor_id, course_id, term)
);

CREATE TABLE tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Which tags a review carries. Many to many.
CREATE TABLE review_tags (
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    tag_id    INTEGER NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (review_id, tag_id)
);

-- A student flagging a review. One report per student per review.
CREATE TABLE reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id  INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    reason     TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (review_id, user_id)
);

-- A log used for rate limits: who did what, and when (seconds since 1970).
CREATE TABLE rate_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    who        TEXT NOT NULL,
    created_at REAL NOT NULL
);

-- Indexes for the lookups the pages do most.
CREATE INDEX idx_reviews_professor ON reviews (professor_id, course_id);
CREATE INDEX idx_reviews_created   ON reviews (created_at);
CREATE INDEX idx_rate_events       ON rate_events (action, who, created_at);

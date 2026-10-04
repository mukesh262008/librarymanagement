from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import g

DATABASE_PATH = Path(__file__).resolve().parent / "instance" / "library.db"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY,
            member_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            member_type TEXT NOT NULL,
            joined_on TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'suspended', 'expired'))
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            isbn TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            publisher TEXT,
            published_year INTEGER,
            shelf_location TEXT,
            description TEXT,
            total_copies INTEGER NOT NULL DEFAULT 1 CHECK (total_copies > 0)
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY,
            member_id INTEGER NOT NULL REFERENCES members(id),
            book_id INTEGER NOT NULL REFERENCES books(id),
            borrowed_on TEXT NOT NULL,
            due_on TEXT NOT NULL,
            returned_on TEXT,
            renewals INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'returned'))
        );
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY,
            member_id INTEGER NOT NULL REFERENCES members(id),
            loan_id INTEGER NOT NULL REFERENCES loans(id),
            amount REAL NOT NULL CHECK (amount >= 0),
            reason TEXT NOT NULL,
            assessed_on TEXT NOT NULL,
            paid_on TEXT
        );
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY,
            policy_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            value TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS staff_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_loans_member_status ON loans(member_id, status);
        CREATE INDEX IF NOT EXISTS idx_loans_book_status ON loans(book_id, status);
        CREATE INDEX IF NOT EXISTS idx_fines_member_paid ON fines(member_id, paid_on);
        """
    )
    _seed(db)
    _seed_supplemental_records(db)
    db.commit()


def _seed(db: sqlite3.Connection) -> None:
    if db.execute("SELECT 1 FROM members LIMIT 1").fetchone():
        return

    today = date.today()
    members = [
        ("M-10021", "Olivia Chen", "olivia.chen@example.org", "555-0101", "Faculty", -720, "active"),
        ("M-10022", "Marcus Reed", "marcus.reed@example.org", "555-0102", "Graduate", -510, "active"),
        ("M-10023", "Priya Nair", "priya.nair@example.org", "555-0103", "Staff", -385, "active"),
        ("M-10024", "Daniel Foster", "daniel.foster@example.org", "555-0104", "Undergraduate", -240, "active"),
        ("M-10025", "Amara Okafor", "amara.okafor@example.org", "555-0105", "Graduate", -90, "suspended"),
        ("M-10026", "Ethan Brooks", "ethan.brooks@example.org", "555-0106", "Undergraduate", -34, "active"),
    ]
    db.executemany(
        "INSERT INTO members (member_number, name, email, phone, member_type, joined_on, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(number, name, email, phone, kind, (today + timedelta(days=joined)).isoformat(), status)
         for number, name, email, phone, kind, joined, status in members],
    )
    books = [
        ("9780132350884", "Clean Code", "Robert C. Martin", "Software Engineering", "Prentice Hall", 2008, "QA 76.76 .M38", "A practical guide to writing maintainable, readable software.", 3),
        ("9780201485677", "Refactoring", "Martin Fowler", "Software Engineering", "Addison-Wesley", 1999, "QA 76.76 .F69", "Techniques for improving the design of existing code.", 2),
        ("9780062316097", "Sapiens", "Yuval Noah Harari", "History", "Harper", 2015, "CB 113 .H37", "A brief history of humankind.", 4),
        ("9780143127741", "The Fifth Season", "N. K. Jemisin", "Fiction", "Orbit", 2015, "PS 3610 .E46", "The opening novel in The Broken Earth trilogy.", 2),
        ("9780262033848", "Introduction to Algorithms", "Thomas H. Cormen", "Computer Science", "MIT Press", 2009, "Q 335 .C67", "A comprehensive introduction to modern algorithms.", 3),
        ("9780307887894", "The Lean Startup", "Eric Ries", "Business", "Crown Business", 2011, "HD 62.5 .R54", "A framework for building and managing new ventures.", 2),
        ("9781501173219", "Educated", "Tara Westover", "Biography", "Random House", 2018, "CT 3262 .W48", "A memoir about education, family and self-invention.", 2),
        ("9780596007126", "Head First Design Patterns", "Eric Freeman", "Computer Science", "O'Reilly Media", 2004, "QA 76.64 .F74", "A visual introduction to object-oriented design patterns.", 2),
    ]
    db.executemany(
        "INSERT INTO books (isbn, title, author, category, publisher, published_year, shelf_location, description, total_copies) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", books,
    )

    # Stable examples: one overdue loan, several current loans, and completed history.
    loans = [
        (1, 1, -35, -7, None, 0, "active"),
        (2, 2, -9, 12, None, 0, "active"),
        (3, 3, -14, 7, None, 0, "active"),
        (4, 5, -31, -3, None, 0, "active"),
        (5, 6, -18, 3, None, 0, "active"),
        (6, 8, -5, 16, None, 0, "active"),
        (1, 3, -120, -98, -95, 0, "returned"),
        (2, 6, -82, -60, -61, 0, "returned"),
        (4, 4, -65, -43, -40, 1, "returned"),
        (3, 1, -52, -30, -30, 0, "returned"),
    ]
    db.executemany(
        "INSERT INTO loans (member_id, book_id, borrowed_on, due_on, returned_on, renewals, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(member, book, (today + timedelta(days=borrowed)).isoformat(),
          (today + timedelta(days=due)).isoformat(),
          (today + timedelta(days=returned)).isoformat() if returned is not None else None,
          renewals, status)
         for member, book, borrowed, due, returned, renewals, status in loans],
    )
    db.executemany(
        "INSERT INTO fines (member_id, loan_id, amount, reason, assessed_on, paid_on) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 2.10, "Overdue return", today.isoformat(), None),
            (2, 8, 1.25, "Overdue return", (today - timedelta(days=61)).isoformat(),
             (today - timedelta(days=58)).isoformat()),
        ],
    )
    policies = [
        ("max_active_loans", "Borrowing limit", "Members may hold up to 5 items at one time.", "5", 1),
        ("loan_period_days", "Loan period", "Standard loans are issued for 21 days.", "21", 2),
        ("overdue_restriction", "Overdue restrictions", "Overdue items restrict new borrowing and renewals until returned.", "true", 3),
        ("daily_fine", "Overdue fines", "A fine of $0.30 per item accrues for each overdue day.", "0.30", 4),
        ("renewal_limit", "Renewal conditions", "An eligible loan may be renewed once for a further 21 days.", "1", 5),
        ("availability", "Book availability", "An item must have an available copy before a loan can be created.", "available_copies > 0", 6),
        ("fine_restriction", "Outstanding balances", "Outstanding fines of $10.00 or more restrict new borrowing.", "10.00", 7),
    ]
    db.executemany(
        "INSERT INTO policies (policy_key, title, description, value, display_order) VALUES (?, ?, ?, ?, ?)",
        policies,
    )


def _seed_supplemental_records(db: sqlite3.Connection) -> None:
    from seed_data import SUPPLEMENTAL_BOOKS, SUPPLEMENTAL_MEMBERS

    today = date.today()
    for index, (name, member_type, prefix) in enumerate(SUPPLEMENTAL_MEMBERS, start=11001):
        db.execute(
            "INSERT OR IGNORE INTO members "
            "(member_number, name, email, phone, member_type, joined_on, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'active')",
            (
                f"M-{index}",
                name,
                f"{prefix}.{index}@central-library.example",
                f"555-{(index % 10000):04d}",
                "Student" if member_type == "student" else "Staff",
                (today - timedelta(days=(index % 480))).isoformat(),
            ),
        )

    for index, (title, author, category, year) in enumerate(SUPPLEMENTAL_BOOKS, start=1):
        isbn_body = f"9781{index:08d}"
        checksum = (10 - sum(
            int(digit) * (1 if position % 2 == 0 else 3)
            for position, digit in enumerate(isbn_body)
        ) % 10) % 10
        shelf_number = 100 + index
        db.execute(
            "INSERT OR IGNORE INTO books "
            "(isbn, title, author, category, publisher, published_year, shelf_location, description, total_copies) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"{isbn_body}{checksum}",
                title,
                author,
                category,
                "Central Library Press",
                year,
                f"QA {shelf_number}",
                f"Library catalogue title in {category.lower()}, selected for the Central Library collection.",
                2 if index % 10 == 0 else 1,
            ),
        )

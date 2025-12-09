import sqlite3
import csv
from datetime import datetime

DB_NAME = "budget.db"

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def connect():
    return sqlite3.connect(DB_NAME)


# -----------------------------
# CREATE TABLES
# -----------------------------
def create_tables():
    conn = connect()
    cur = conn.cursor()

    # -------------------------
    # MAIN BUDGET TABLE
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY,
            income REAL DEFAULT 0,
            savings REAL DEFAULT 0,
            cash REAL DEFAULT 0
        )
    """)

    # Ensure 1 row exists
    cur.execute("SELECT COUNT(*) FROM budget")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO budget (income, savings, cash) VALUES (0,0,0)")

    # -------------------------
    # CATEGORY TABLE
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Seed categories only if empty
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        base = ["Rent", "Food", "Gas", "Utilities", "Personal"]
        cur.executemany("INSERT INTO categories (name) VALUES (?)", [(c,) for c in base])

    # -------------------------
    # EXPENSES TABLE
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# BUDGET FUNCTIONS
# -----------------------------
def get_budget():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT income, savings, cash FROM budget LIMIT 1")
    row = cur.fetchone()

    conn.close()
    return row


def update_budget(income, savings, cash):
    conn = connect()
    cur = conn.cursor()

    cur.execute("UPDATE budget SET income=?, savings=?, cash=? WHERE id=1",
                (income, savings, cash))

    conn.commit()
    conn.close()


# -----------------------------
# CATEGORY FUNCTIONS
# -----------------------------
def get_categories():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM categories ORDER BY name ASC")
    rows = cur.fetchall()

    conn.close()
    return rows


def add_category(name):
    conn = connect()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # category already exists

    conn.close()


def delete_category(cat_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()

    conn.close()


# -----------------------------
# EXPENSE FUNCTIONS
# -----------------------------
def add_expense(amount, category_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO expenses (amount, category_id, date)
        VALUES (?, ?, ?)
    """, (amount, category_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def get_expenses():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT expenses.id, expenses.amount, categories.name, expenses.date
        FROM expenses
        LEFT JOIN categories ON expenses.category_id = categories.id
        ORDER BY expenses.date DESC
    """)

    rows = cur.fetchall()

    conn.close()
    return rows


def delete_expense(exp_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    conn.commit()

    conn.close()


# -----------------------------
# EXPORT CSV
# -----------------------------
def export_expenses_csv(path):
    rows = get_expenses()

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Amount", "Category", "Date"])
        writer.writerows(rows)


# -----------------------------
# IMPORT CSV
# -----------------------------
def import_expenses_csv(path):
    conn = connect()
    cur = conn.cursor()

    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            amount = float(row["Amount"])
            category = row["Category"]
            date = row["Date"]

            # Ensure category exists
            cur.execute("SELECT id FROM categories WHERE name=?", (category,))
            res = cur.fetchone()

            if res:
                cat_id = res[0]
            else:
                cur.execute("INSERT INTO categories (name) VALUES (?)", (category,))
                cat_id = cur.lastrowid

            # Insert expense
            cur.execute("""
                INSERT INTO expenses (amount, category_id, date)
                VALUES (?, ?, ?)
            """, (amount, cat_id, date))

    conn.commit()
    conn.close()

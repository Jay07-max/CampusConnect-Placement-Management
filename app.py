
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "campusconnect-dev-key"

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                branch TEXT NOT NULL,
                cgpa REAL NOT NULL,
                skills TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                min_cgpa REAL NOT NULL,
                required_skills TEXT NOT NULL
            )
        """)


@app.route("/")
def index():
    search = request.args.get("search", "").strip()

    with get_db() as conn:
        if search:
            students = conn.execute("""
                SELECT * FROM students
                WHERE name LIKE ? OR branch LIKE ? OR skills LIKE ?
                ORDER BY id DESC
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            students = conn.execute(
                "SELECT * FROM students ORDER BY id DESC"
            ).fetchall()

        jobs = conn.execute(
            "SELECT * FROM jobs ORDER BY id DESC"
        ).fetchall()

        total_students = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        total_jobs = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

    return render_template(
        "index.html",
        students=students,
        jobs=jobs,
        total_students=total_students,
        total_jobs=total_jobs,
        search=search
    )


@app.route("/add-student", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    branch = request.form.get("branch", "").strip()
    skills = request.form.get("skills", "").strip()

    try:
        cgpa = float(request.form.get("cgpa", ""))
        if not 0 <= cgpa <= 10:
            raise ValueError
    except ValueError:
        flash("CGPA must be between 0 and 10.", "error")
        return redirect(url_for("index"))

    if not all([name, email, branch, skills]):
        flash("Please fill in all student fields.", "error")
        return redirect(url_for("index"))

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO students (name, email, branch, cgpa, skills)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, branch, cgpa, skills))
        flash("Student added successfully!", "success")
    except sqlite3.IntegrityError:
        flash("This email is already registered.", "error")

    return redirect(url_for("index"))


@app.route("/add-job", methods=["POST"])
def add_job():
    company = request.form.get("company", "").strip()
    role = request.form.get("role", "").strip()
    skills = request.form.get("required_skills", "").strip()

    try:
        min_cgpa = float(request.form.get("min_cgpa", ""))
        if not 0 <= min_cgpa <= 10:
            raise ValueError
    except ValueError:
        flash("Minimum CGPA must be between 0 and 10.", "error")
        return redirect(url_for("index"))

    if not all([company, role, skills]):
        flash("Please fill in all job fields.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute("""
            INSERT INTO jobs (company, role, min_cgpa, required_skills)
            VALUES (?, ?, ?, ?)
        """, (company, role, min_cgpa, skills))

    flash("Placement opportunity added!", "success")
    return redirect(url_for("index"))


@app.route("/delete-student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    with get_db() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    flash("Student deleted.", "success")
    return redirect(url_for("index"))


@app.route("/delete-job/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    flash("Placement opportunity deleted.", "success")
    return redirect(url_for("index"))


@app.route("/eligible/<int:job_id>")
def eligible_students(job_id):
    with get_db() as conn:
        job = conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

        if job is None:
            flash("Opportunity not found.", "error")
            return redirect(url_for("index"))

        students = conn.execute("""
            SELECT * FROM students WHERE cgpa >= ?
            ORDER BY cgpa DESC
        """, (job["min_cgpa"],)).fetchall()

    required = {
        s.strip().lower()
        for s in job["required_skills"].split(",") if s.strip()
    }

    eligible = []
    for student in students:
        skills = {
            s.strip().lower()
            for s in student["skills"].split(",") if s.strip()
        }
        if required.issubset(skills):
            eligible.append(student)

    return render_template("eligible.html", job=job, students=eligible)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

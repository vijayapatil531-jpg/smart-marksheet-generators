
from flask import Flask, request, redirect, url_for, render_template_string, send_file, abort
import sqlite3
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "marksheet.db")

COLLEGE_NAME = "PRATAP COLLEGE(AUTONOMOUS)AMALNER"
SUBJECTS = [
    "Java",
    "Python",
    "DBMS",
    "Prompt Engineering",
    "Software Development"
]
MAX_MARKS = 100
PASS_MARKS = 35


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                java REAL NOT NULL,
                python REAL NOT NULL,
                dbms REAL NOT NULL,
                prompt REAL NOT NULL,
                software REAL NOT NULL
            )
        """)


def calculate(student):
    marks = [
        float(student["java"]),
        float(student["python"]),
        float(student["dbms"]),
        float(student["prompt"]),
        float(student["software"])
    ]
    total = sum(marks)
    percentage = total / len(SUBJECTS)
    cgpa = percentage / 10

    if any(m < PASS_MARKS for m in marks):
        grade = "F"
        result = "FAIL"
    else:
        result = "PASS"
        if percentage >= 90:
            grade = "A+"
        elif percentage >= 80:
            grade = "A"
        elif percentage >= 70:
            grade = "B+"
        elif percentage >= 60:
            grade = "B"
        elif percentage >= 50:
            grade = "C"
        elif percentage >= 35:
            grade = "D"
        else:
            grade = "F"

    return {
        "marks": marks,
        "total": total,
        "maximum": len(SUBJECTS) * MAX_MARKS,
        "percentage": percentage,
        "cgpa": cgpa,
        "grade": grade,
        "result": result
    }


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Marksheet Generator</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f1f5f9;color:#172554}
header{background:#172554;color:white;text-align:center;padding:25px 12px}
header h1{margin:0 0 8px;font-size:27px}
header p{margin:0;color:#dbeafe}
main{max-width:1200px;margin:25px auto;padding:0 15px}
.card{background:white;border-radius:12px;padding:22px;margin-bottom:22px;
box-shadow:0 3px 15px #0000000d}
h2{margin-top:0;color:#1d4ed8}
.formgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}
label{font-size:13px;font-weight:bold;display:block;margin-bottom:6px}
input{width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:6px}
button,.btn{border:0;padding:10px 13px;border-radius:6px;cursor:pointer;
font-weight:bold;text-decoration:none;display:inline-block;font-size:13px}
.primary{background:#2563eb;color:white}
.edit{background:#f59e0b;color:#111827}
.delete{background:#dc2626;color:white}
.pdf{background:#059669;color:white}
.cancel{background:#64748b;color:white}
.actions{display:flex;gap:6px;flex-wrap:wrap}
.search{max-width:400px;margin-bottom:15px}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}
th,td{padding:11px 9px;border-bottom:1px solid #e2e8f0;text-align:center}
th{background:#dbeafe;color:#1e3a8a}
td.name{text-align:left}
.pass{color:#15803d;font-weight:bold}
.fail{color:#dc2626;font-weight:bold}
.notice{padding:12px;background:#dcfce7;border-radius:7px;margin-bottom:15px}
footer{text-align:center;padding:20px;color:#64748b}
@media(max-width:700px){.formgrid{grid-template-columns:1fr 1fr}header h1{font-size:22px}}
@media(max-width:430px){.formgrid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
<h1>{{ college }}</h1>
<p>Smart Marks Entry &amp; Marksheet Generator</p>
</header>
<main>
{% if message %}
<div class="notice">{{ message }}</div>
{% endif %}

<section class="card">
<h2>{{ 'Edit Student Marks' if student else 'Add Student Marks' }}</h2>
<form method="post" action="{{ url_for('save_student') }}">
{% if student %}
<input type="hidden" name="id" value="{{ student.id }}">
{% endif %}
<div class="formgrid">
<div>
<label>Roll Number</label>
<input name="roll" required maxlength="30"
value="{{ student.roll if student else '' }}">
</div>
<div>
<label>Student Full Name</label>
<input name="name" required maxlength="100"
value="{{ student.name if student else '' }}">
</div>
{% for subject, key in fields %}
<div>
<label>{{ subject }} (out of 100)</label>
<input type="number" name="{{ key }}" min="0" max="100"
step="0.01" required
value="{{ student[key] if student else '' }}">
</div>
{% endfor %}
</div>
<br>
<button class="primary" type="submit">
{{ 'Update Marks' if student else 'Save Student' }}
</button>
{% if student %}
<a class="btn cancel" href="{{ url_for('index') }}">Cancel Edit</a>
{% endif %}
</form>
</section>

<section class="card">
<h2>Student Result Records</h2>
<input id="search" class="search" placeholder="Search by name or roll number..."
oninput="filterRows()">
<div class="tablewrap">
<table id="results">
<thead>
<tr>
<th>Roll</th><th>Student Name</th>
{% for subject, key in fields %}<th>{{ subject }}</th>{% endfor %}
<th>Total / 500</th><th>Percentage</th><th>Grade</th>
<th>CGPA / 10</th><th>Result</th><th>Actions</th>
</tr>
</thead>
<tbody>
{% for s in students %}
{% set r = calculate(s) %}
<tr>
<td>{{ s.roll }}</td>
<td class="name">{{ s.name }}</td>
{% for mark in r.marks %}<td>{{ '%.2f'|format(mark) }}</td>{% endfor %}
<td>{{ '%.2f'|format(r.total) }}</td>
<td>{{ '%.2f'|format(r.percentage) }}%</td>
<td>{{ r.grade }}</td>
<td>{{ '%.2f'|format(r.cgpa) }}</td>
<td class="{{ 'pass' if r.result == 'PASS' else 'fail' }}">{{ r.result }}</td>
<td>
<div class="actions">
<a class="btn edit" href="{{ url_for('index', edit=s.id) }}">Edit</a>
<a class="btn pdf" href="{{ url_for('download_pdf', student_id=s.id) }}">PDF</a>
<form method="post" action="{{ url_for('delete_student', student_id=s.id) }}"
onsubmit="return confirm('Delete this student record permanently?')">
<button class="delete" type="submit">Delete</button>
</form>
</div>
</td>
</tr>
{% else %}
<tr><td colspan="12">No student records yet. Add the first student above.</td></tr>
{% endfor %}
</tbody>
</table>
</div>
</section>
</main>
<footer>Smart Marksheet Generator | B.Sc. Computer Science Project</footer>
<script>
function filterRows(){
 const q=document.getElementById('search').value.toLowerCase();
 document.querySelectorAll('#results tbody tr').forEach(row=>{
   row.style.display=row.innerText.toLowerCase().includes(q)?'':'none';
 });
}
</script>
</body>
</html>
"""


FIELDS = [
    ("Java", "java"),
    ("Python", "python"),
    ("DBMS", "dbms"),
    ("Prompt Engineering", "prompt"),
    ("Software Development", "software")
]


@app.route("/")
def index():
    with get_db() as con:
        students = con.execute(
            "SELECT * FROM students ORDER BY name COLLATE NOCASE"
        ).fetchall()

        edit_id = request.args.get("edit", type=int)
        student = None
        if edit_id:
            student = con.execute(
                "SELECT * FROM students WHERE id=?", (edit_id,)
            ).fetchone()
            if student is None:
                abort(404)

    return render_template_string(
        HTML,
        college=COLLEGE_NAME,
        subjects=SUBJECTS,
        fields=FIELDS,
        students=students,
        student=student,
        calculate=calculate,
        message=request.args.get("message", "")
    )


@app.route("/save", methods=["POST"])
def save_student():
    roll = request.form.get("roll", "").strip()
    name = request.form.get("name", "").strip()
    student_id = request.form.get("id", "").strip()

    if not roll or not name:
        return redirect(url_for("index", message="Enter roll number and name."))

    try:
        marks = []
        for _, key in FIELDS:
            mark = float(request.form[key])
            if not 0 <= mark <= MAX_MARKS:
                raise ValueError
            marks.append(mark)

        with get_db() as con:
            if student_id:
                con.execute("""
                    UPDATE students
                    SET roll=?, name=?, java=?, python=?, dbms=?, prompt=?, software=?
                    WHERE id=?
                """, (roll, name, *marks, int(student_id)))
                msg = "Student marks updated successfully."
            else:
                con.execute("""
                    INSERT INTO students
                    (roll, name, java, python, dbms, prompt, software)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (roll, name, *marks))
                msg = "Student added successfully."

        return redirect(url_for("index", message=msg))

    except ValueError:
        return redirect(url_for("index", message="Enter valid marks from 0 to 100."))
    except sqlite3.IntegrityError:
        return redirect(url_for("index", message="Roll number already exists. Use a unique roll number."))


@app.route("/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    with get_db() as con:
        con.execute("DELETE FROM students WHERE id=?", (student_id,))
    return redirect(url_for("index", message="Student record deleted."))


@app.route("/pdf/<int:student_id>")
def download_pdf(student_id):
    with get_db() as con:
        student = con.execute(
            "SELECT * FROM students WHERE id=?", (student_id,)
        ).fetchone()

    if student is None:
        abort(404)

    result = calculate(student)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle("Student Marksheet - " + student["roll"])
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 55, COLLEGE_NAME)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, height - 85, "STUDENT MARKSHEET")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(55, height - 125, "Roll Number: " + student["roll"])
    pdf.drawString(55, height - 145, "Student Name: " + student["name"])

    y = height - 195
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(60, y, "Subject")
    pdf.drawString(340, y, "Maximum Marks")
    pdf.drawString(470, y, "Marks")
    y -= 22

    pdf.setFont("Helvetica", 11)
    for (subject, key), mark in zip(FIELDS, result["marks"]):
        pdf.drawString(60, y, subject)
        pdf.drawString(370, y, "100")
        pdf.drawString(480, y, f"{mark:.2f}")
        y -= 25

    y -= 10
    pdf.line(55, y, width - 55, y)
    y -= 30

    lines = [
        f"Total Marks: {result['total']:.2f} / {result['maximum']}",
        f"Percentage: {result['percentage']:.2f}%",
        f"Grade: {result['grade']}",
        f"CGPA (Percentage / 10): {result['cgpa']:.2f} / 10",
        f"Final Result: {result['result']}"
    ]

    for line in lines:
        pdf.drawString(60, y, line)
        y -= 25

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawCentredString(width / 2, 50, "Generated by Smart Marksheet Generator")
    pdf.save()
    buffer.seek(0)

    safe_roll = "".join(
        ch for ch in student["roll"] if ch.isalnum() or ch in "-_"
    ) or "student"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Marksheet_{safe_roll}.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

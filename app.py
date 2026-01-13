from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import date, datetime
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


def login_required(view_func):
    """Require a logged-in user."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to continue.", "danger")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles):

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                flash("Please log in to continue.", "danger")
                return redirect(url_for("home"))

            role = (session.get("role") or "EMPLOYEE").upper()
            allowed = {r.upper() for r in allowed_roles}
            if allowed and role not in allowed:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard"))

            return view_func(*args, **kwargs)

        return wrapper

    return decorator


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        result = db.session.execute(
            text("SELECT 1 FROM users WHERE username = :username"),
            {"username": username}
        )
        existing_user = result.first()

        if existing_user:
            flash("Username already taken!", "danger")
            return redirect(url_for('register'))

        # Insert new user
        db.session.execute(
            text("""
                INSERT INTO users (username, password)
                VALUES (:username, :password)
            """),
            {
                "username": username,
                "password": password
            }
        )
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    result = db.session.execute(
        text("""
            SELECT username, account_type
            FROM users
            WHERE username = :username
              AND password = :password
        """),
        {
            "username": username,
            "password": password
        }
    )

    user = result.mappings().first()

    if user:
        session['username'] = user['username']

        # Normalize role from DB
        raw_role = user.get('account_type') or 'Employee'
        session['role'] = (raw_role.strip() or 'Employee').upper()

        return redirect(url_for('dashboard'))

    flash("Invalid username or password.", "danger")
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Total employees
    result = db.session.execute(
        text("SELECT COUNT(*) AS total FROM employees")
    )
    total_employees = result.scalar()

    # Active projects
    result = db.session.execute(
        text("SELECT COUNT(*) AS total FROM projects WHERE status = 'Active'")
    )
    active_projects = result.scalar()

    # Attendance rate today
    today = date.today()

    result = db.session.execute(
        text("SELECT COUNT(*) FROM attendance WHERE date = :today"),
        {"today": today}
    )
    total_attendance = result.scalar()

    result = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM attendance
            WHERE date = :today AND status = 'Present'
        """),
        {"today": today}
    )
    present = result.scalar()

    attendance_rate = 0
    if total_attendance and total_attendance > 0:
        attendance_rate = round((present / total_attendance) * 100, 2)

    # Payroll this month (PostgreSQL-compatible)
    result = db.session.execute(
        text("""
            SELECT COALESCE(SUM(net_pay), 0)
            FROM payroll
            WHERE pay_period_end >= date_trunc('month', CURRENT_DATE)
              AND pay_period_end < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
        """)
    )
    payroll_month = result.scalar()

    return render_template(
        'dashboard.html',
        username=session['username'],
        total_employees=total_employees,
        active_projects=active_projects,
        attendance_rate=attendance_rate,
        payroll_month=payroll_month
    )


@app.route('/employees')
@login_required
def employees():
    # Fetch all employees
    result = db.session.execute(text("SELECT * FROM employees ORDER BY name ASC"))
    employees = result.fetchall()  # returns list of Row objects

    # Convert to list of dicts for easier access in template
    employees_list = [dict(row) for row in employees]

    return render_template('employees.html', employees=employees_list, username=session.get('username'))

@app.route('/add_employee', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_employee():
    name = request.form['name']
    position = request.form['position']
    department = request.form['department']
    status = request.form['status']

    # Insert new employee using parameter binding
    db.session.execute(
        text("""
            INSERT INTO employees (name, position, department, status)
            VALUES (:name, :position, :department, :status)
        """),
        {"name": name, "position": position, "department": department, "status": status}
    )
    db.session.commit()  # commit the transaction

    flash("Employee added successfully!", "success")
    return redirect(url_for('employees'))

@app.route('/employees')
@login_required
def employees():
    result = db.session.execute(text("SELECT * FROM employees ORDER BY name ASC"))
    employees_list = [dict(row) for row in result.fetchall()]
    return render_template('employees.html', employees=employees_list, username=session.get('username'))


@app.route('/add_employee', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_employee():
    db.session.execute(
        text("""
            INSERT INTO employees (name, position, department, status)
            VALUES (:name, :position, :department, :status)
        """),
        {"name": request.form['name'],
         "position": request.form['position'],
         "department": request.form['department'],
         "status": request.form['status']}
    )
    db.session.commit()
    flash("Employee added successfully!", "success")
    return redirect(url_for('employees'))


@app.route('/update_employee', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def update_employee():
    db.session.execute(
        text("""
            UPDATE employees 
            SET name=:name, position=:position, department=:department, status=:status 
            WHERE id=:id
        """),
        {"id": request.form['id'],
         "name": request.form['name'],
         "position": request.form['position'],
         "department": request.form['department'],
         "status": request.form['status']}
    )
    db.session.commit()
    flash("Employee updated successfully!", "success")
    return redirect(url_for('employees'))


@app.route('/attendance')
@login_required
def attendance():
    selected_date = request.args.get('date') or date.today().isoformat()

    employees_result = db.session.execute(text("SELECT * FROM employees ORDER BY name ASC"))
    employees = [dict(row) for row in employees_result.fetchall()]

    attendance_result = db.session.execute(
        text("""
            SELECT a.id, a.employee_id, e.name, e.department, a.date, a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.date = :selected_date
            ORDER BY e.name ASC
        """),
        {"selected_date": selected_date}
    )
    attendance_records = [dict(row) for row in attendance_result.fetchall()]

    return render_template('attendance.html',
                           employees=employees,
                           attendance_records=attendance_records,
                           date_today=selected_date,
                           username=session.get('username'))


@app.route('/add_attendance', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager", "Employee")
def add_attendance():
    db.session.execute(
        text("""
            INSERT INTO attendance (employee_id, date, status)
            VALUES (:employee_id, :date, :status)
        """),
        {"employee_id": request.form['employee_id'],
         "date": request.form['date'],
         "status": request.form['status']}
    )
    db.session.commit()
    flash('Attendance added successfully!', 'success')
    return redirect(url_for('attendance'))


@app.route('/edit_attendance/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_attendance(id):
    db.session.execute(
        text("""
            UPDATE attendance
            SET employee_id=:employee_id, date=:date, status=:status
            WHERE id=:id
        """),
        {"employee_id": request.form['employee_id'],
         "date": request.form['date'],
         "status": request.form['status'],
         "id": id}
    )
    db.session.commit()
    flash('Attendance updated successfully!', 'success')
    return redirect(url_for('attendance'))


@app.route('/delete_attendance/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_attendance(id):
    db.session.execute(text("DELETE FROM attendance WHERE id = :id"), {"id": id})
    db.session.commit()
    flash('Attendance record deleted successfully!', 'success')
    return redirect(url_for('attendance'))


@app.route('/projects')
@login_required
def projects():
    projects_result = db.session.execute(text("SELECT * FROM projects"))
    projects = [dict(row) for row in projects_result.fetchall()]

    employees_result = db.session.execute(text("SELECT id, name FROM employees"))
    employees = [dict(row) for row in employees_result.fetchall()]

    return render_template('projects.html', projects=projects, employees=employees, username=session.get('username'))


@app.route('/project_employees/<int:project_id>')
@login_required
def project_employees(project_id):
    result = db.session.execute(
        text("""
            SELECT e.id, e.name, e.position
            FROM project_employees pe
            JOIN employees e ON pe.employee_id = e.id
            WHERE pe.project_id = :project_id
            ORDER BY e.name
        """),
        {"project_id": project_id}
    )
    employees = [dict(row) for row in result.fetchall()]
    return jsonify(employees)


@app.route('/edit_project/<int:id>', methods=['GET', 'POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_project(id):
    if request.method == 'POST':
        db.session.execute(
            text("""
                UPDATE projects
                SET project_name=:project_name, department=:department,
                    start_date=:start_date, end_date=:end_date, status=:status
                WHERE id=:id
            """),
            {"project_name": request.form['project_name'],
             "department": request.form['department'],
             "start_date": request.form['start_date'],
             "end_date": request.form['end_date'],
             "status": request.form['status'],
             "id": id}
        )

        # Remove old assignments
        db.session.execute(text("DELETE FROM project_employees WHERE project_id=:id"), {"id": id})

        # Add new assignments
        for emp_id in request.form.getlist('employees'):
            db.session.execute(
                text("INSERT INTO project_employees (project_id, employee_id) VALUES (:project_id, :emp_id)"),
                {"project_id": id, "emp_id": emp_id}
            )

        db.session.commit()
        flash('Project and assigned employees updated successfully!', 'success')
        return redirect(url_for('projects'))

    project_result = db.session.execute(text("SELECT * FROM projects WHERE id=:id"), {"id": id})
    project = dict(project_result.fetchone())

    employees_result = db.session.execute(text("SELECT id, name FROM employees"))
    employees = [dict(row) for row in employees_result.fetchall()]

    assigned_result = db.session.execute(text("SELECT employee_id FROM project_employees WHERE project_id=:id"), {"id": id})
    assigned = [row['employee_id'] for row in assigned_result.fetchall()]

    return render_template('edit_project.html', project=project, employees=employees, assigned=assigned)


@app.route('/add_project', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_project():
    db.session.execute(
        text("""
            INSERT INTO projects (project_name, department, start_date, end_date, status)
            VALUES (:project_name, :department, :start_date, :end_date, :status)
            RETURNING id
        """),
        {"project_name": request.form['project_name'],
         "department": request.form['department'],
         "start_date": request.form['start_date'],
         "end_date": request.form['end_date'],
         "status": request.form['status']}
    )
    project_id = db.session.execute(text("SELECT currval(pg_get_serial_sequence('projects','id'))")).scalar()

    for emp_id in request.form.getlist('employees'):
        db.session.execute(
            text("INSERT INTO project_employees (project_id, employee_id) VALUES (:project_id, :emp_id)"),
            {"project_id": project_id, "emp_id": emp_id}
        )

    db.session.commit()
    flash('Project and employees added successfully!', 'success')
    return redirect(url_for('projects'))


@app.route('/update_project', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def update_project():
    db.session.execute(
        text("""
            UPDATE projects
            SET project_name=:project_name, department=:department,
                start_date=:start_date, end_date=:end_date, status=:status
            WHERE id=:id
        """),
        {"id": request.form['id'],
         "project_name": request.form['project_name'],
         "department": request.form['department'],
         "start_date": request.form['start_date'],
         "end_date": request.form['end_date'],
         "status": request.form['status']}
    )
    db.session.commit()
    flash('Project updated successfully!', 'success')
    return redirect(url_for('projects'))


@app.route('/delete_project/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_project(id):
    db.session.execute(text("DELETE FROM projects WHERE id = :id"), {"id": id})
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects'))


@app.route('/payroll')
@login_required
def payroll():
    payroll_result = db.session.execute(
        text("""
            SELECT p.*, e.name, e.position, pr.project_name, pr.id as project_id
            FROM payroll p
            JOIN employees e ON p.employee_id = e.id
            LEFT JOIN projects pr ON p.project_id = pr.id
            ORDER BY p.pay_period_end DESC, p.created_at DESC
        """)
    )
    payroll_records = [dict(row) for row in payroll_result.fetchall()]

    employees_result = db.session.execute(text("SELECT id, name, position FROM employees"))
    employees = [dict(row) for row in employees_result.fetchall()]

    projects_result = db.session.execute(text("SELECT id, project_name FROM projects ORDER BY project_name"))
    projects = [dict(row) for row in projects_result.fetchall()]

    summary_result = db.session.execute(
        text("""
            SELECT 
                COUNT(*) as employees_paid,
                COALESCE(SUM(COALESCE(gross_pay, basic_salary + overtime)), 0) as total_gross_pay,
                COALESCE(SUM(COALESCE(total_deductions, deductions)), 0) as total_deductions,
                COALESCE(SUM(net_pay), 0) as total_net_pay
            FROM payroll
        """)
    )
    summary = dict(summary_result.fetchone())

    return render_template('payroll.html',
                           payroll_records=payroll_records,
                           employees=employees,
                           projects=projects,
                           summary=summary,
                           username=session.get('username'))


@app.route('/add_payroll', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_payroll():
    employee_id = request.form['employee_id']
    project_id = request.form.get('project_id') or None
    pay_period_start = request.form['pay_period_start']
    pay_period_end = request.form['pay_period_end']
    position = request.form.get('position', '')

    # Excel-style fields
    daily_rate = float(request.form.get('daily_rate', 0) or 0)
    meal = float(request.form.get('meal', 0) or 0)
    transpo = float(request.form.get('transpo', 0) or 0)
    days_worked = int(request.form.get('days_worked', 0) or 0)
    total_ot_hours = float(request.form.get('total_ot_hours', 0) or 0)
    holiday_pay = float(request.form.get('holiday_pay', 0) or 0)
    holiday_pay_amount = float(request.form.get('holiday_pay_amount', 0) or 0)
    others = float(request.form.get('others', 0) or 0)
    cash_advance = float(request.form.get('cash_advance', 0) or 0)

    # Legacy/simple fields
    basic_salary = float(request.form.get('basic_salary', 0) or 0)
    overtime = float(request.form.get('overtime', 0) or 0)
    deductions = float(request.form.get('deductions', 0) or 0)

    if basic_salary > 0:  # Legacy mode
        net_pay = basic_salary + overtime - deductions
        total_daily_salary = daily_rate + meal + transpo if daily_rate > 0 else basic_salary / max(days_worked, 1)
        ot_amount = (daily_rate / 8) * 1.25 * total_ot_hours if total_ot_hours > 0 and daily_rate > 0 else overtime
        total_deductions = cash_advance if cash_advance > 0 else deductions
        gross_pay = basic_salary + overtime
    else:  # Excel-style mode
        total_daily_salary = daily_rate + meal + transpo
        ot_amount = (daily_rate / 8) * 1.25 * total_ot_hours if daily_rate > 0 else 0
        total_deductions = cash_advance
        gross_pay = (total_daily_salary * days_worked) + ot_amount + holiday_pay_amount + others
        net_pay = gross_pay - total_deductions
        basic_salary = total_daily_salary * days_worked
        overtime = ot_amount
        deductions = total_deductions

    status = request.form.get('status', 'Pending')

    # Insert payroll record
    db.session.execute(
        text("""
            INSERT INTO payroll (
                employee_id, project_id, pay_period_start, pay_period_end, position,
                daily_rate, meal, transpo, total_daily_salary, days_worked,
                total_ot_hours, ot_amount, holiday_pay, holiday_pay_amount, others,
                cash_advance, total_deductions, gross_pay, net_pay,
                basic_salary, overtime, deductions, status
            ) VALUES (
                :employee_id, :project_id, :pay_period_start, :pay_period_end, :position,
                :daily_rate, :meal, :transpo, :total_daily_salary, :days_worked,
                :total_ot_hours, :ot_amount, :holiday_pay, :holiday_pay_amount, :others,
                :cash_advance, :total_deductions, :gross_pay, :net_pay,
                :basic_salary, :overtime, :deductions, :status
            )
        """),
        {
            "employee_id": employee_id,
            "project_id": project_id,
            "pay_period_start": pay_period_start,
            "pay_period_end": pay_period_end,
            "position": position,
            "daily_rate": daily_rate,
            "meal": meal,
            "transpo": transpo,
            "total_daily_salary": total_daily_salary,
            "days_worked": days_worked,
            "total_ot_hours": total_ot_hours,
            "ot_amount": ot_amount,
            "holiday_pay": holiday_pay,
            "holiday_pay_amount": holiday_pay_amount,
            "others": others,
            "cash_advance": cash_advance,
            "total_deductions": total_deductions,
            "gross_pay": gross_pay,
            "net_pay": net_pay,
            "basic_salary": basic_salary,
            "overtime": overtime,
            "deductions": deductions,
            "status": status
        }
    )

    # Ensure employee is assigned to project if project_id provided
    if project_id:
        exists_result = db.session.execute(
            text("SELECT 1 FROM project_employees WHERE employee_id=:employee_id AND project_id=:project_id"),
            {"employee_id": employee_id, "project_id": project_id}
        ).fetchone()
        if not exists_result:
            db.session.execute(
                text("INSERT INTO project_employees (employee_id, project_id) VALUES (:employee_id, :project_id)"),
                {"employee_id": employee_id, "project_id": project_id}
            )

    db.session.commit()

    flash_msg = 'Payroll record added successfully!'
    if project_id:
        flash_msg += ' Employee assigned to project.'
    flash(flash_msg, 'success')

    # Redirect
    return redirect(url_for('project_payroll', project_id=project_id)) if project_id else redirect(url_for('payroll'))


@app.route('/edit_payroll', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_payroll():
    try:
        id = int(request.form['id'])
        employee_id = request.form['employee_id']
        project_id = request.form.get('project_id') or None
        pay_period_start = request.form['pay_period_start']
        pay_period_end = request.form['pay_period_end']
        basic_salary = float(request.form.get('basic_salary', 0) or 0)
        overtime = float(request.form.get('overtime', 0) or 0)
        deductions = float(request.form.get('deductions', 0) or 0)
        status = request.form.get('status', 'Pending')

        gross_pay = basic_salary + overtime
        total_deductions = deductions
        net_pay = gross_pay - total_deductions

        db.session.execute(
            text("""
                UPDATE payroll 
                SET employee_id=:employee_id,
                    project_id=:project_id,
                    pay_period_start=:pay_period_start,
                    pay_period_end=:pay_period_end,
                    basic_salary=:basic_salary,
                    overtime=:overtime,
                    deductions=:deductions,
                    gross_pay=:gross_pay,
                    total_deductions=:total_deductions,
                    net_pay=:net_pay,
                    status=:status
                WHERE id=:id
            """),
            {
                "employee_id": employee_id,
                "project_id": project_id,
                "pay_period_start": pay_period_start,
                "pay_period_end": pay_period_end,
                "basic_salary": basic_salary,
                "overtime": overtime,
                "deductions": deductions,
                "gross_pay": gross_pay,
                "total_deductions": total_deductions,
                "net_pay": net_pay,
                "status": status,
                "id": id
            }
        )
        db.session.commit()
        flash('Payroll record updated successfully!', 'success')
        return redirect(url_for('project_payroll', project_id=project_id)) if project_id else redirect(url_for('payroll'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating payroll: {str(e)}', 'danger')
        return redirect(url_for('payroll'))


@app.route('/get_payroll/<int:id>', methods=['GET'])
@roles_required("Admin", "Manager", "Assistant Manager")
def get_payroll(id):
    result = db.session.execute(
        text("SELECT * FROM payroll WHERE id=:id"),
        {"id": id}
    )
    record = result.fetchone()
    if record:
        return jsonify(dict(record))
    return jsonify({'error': 'Record not found'}), 404


@app.route('/delete_payroll/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_payroll(id):
    # Get project_id before deleting (for redirect)
    project_result = db.session.execute(
        text("SELECT project_id FROM payroll WHERE id=:id"),
        {"id": id}
    ).fetchone()
    project_id = project_result['project_id'] if project_result else None

    db.session.execute(
        text("DELETE FROM payroll WHERE id=:id"),
        {"id": id}
    )
    db.session.commit()
    flash('Payroll record deleted successfully!', 'success')
    return redirect(url_for('project_payroll', project_id=project_id)) if project_id else redirect(url_for('payroll'))


@app.route('/payroll_overview')
@login_required
def payroll_overview():
    result = db.session.execute(text("""
        SELECT 
            pr.id,
            pr.project_name,
            pr.department,
            pr.status,
            COALESCE((SELECT SUM(net_pay) FROM payroll WHERE project_id = pr.id), 0) AS total_payroll_cost,
            COALESCE((SELECT COUNT(DISTINCT employee_id) FROM project_employees WHERE project_id = pr.id), 0) AS employee_count,
            COALESCE((SELECT COUNT(DISTINCT employee_id) FROM payroll WHERE project_id = pr.id), 0) AS employees_with_payroll,
            COALESCE((SELECT COUNT(*) FROM payroll WHERE project_id = pr.id), 0) AS payroll_record_count
        FROM projects pr
        ORDER BY pr.project_name
    """))
    projects = [dict(row) for row in result.fetchall()]
    return render_template('payroll_overview.html', projects=projects, username=session.get('username'))


@app.route('/project_payroll/<int:project_id>')
@login_required
def project_payroll(project_id):
    # Get project details
    project_result = db.session.execute(
        text("SELECT * FROM projects WHERE id=:id"),
        {"id": project_id}
    ).fetchone()
    if not project_result:
        flash('Project not found!', 'danger')
        return redirect(url_for('payroll_overview'))
    project = dict(project_result)

    # Assigned employees
    assigned_result = db.session.execute(
        text("""
            SELECT e.id AS employee_id, e.name, e.position
            FROM employees e
            JOIN project_employees pe ON e.id = pe.employee_id
            WHERE pe.project_id=:project_id
            ORDER BY e.name
        """),
        {"project_id": project_id}
    )
    assigned_employees = [dict(row) for row in assigned_result.fetchall()]

    # Latest payroll per employee
    payroll_result = db.session.execute(
        text("""
            SELECT e.id AS employee_id, e.name, e.position,
                   p.id AS payroll_id, p.pay_period_start, p.pay_period_end,
                   p.basic_salary, p.overtime, p.deductions, p.net_pay,
                   p.status, p.gross_pay, p.total_deductions,
                   p.daily_rate, p.meal, p.transpo, p.total_daily_salary,
                   p.days_worked, p.total_ot_hours, p.ot_amount,
                   p.holiday_pay, p.holiday_pay_amount, p.others, p.cash_advance,
                   p.created_at
            FROM employees e
            JOIN project_employees pe ON e.id = pe.employee_id
            LEFT JOIN (
                SELECT p1.*, ROW_NUMBER() OVER (PARTITION BY p1.employee_id ORDER BY p1.pay_period_end DESC, p1.created_at DESC) AS rn
                FROM payroll p1
                WHERE p1.project_id=:project_id
            ) p ON e.id = p.employee_id AND p.rn = 1
            WHERE pe.project_id=:project_id
            ORDER BY e.name
        """),
        {"project_id": project_id}
    )
    all_payroll_data = [dict(row) for row in payroll_result.fetchall()]

    # Build combined records
    combined_records = []
    for r in all_payroll_data:
        if r['payroll_id'] is None:
            combined_records.append({
                'employee_id': r['employee_id'],
                'id': None,
                'name': r['name'],
                'position': r['position'],
                'pay_period_start': None,
                'pay_period_end': None,
                'basic_salary': 0,
                'overtime': 0,
                'deductions': 0,
                'net_pay': 0,
                'status': 'No Payroll',
                'has_payroll': False
            })
        else:
            combined_records.append(r)

    # Summary
    summary_result = db.session.execute(
        text("""
            SELECT 
                COUNT(*) AS employees_paid,
                COALESCE(SUM(COALESCE(gross_pay, basic_salary + overtime)), 0) AS total_gross_pay,
                COALESCE(SUM(COALESCE(total_deductions, deductions)), 0) AS total_deductions,
                COALESCE(SUM(net_pay), 0) AS total_net_pay
            FROM payroll
            WHERE project_id=:project_id
        """),
        {"project_id": project_id}
    )
    summary = dict(summary_result.fetchone() or {})

    # All employees for dropdown
    all_employees_result = db.session.execute(
        text("SELECT id, name, position FROM employees ORDER BY name")
    )
    all_employees = [dict(row) for row in all_employees_result.fetchall()]

    return render_template('project_payroll.html',
                           project=project,
                           payroll_records=combined_records,
                           assigned_employees=assigned_employees,
                           all_employees=all_employees,
                           summary=summary,
                           username=session.get('username'))


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('home'))


@app.route('/admin/settings')
@roles_required("Admin")
def admin_settings():
    """Admin panel: manage user accounts and roles."""
    result = db.session.execute(text("SELECT id, username, account_type FROM users ORDER BY username"))
    users = [dict(row) for row in result.fetchall()]

    return render_template(
        'admin_settings.html',
        users=users,
        username=session.get('username'),
    )


@app.route('/admin/users/add', methods=['POST'])
@roles_required("Admin")
def add_user():
    """Add a new user account."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    account_type = request.form.get('account_type', 'Employee')

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for('admin_settings'))

    try:
        # Check if username already exists
        existing_user = db.session.execute(
            text("SELECT 1 FROM users WHERE username=:username"),
            {"username": username}
        ).fetchone()

        if existing_user:
            flash("Username already taken!", "danger")
            return redirect(url_for('admin_settings'))

        # Insert new user
        db.session.execute(
            text("INSERT INTO users (username, password, account_type) VALUES (:username, :password, :account_type)"),
            {"username": username, "password": password, "account_type": account_type}
        )
        db.session.commit()
        flash(f"User '{username}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding user: {e}", "danger")

    return redirect(url_for('admin_settings'))


@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@roles_required("Admin")
def update_user(user_id: int):
    """Update username, password and/or role for a user."""
    new_username = request.form.get('username')
    new_password = request.form.get('password')
    new_role = request.form.get('account_type')

    fields = {}
    if new_username:
        fields['username'] = new_username
    if new_password:
        fields['password'] = new_password
    if new_role:
        fields['account_type'] = new_role

    if not fields:
        flash("No changes to update.", "info")
        return redirect(url_for('admin_settings'))

    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    fields['id'] = user_id

    try:
        db.session.execute(
            text(f"UPDATE users SET {set_clause} WHERE id = :id"),
            fields
        )
        db.session.commit()
        flash("User updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating user: {e}", "danger")

    return redirect(url_for('admin_settings'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@roles_required("Admin")
def delete_user(user_id: int):
    """Delete a user account."""
    try:
        # Check if user exists
        user = db.session.execute(
            text("SELECT username FROM users WHERE id = :id"),
            {"id": user_id}
        ).fetchone()

        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('admin_settings'))

        # Prevent deleting yourself
        if session.get('username') == user['username']:
            flash("You cannot delete your own account!", "danger")
            return redirect(url_for('admin_settings'))

        # Delete the user
        db.session.execute(
            text("DELETE FROM users WHERE id = :id"),
            {"id": user_id}
        )
        db.session.commit()
        flash(f"User '{user['username']}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting user: {e}", "danger")

    return redirect(url_for('admin_settings'))


@app.route('/delete_employee/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_employee(id):
    db.session.execute(
        text("DELETE FROM employees WHERE id=:id"),
        {"id": id}
    )
    db.session.commit()
    flash("Employee deleted successfully!", "success")
    return redirect(url_for('employees'))


@app.route('/get_project_payroll/<int:id>', methods=['GET'])
def get_project_payroll(id):
    result = db.session.execute(
        text("SELECT * FROM payroll WHERE id=:id"),
        {"id": id}
    ).fetchone()

    if result:
        return jsonify(dict(result))
    return jsonify({'error': 'Payroll record not found'}), 404


@app.route('/reports')
@roles_required("Admin", "Manager", "Assistant Manager")
def reports():
    report_result = db.session.execute(
        text("SELECT * FROM reports ORDER BY report_date DESC")
    )
    report_list = [dict(r) for r in report_result.fetchall()]

    projects_result = db.session.execute(
        text("SELECT id, project_name FROM projects ORDER BY project_name")
    )
    projects = [dict(p) for p in projects_result.fetchall()]

    return render_template(
        'reports.html',
        reports=report_list,
        projects=projects,
        username=session.get('username'),
        date=date
    )


@app.route('/generate_report', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def generate_report():
    report_type = request.form['report_type']
    created_by = session.get('username', 'Unknown')
    project_id = request.form.get('project_id')
    title = ""
    description = ""

    if report_type == "employees":
        title = "Employee Master List"
        description = "Complete list of all employees."

    elif report_type == "attendance_daily":
        date_selected = request.form.get('date', date.today().isoformat())
        title = f"Daily Attendance Report - {date_selected}"
        description = f"Employee attendance for {date_selected}"

    elif report_type == "attendance_monthly":
        month_selected = request.form.get('month', date.today().strftime('%Y-%m'))
        month_obj = datetime.strptime(month_selected, '%Y-%m')
        month_display = month_obj.strftime('%B %Y')
        title = "Monthly Attendance Summary"
        description = f"Summary of employee attendance for {month_display} (Month: {month_selected})"

    elif report_type == "payroll_employee":
        title = "Payroll Per Employee"
        description = "Payroll records grouped by employee with totals and averages."

    elif report_type == "payroll_project":
        if not project_id:
            flash("Please select a project for payroll report", "danger")
            return redirect(url_for('reports'))

        project = db.session.execute(
            text("SELECT project_name FROM projects WHERE id=:id"),
            {"id": project_id}
        ).fetchone()
        project_name = project['project_name'] if project else f"Project {project_id}"
        title = f"Payroll Report - {project_name}"
        description = f"Detailed payroll analysis for {project_name}"

    elif report_type == "project_list":
        if not project_id:
            flash("Please select a project for employee list", "danger")
            return redirect(url_for('reports'))

        project = db.session.execute(
            text("SELECT project_name FROM projects WHERE id=:id"),
            {"id": project_id}
        ).fetchone()
        project_name = project['project_name'] if project else f"Project {project_id}"
        title = f"Project Employee List - {project_name}"
        description = f"Employees assigned to {project_name}"

    # Insert report into DB and return the inserted id
    inserted_id = db.session.execute(
        text("""
            INSERT INTO reports (title, description, created_by, project_id)
            VALUES (:title, :description, :created_by, :project_id)
            RETURNING id
        """),
        {"title": title, "description": description, "created_by": created_by, "project_id": project_id}
    ).fetchone()['id']

    db.session.commit()
    flash(f'Report "{title}" generated successfully!', 'success')
    return redirect(url_for('view_report', id=inserted_id))

@app.route('/report/view/<int:id>')
@roles_required("Admin", "Manager", "Assistant Manager")
def view_report(id):
    # Fetch report
    report_row = db.session.execute(
        text("SELECT * FROM reports WHERE id = :id"), {"id": id}
    ).fetchone()

    if not report_row:
        flash("Report not found!", "danger")
        return redirect(url_for('reports'))

    report = dict(report_row)
    title = report['title']
    project_id = report.get('project_id')

    # 1. EMPLOYEE MASTER LIST
    if "Employee Master List" in title:
        employees = [dict(e) for e in db.session.execute(
            text("SELECT * FROM employees ORDER BY name")
        ).fetchall()]
        return render_template("report_employee_list.html", employees=employees, report=report)

    # 2. DAILY ATTENDANCE
    if "Daily Attendance" in title:
        date_str = report.get("description", "").split("for ")[-1] or date.today().isoformat()
        attendance_data = [dict(r) for r in db.session.execute(
            text("""
                SELECT e.name, e.department, e.position, a.status, a.date
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.date = :date
                ORDER BY e.name
            """), {"date": date_str}
        ).fetchall()]
        return render_template("report_attendance_daily.html", attendance_data=attendance_data, date=date_str, report=report)

    # 3. MONTHLY ATTENDANCE
    if "Monthly Attendance" in title:
        month = date.today().strftime("%Y-%m")
        description = report.get("description", "")
        if "Month:" in description:
            month = description.split("Month:")[-1].strip().rstrip(")")

        monthly_data = [dict(r) for r in db.session.execute(
            text("""
                SELECT
                    e.id,
                    e.name,
                    e.department,
                    e.position,
                    COUNT(a.id) AS days_recorded,
                    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS days_present,
                    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS days_absent,
                    SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS days_late,
                    CASE 
                        WHEN COUNT(a.id) > 0 THEN ROUND((SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)::numeric / COUNT(a.id)) * 100, 2)
                        ELSE 0
                    END AS attendance_rate
                FROM employees e
                LEFT JOIN attendance a ON e.id = a.employee_id AND TO_CHAR(a.date, 'YYYY-MM') = :month
                GROUP BY e.id, e.name, e.department, e.position
                ORDER BY e.department, e.name
            """), {"month": month}
        ).fetchall()]
        return render_template("report_attendance_monthly.html", monthly_data=monthly_data, month=month, report=report, now=datetime.now())

    # 4. PAYROLL PER EMPLOYEE
    if "Payroll Per Employee" in title:
        payroll_summary = [dict(r) for r in db.session.execute(
            text("""
                SELECT
                    e.id,
                    e.name,
                    e.department,
                    e.position,
                    COUNT(p.id) AS pay_records,
                    COALESCE(SUM(p.net_pay),0) AS total_earned,
                    COALESCE(AVG(p.net_pay),0) AS avg_pay,
                    MAX(p.pay_period_end) AS latest_pay_period
                FROM employees e
                LEFT JOIN payroll p ON e.id = p.employee_id
                GROUP BY e.id, e.name, e.department, e.position
                ORDER BY total_earned DESC, e.name
            """)
        ).fetchall()]

        payroll_entries = [dict(r) for r in db.session.execute(
            text("""
                SELECT e.name, e.department, e.position, p.pay_period_start, p.pay_period_end,
                       p.basic_salary, p.overtime, p.deductions, p.net_pay, p.status
                FROM payroll p
                JOIN employees e ON e.id = p.employee_id
                ORDER BY p.pay_period_end DESC, e.name
            """)
        ).fetchall()]

        total_payroll_cost = sum(r['total_earned'] or 0 for r in payroll_summary)
        total_employees = len(payroll_summary)
        employees_with_payroll = len([r for r in payroll_summary if r['total_earned'] > 0])
        avg_employee_pay = total_payroll_cost / employees_with_payroll if employees_with_payroll else 0
        latest_pay_period = max((r['latest_pay_period'] for r in payroll_summary if r['latest_pay_period']), default=None)

        return render_template("report_payroll_employee.html",
                               payroll_summary=payroll_summary,
                               payroll_entries=payroll_entries,
                               total_payroll_cost=total_payroll_cost,
                               total_employees=total_employees,
                               employees_with_payroll=employees_with_payroll,
                               avg_employee_pay=avg_employee_pay,
                               latest_pay_period=latest_pay_period,
                               report=report,
                               now=datetime.now())

    # 5. PAYROLL PER PROJECT
    if "Payroll Per Project" in title or "Payroll Report -" in title:
        project_filter = "WHERE p.id=:project_id" if project_id else ""
        project_data = [dict(r) for r in db.session.execute(
            text(f"""
                SELECT 
                    p.id as project_id,
                    p.project_name,
                    p.department,
                    p.status as project_status,
                    COUNT(DISTINCT pe.employee_id) as assigned_employees,
                    COUNT(pay.id) as payroll_records,
                    COALESCE(SUM(pay.net_pay),0) as total_payroll_cost,
                    COALESCE(AVG(pay.net_pay),0) as avg_employee_pay
                FROM projects p
                LEFT JOIN project_employees pe ON p.id = pe.project_id
                LEFT JOIN payroll pay ON p.id = pay.project_id
                {project_filter}
                GROUP BY p.id, p.project_name, p.department, p.status
                ORDER BY total_payroll_cost DESC
            """), {"project_id": project_id} if project_id else {}
        ).fetchall()]

        total_payroll_cost = sum(p['total_payroll_cost'] for p in project_data)
        total_employees = sum(p['assigned_employees'] for p in project_data)
        total_payroll_records = sum(p['payroll_records'] for p in project_data)
        avg_employee_cost = total_payroll_cost / total_employees if total_employees else 0

        return render_template("report_payroll_project.html",
                               project_data=project_data,
                               total_payroll_cost=total_payroll_cost,
                               total_employees=total_employees,
                               total_payroll_records=total_payroll_records,
                               avg_employee_cost=avg_employee_cost,
                               report=report,
                               now=datetime.now())

    # 6. PROJECT EMPLOYEE LIST
    if "Project Employee List" in title:
        rows = [dict(r) for r in db.session.execute(
            text("""
                SELECT 
                    p.id AS project_id, p.project_name, p.department AS project_department, p.status AS project_status,
                    e.id AS employee_id, e.name AS employee_name, e.position AS employee_position, e.department AS employee_department
                FROM projects p
                LEFT JOIN project_employees pe ON p.id = pe.project_id
                LEFT JOIN employees e ON pe.employee_id = e.id
                ORDER BY p.project_name, e.name
            """)
        ).fetchall()]

        projects_map = {}
        for row in rows:
            pid = row['project_id']
            if pid not in projects_map:
                projects_map[pid] = {
                    'project_id': pid,
                    'project_name': row['project_name'],
                    'project_department': row['project_department'],
                    'project_status': row['project_status'],
                    'employees': []
                }
            if row['employee_id']:
                projects_map[pid]['employees'].append({
                    'employee_id': row['employee_id'],
                    'name': row['employee_name'],
                    'position': row['employee_position'],
                    'department': row['employee_department']
                })

        projects_data = list(projects_map.values())
        total_projects = len(projects_data)
        total_assignments = sum(len(proj['employees']) for proj in projects_data)
        projects_with_staff = len([proj for proj in projects_data if proj['employees']])

        return render_template("report_project_employee.html",
                               projects_data=projects_data,
                               total_projects=total_projects,
                               total_assignments=total_assignments,
                               projects_with_staff=projects_with_staff,
                               report=report,
                               now=datetime.now())

    flash("Unknown report type.", "warning")
    return redirect(url_for('reports'))

@app.route('/download_report/<int:id>')
@roles_required("Admin", "Manager", "Assistant Manager")
def download_report(id):
    try:
        with db.engine.connect() as conn:
            # Fetch the report
            result = conn.execute(
                text("SELECT * FROM reports WHERE id = :id"),
                {"id": id}
            )
            report = result.mappings().first()

            if not report:
                flash("Report not found!", "danger")
                return redirect(url_for('reports'))

            report_title = report["title"]

            # -------------------------
            # EMPLOYEE MASTER LIST
            # -------------------------
            if "Employee Master List" in report_title:
                result = conn.execute(text("SELECT * FROM employees ORDER BY name"))
                data = result.mappings().all()
                return generate_text_report(
                    f"Employee Master List - {date.today()}",
                    data,
                    ["name", "position", "department", "status"]
                )

            # -------------------------
            # DAILY ATTENDANCE
            # -------------------------
            elif "Daily Attendance" in report_title:
                date_str = report["description"].split("for ")[-1] if "for " in report["description"] else date.today().isoformat()
                result = conn.execute(
                    text("""
                        SELECT e.name, e.department, e.position, a.status, a.date
                        FROM attendance a
                        JOIN employees e ON a.employee_id = e.id
                        WHERE a.date = :date_str
                        ORDER BY e.name
                    """),
                    {"date_str": date_str}
                )
                data = result.mappings().all()
                return generate_text_report(
                    f"Daily Attendance - {date_str}",
                    data,
                    ["name", "department", "position", "status", "date"]
                )

            # -------------------------
            # MONTHLY ATTENDANCE
            # -------------------------
            elif "Monthly Attendance Summary" in report_title:
                current_month = date.today().strftime('%Y-%m')
                result = conn.execute(
                    text("""
                        SELECT e.name, e.department, e.position,
                               COUNT(a.id) AS days_recorded,
                               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS days_present,
                               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS days_absent,
                               SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS days_late
                        FROM employees e
                        LEFT JOIN attendance a 
                               ON e.id = a.employee_id AND TO_CHAR(a.date, 'YYYY-MM') = :month
                        GROUP BY e.id, e.name, e.department, e.position
                        HAVING COUNT(a.id) > 0
                        ORDER BY e.department, e.name
                    """),
                    {"month": current_month}
                )
                data = result.mappings().all()
                return generate_text_report(
                    f"Monthly Attendance Summary - {current_month}",
                    data,
                    ["name", "department", "position", "days_recorded", "days_present", "days_absent", "days_late"]
                )

            # -------------------------
            # GENERIC FALLBACK
            # -------------------------
            else:
                content = f"Report: {report['title']}\n"
                content += f"Description: {report['description']}\n"
                content += f"Created By: {report['created_by']}\n"
                content += f"Date: {report['report_date']}\n"
                return generate_simple_text(content, f"report_{id}.txt")

    except Exception as e:
        print(f"Error downloading report: {e}")
        flash("Error downloading report", "danger")
        return redirect(url_for('reports'))


# -------------------------
# HELPER FUNCTIONS
# -------------------------
def generate_text_report(title, data, columns):
    """Generate a CSV report from data."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([title])
    writer.writerow([])
    writer.writerow(columns)

    # Data
    for row in data:
        writer.writerow([row.get(col, '') for col in columns])

    content = output.getvalue()
    output.close()

    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{title.replace(' ', '_')}_{date.today()}.csv",
        mimetype='text/csv'
    )


def generate_simple_text(content, filename):
    """Generate a simple text file download."""
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )
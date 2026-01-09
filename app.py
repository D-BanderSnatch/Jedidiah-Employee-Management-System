from calendar import month
from sqlite3 import Cursor
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify  # type: ignore
from datetime import date, datetime
from datetime import date

import mysql.connector  # type: ignore

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change later


# MySQL Config
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="employee_db"
)

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

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username already taken!", "danger")
            cursor.close()
            return redirect(url_for('register'))

        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        db.commit()
        cursor.close()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        session['username'] = user['username']
        # Normalize role from DB: accept small letters, etc.
        raw_role = user.get('account_type') or 'Employee'
        session['role'] = (raw_role.strip() or 'Employee').upper()
        return redirect(url_for('dashboard'))

    flash("Invalid username or password.", "danger")
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    cursor = db.cursor(dictionary=True)

    # Total employees
    cursor.execute("SELECT COUNT(*) AS total FROM employees")
    total_employees = cursor.fetchone()['total']

    # Active projects
    cursor.execute("SELECT COUNT(*) AS total FROM projects WHERE status='Active'")
    active_projects = cursor.fetchone()['total']

    # Attendance Rate Today
    today = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) AS total FROM attendance WHERE date=%s", (today,))
    total_attendance = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS present FROM attendance WHERE date=%s AND status='Present'", (today,))
    present = cursor.fetchone()['present']

    attendance_rate = 0
    if total_attendance > 0:
        attendance_rate = round((present / total_attendance) * 100, 2)

    # Payroll This Month
    cursor.execute("""
        SELECT COALESCE(SUM(net_pay), 0) AS total 
        FROM payroll 
        WHERE MONTH(pay_period_end) = MONTH(CURRENT_DATE())
        AND YEAR(pay_period_end) = YEAR(CURRENT_DATE())
    """)
    payroll_month = cursor.fetchone()['total']

    cursor.close()

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
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    return render_template('employees.html', employees=employees, username=session.get('username'))

@app.route('/add_employee', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_employee():
    name = request.form['name']
    position = request.form['position']
    department = request.form['department']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute("INSERT INTO employees (name, position, department, status) VALUES (%s, %s, %s, %s)",
                   (name, position, department, status))
    db.commit()
    cursor.close()

    flash("Employee added successfully!", "success")
    return redirect(url_for('employees'))


@app.route('/update_employee', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def update_employee():
    emp_id = request.form['id']
    name = request.form['name']
    position = request.form['position']
    department = request.form['department']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute("""
        UPDATE employees 
        SET name=%s, position=%s, department=%s, status=%s 
        WHERE id=%s
    """, (name, position, department, status, emp_id))
    db.commit()
    cursor.close()

    flash("Employee updated successfully!", "success")
    return redirect(url_for('employees'))


@app.route('/attendance')
@login_required
def attendance():

    selected_date = request.args.get('date')
    if not selected_date:
        selected_date = date.today().isoformat()

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM employees ORDER BY name ASC")
    employees = cursor.fetchall()

    cursor.execute('''
        SELECT a.id, a.employee_id, e.name, e.department, a.date, a.status
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE a.date = %s
        ORDER BY e.name ASC
    ''', (selected_date,))
    
    attendance_records = cursor.fetchall()
    cursor.close()

    return render_template('attendance.html', 
                         employees=employees, 
                         attendance_records=attendance_records, 
                         date_today=selected_date,
                         username=session.get('username'))



@app.route('/add_attendance', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager", "Employee")
def add_attendance():
    employee_id = request.form['employee_id']
    date = request.form['date']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute('''INSERT INTO attendance (employee_id, date, status)
                      VALUES (%s, %s, %s)''', (employee_id, date, status))
    db.commit()
    cursor.close()

    flash('Attendance added successfully!', 'success')
    return redirect(url_for('attendance'))

@app.route('/edit_attendance/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_attendance(id):
    employee_id = request.form['employee_id']
    date = request.form['date']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute('''UPDATE attendance
                      SET employee_id=%s, date=%s, status=%s
                      WHERE id=%s''', (employee_id, date, status, id))
    db.commit()
    cursor.close()

    flash('Attendance updated successfully!', 'success')
    return redirect(url_for('attendance'))

@app.route('/delete_attendance/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_attendance(id):
    cursor = db.cursor()
    cursor.execute('DELETE FROM attendance WHERE id = %s', (id,))
    db.commit()
    cursor.close()

    flash('Attendance record deleted successfully!', 'success')
    return redirect(url_for('attendance'))

@app.route('/projects')
@login_required
def projects():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects")
    projects = cursor.fetchall()
    cursor.execute("SELECT id, name FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    return render_template('projects.html', projects=projects, employees=employees, username=session.get('username'))

@app.route('/project_employees/<int:project_id>')
@login_required
def project_employees(project_id):
    """Get list of employees assigned to a project."""
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id, e.name, e.position 
        FROM project_employees pe
        JOIN employees e ON pe.employee_id = e.id
        WHERE pe.project_id = %s
        ORDER BY e.name
    """, (project_id,))
    
    employees = cursor.fetchall()
    cursor.close()
    
    return jsonify(employees)


@app.route('/edit_project/<int:id>', methods=['GET', 'POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_project(id):
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        project_name = request.form['project_name']
        department = request.form['department']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']
        employee_ids = request.form.getlist('employees')

        cursor.execute('''UPDATE projects
                          SET project_name=%s, department=%s, start_date=%s, end_date=%s, status=%s
                          WHERE id=%s''', (project_name, department, start_date, end_date, status, id))

        cursor.execute('DELETE FROM project_employees WHERE project_id = %s', (id,))
        for emp_id in employee_ids:
            cursor.execute('INSERT INTO project_employees (project_id, employee_id) VALUES (%s, %s)', (id, emp_id))

        db.commit()
        cursor.close()

        flash('Project and assigned employees updated successfully!', 'success')
        return redirect(url_for('projects'))

    cursor.execute('SELECT * FROM projects WHERE id = %s', (id,))
    project = cursor.fetchone()
    cursor.execute('SELECT id, name FROM employees')
    employees = cursor.fetchall()
    cursor.execute('SELECT employee_id FROM project_employees WHERE project_id = %s', (id,))
    assigned = [row['employee_id'] for row in cursor.fetchall()]
    cursor.close()

    return render_template('edit_project.html', project=project, employees=employees, assigned=assigned)

@app.route('/add_project', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def add_project():
    project_name = request.form['project_name']
    department = request.form['department']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    status = request.form['status']
    employee_ids = request.form.getlist('employees')

    cursor = db.cursor()
    cursor.execute('''INSERT INTO projects (project_name, department, start_date, end_date, status)
                      VALUES (%s, %s, %s, %s, %s)''', (project_name, department, start_date, end_date, status))
    project_id = cursor.lastrowid

    for emp_id in employee_ids:
        cursor.execute('INSERT INTO project_employees (project_id, employee_id) VALUES (%s, %s)', (project_id, emp_id))

    db.commit()
    cursor.close()

    flash('Project and employees added successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/update_project', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def update_project():
    project_id = request.form['id']
    project_name = request.form['project_name']
    department = request.form['department']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute('''UPDATE projects SET project_name=%s, department=%s, start_date=%s, end_date=%s, status=%s WHERE id=%s''',
                   (project_name, department, start_date, end_date, status, project_id))
    db.commit()
    cursor.close()

    flash('Project updated successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/delete_project/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_project(id):
    cursor = db.cursor()
    cursor.execute('DELETE FROM projects WHERE id = %s', (id,))
    db.commit()
    cursor.close()

    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/payroll')
@login_required
def payroll():
    cursor = db.cursor(dictionary=True)
    
    # Fetch all payroll records with employee and project information
    cursor.execute('''SELECT p.*, e.name, e.position, pr.project_name, pr.id as project_id
                      FROM payroll p
                      JOIN employees e ON p.employee_id = e.id
                      LEFT JOIN projects pr ON p.project_id = pr.id
                      ORDER BY p.pay_period_end DESC, p.created_at DESC''')
    payroll_records = cursor.fetchall()
    
    # Fetch all employees for the dropdown
    cursor.execute("SELECT id, name, position FROM employees")
    employees = cursor.fetchall()
    
    # Fetch all projects for the dropdown
    cursor.execute("SELECT id, project_name FROM projects ORDER BY project_name")
    projects = cursor.fetchall()
    
    # Calculate summary statistics
    cursor.execute('''SELECT 
                      COUNT(*) as employees_paid,
                      COALESCE(SUM(COALESCE(gross_pay, basic_salary + overtime)), 0) as total_gross_pay,
                      COALESCE(SUM(COALESCE(total_deductions, deductions)), 0) as total_deductions,
                      COALESCE(SUM(net_pay), 0) as total_net_pay
                      FROM payroll''')
    summary = cursor.fetchone()
    
    cursor.close()
    
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
    
    # Try to read Excel-style fields first, fall back to legacy if not present
    daily_rate = float(request.form.get('daily_rate', 0) or 0)
    meal = float(request.form.get('meal', 0) or 0)
    transpo = float(request.form.get('transpo', 0) or 0)
    days_worked = int(request.form.get('days_worked', 0) or 0)
    # Try to read Excel-style fields first, fall back to legacy if not present
    daily_rate = float(request.form.get('daily_rate', 0) or 0)
    meal = float(request.form.get('meal', 0) or 0)
    transpo = float(request.form.get('transpo', 0) or 0)
    days_worked = int(request.form.get('days_worked', 0) or 0)
    total_ot_hours = float(request.form.get('total_ot_hours', 0) or 0)
    holiday_pay = float(request.form.get('holiday_pay', 0) or 0)
    holiday_pay_amount = float(request.form.get('holiday_pay_amount', 0) or 0)
    others = float(request.form.get('others', 0) or 0)
    cash_advance = float(request.form.get('cash_advance', 0) or 0)
    
    # If using simple fields (basic_salary provided), use those
    if request.form.get('basic_salary'):
        basic_salary = float(request.form.get('basic_salary', 0) or 0)
        overtime = float(request.form.get('overtime', 0) or 0)
        deductions = float(request.form.get('deductions', 0) or 0)
        net_pay = basic_salary + overtime - deductions
        
        # Calculate Excel-style fields from legacy fields
        if daily_rate == 0 and days_worked == 0:
            # Estimate: assume basic_salary is for 1 day if days_worked is 0
            total_daily_salary = basic_salary if days_worked == 0 else basic_salary / max(days_worked, 1)
        else:
            total_daily_salary = daily_rate + meal + transpo
        
        ot_amount = overtime if total_ot_hours == 0 else (daily_rate / 8) * 1.25 * total_ot_hours if daily_rate > 0 else 0
        total_deductions = deductions if cash_advance == 0 else cash_advance
        gross_pay = basic_salary + overtime
    else:
        # Using Excel-style fields
        total_daily_salary = daily_rate + meal + transpo
        ot_amount = (daily_rate / 8) * 1.25 * total_ot_hours if daily_rate > 0 else 0
        total_deductions = cash_advance
        gross_pay = (total_daily_salary * days_worked) + ot_amount + holiday_pay_amount + others
        net_pay = gross_pay - total_deductions
        
        # Legacy fields for backward compatibility
        basic_salary = total_daily_salary * days_worked
        overtime = ot_amount
        deductions = total_deductions
    
    status = request.form.get('status', 'Pending')
    
    cursor = db.cursor()
    
    # Insert payroll record
    cursor.execute('''INSERT INTO payroll 
                      (employee_id, project_id, pay_period_start, pay_period_end, position,
                       daily_rate, meal, transpo, total_daily_salary, days_worked,
                       total_ot_hours, ot_amount, holiday_pay, holiday_pay_amount, others,
                       cash_advance, total_deductions, gross_pay, net_pay,
                       basic_salary, overtime, deductions, status)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                   (employee_id, project_id, pay_period_start, pay_period_end, position,
                    daily_rate, meal, transpo, total_daily_salary, days_worked,
                    total_ot_hours, ot_amount, holiday_pay, holiday_pay_amount, others,
                    cash_advance, total_deductions, gross_pay, net_pay,
                    basic_salary, overtime, deductions, status))
    
    # If project_id is provided, ensure employee is assigned to project_employees table
    if project_id:
        cursor.execute('SELECT * FROM project_employees WHERE employee_id = %s AND project_id = %s', 
                      (employee_id, project_id))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute('INSERT INTO project_employees (employee_id, project_id) VALUES (%s, %s)', 
                          (employee_id, project_id))
    
    db.commit()
    cursor.close()
    
    if project_id:
        flash('Payroll record added successfully and employee assigned to project!', 'success')
    else:
        flash('Payroll record added successfully!', 'success')
    
    # Redirect back to project payroll if project_id was provided
    if project_id:
        return redirect(url_for('project_payroll', project_id=project_id))
    return redirect(url_for('payroll'))

@app.route('/edit_payroll', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def edit_payroll():
    cursor = db.cursor(dictionary=True)

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

        cursor.execute('''
            UPDATE payroll 
            SET employee_id=%s,
                project_id=%s,
                pay_period_start=%s,
                pay_period_end=%s,
                basic_salary=%s,
                overtime=%s,
                deductions=%s,
                gross_pay=%s,
                total_deductions=%s,
                net_pay=%s,
                status=%s
            WHERE id=%s
        ''', (employee_id, project_id, pay_period_start, pay_period_end,
              basic_salary, overtime, deductions,
              gross_pay, total_deductions, net_pay,
              status, id))

        db.commit()
        cursor.close()
        flash('Payroll record updated successfully!', 'success')

        if project_id:
            return redirect(url_for('project_payroll', project_id=project_id))
        return redirect(url_for('payroll'))

    except Exception as e:
        db.rollback()
        cursor.close()
        flash(f'Error updating payroll: {str(e)}', 'danger')
        return redirect(url_for('payroll'))


@app.route('/get_payroll/<int:id>', methods=['GET'])
@roles_required("Admin", "Manager", "Assistant Manager")
def get_payroll(id):
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM payroll WHERE id = %s', (id,))
    record = cursor.fetchone()
    cursor.close()

    if record:
        return jsonify(record)
    else:
        return jsonify({'error': 'Record not found'}), 404


@app.route('/delete_payroll/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_payroll(id):
    cursor = db.cursor(dictionary=True)
    # Get project_id before deleting (for redirect)
    cursor.execute('SELECT project_id FROM payroll WHERE id = %s', (id,))
    payroll_record = cursor.fetchone()
    project_id = payroll_record['project_id'] if payroll_record else None
    
    cursor.execute('DELETE FROM payroll WHERE id = %s', (id,))
    db.commit()
    cursor.close()
    
    flash('Payroll record deleted successfully!', 'success')
    
    # Redirect back to project payroll if it was linked to a project
    if project_id:
        return redirect(url_for('project_payroll', project_id=project_id))
    return redirect(url_for('payroll'))

@app.route('/payroll_overview')
@login_required
def payroll_overview():
    cursor = db.cursor(dictionary=True)
    
    # Get all projects with their total payroll cost and employee count
    cursor.execute('''
        SELECT 
            pr.id,
            pr.project_name,
            pr.department,
            pr.status,
            COALESCE((SELECT SUM(net_pay) FROM payroll WHERE project_id = pr.id), 0) as total_payroll_cost,
            COALESCE((SELECT COUNT(DISTINCT employee_id) FROM project_employees WHERE project_id = pr.id), 0) as employee_count,
            COALESCE((SELECT COUNT(DISTINCT employee_id) FROM payroll WHERE project_id = pr.id), 0) as employees_with_payroll,
            COALESCE((SELECT COUNT(*) FROM payroll WHERE project_id = pr.id), 0) as payroll_record_count
        FROM projects pr
        ORDER BY pr.project_name
    ''')
    projects = cursor.fetchall()
    
    cursor.close()
    
    return render_template('payroll_overview.html', 
                         projects=projects,
                         username=session.get('username'))

@app.route('/project_payroll/<int:project_id>')
@login_required
def project_payroll(project_id):
    cursor = db.cursor(dictionary=True)
    
    # Get project details
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    
    if not project:
        flash('Project not found!', 'danger')
        cursor.close()
        return redirect(url_for('payroll_overview'))
    
    # Get all employees assigned to this project (aligned with projects.html)
    cursor.execute('''
        SELECT 
            e.id as employee_id,
            e.name,
            e.position
        FROM employees e
        JOIN project_employees pe ON e.id = pe.employee_id
        WHERE pe.project_id = %s
        ORDER BY e.name
    ''', (project_id,))
    assigned_employees = cursor.fetchall()
    
    cursor.execute('''
        SELECT 
            e.id as employee_id,
            e.name,
            e.position,
            p.id as payroll_id,
            p.pay_period_start,
            p.pay_period_end,
            p.basic_salary,
            p.overtime,
            p.deductions,
            p.net_pay,
            p.status,
            p.gross_pay,
            p.total_deductions,
            p.daily_rate,
            p.meal,
            p.transpo,
            p.total_daily_salary,
            p.days_worked,
            p.total_ot_hours,
            p.ot_amount,
            p.holiday_pay,
            p.holiday_pay_amount,
            p.others,
            p.cash_advance,
            p.created_at
        FROM employees e
        JOIN project_employees pe ON e.id = pe.employee_id
        LEFT JOIN (
            SELECT 
                p1.*,
                ROW_NUMBER() OVER (PARTITION BY p1.employee_id ORDER BY p1.pay_period_end DESC, p1.created_at DESC) as rn
            FROM payroll p1
            WHERE p1.project_id = %s
        ) p ON e.id = p.employee_id AND p.rn = 1
        WHERE pe.project_id = %s
        ORDER BY e.name
    ''', (project_id, project_id))
    all_payroll_data = cursor.fetchall()
    
    # Build combined records - each assigned employee appears exactly once
    combined_records = []
    for record in all_payroll_data:
        if record['payroll_id'] is None:
            # Employee assigned but no payroll - show with 0 values
            combined_records.append({
                'employee_id': record['employee_id'],
                'id': None,
                'name': record['name'],
                'position': record['position'],
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
            # Employee has payroll - create full record
            combined_records.append({
                'employee_id': record['employee_id'],
                'id': record['payroll_id'],
                'name': record['name'],
                'position': record['position'],
                'pay_period_start': record['pay_period_start'],
                'pay_period_end': record['pay_period_end'],
                'basic_salary': record['basic_salary'] or 0,
                'overtime': record['overtime'] or 0,
                'deductions': record['deductions'] or 0,
                'net_pay': record['net_pay'] or 0,
                'status': record['status'],
                'gross_pay': record['gross_pay'],
                'total_deductions': record['total_deductions'],
                'daily_rate': record['daily_rate'],
                'meal': record['meal'],
                'transpo': record['transpo'],
                'total_daily_salary': record['total_daily_salary'],
                'days_worked': record['days_worked'],
                'total_ot_hours': record['total_ot_hours'],
                'ot_amount': record['ot_amount'],
                'holiday_pay': record['holiday_pay'],
                'holiday_pay_amount': record['holiday_pay_amount'],
                'others': record['others'],
                'cash_advance': record['cash_advance'],
                'created_at': record['created_at']
            })
    
    # Calculate summary for this project (only from actual payroll records)
    cursor.execute('''
        SELECT 
            COUNT(*) as employees_paid,
            COALESCE(SUM(COALESCE(gross_pay, basic_salary + overtime)), 0) as total_gross_pay,
            COALESCE(SUM(COALESCE(total_deductions, deductions)), 0) as total_deductions,
            COALESCE(SUM(net_pay), 0) as total_net_pay
        FROM payroll p
        WHERE p.project_id = %s
    ''', (project_id,))
    summary = cursor.fetchone()
    
    # Get all employees for the add payroll dropdown (allows adding payroll for any employee)
    cursor.execute("SELECT id, name, position FROM employees ORDER BY name")
    all_employees = cursor.fetchall() or []
    
    # Ensure assigned_employees is also a list (not None)
    if not assigned_employees:
        assigned_employees = []
    
    cursor.close()
    
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
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, username, account_type FROM users ORDER BY username")
    users = cursor.fetchall()
    cursor.close()

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

    cursor = db.cursor(dictionary=True)
    try:
        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username already taken!", "danger")
            cursor.close()
            return redirect(url_for('admin_settings'))

        # Insert new user
        cursor.execute("INSERT INTO users (username, password, account_type) VALUES (%s, %s, %s)", 
                      (username, password, account_type))
        db.commit()
        flash(f"User '{username}' added successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error adding user: {e}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('admin_settings'))


@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@roles_required("Admin")
def update_user(user_id: int):
    """Update username, password and/or role for a user."""
    new_username = request.form.get('username') or None
    new_password = request.form.get('password') or None
    new_role = request.form.get('account_type') or None

    fields = []
    values = []

    if new_username:
        fields.append("username = %s")
        values.append(new_username)
    if new_password:
        fields.append("password = %s")
        values.append(new_password)
    if new_role:
        fields.append("account_type = %s")
        values.append(new_role)

    if not fields:
        flash("No changes to update.", "info")
        return redirect(url_for('admin_settings'))

    values.append(user_id)

    cursor = db.cursor()
    try:
        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s", tuple(values))
        db.commit()
        flash("User updated successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating user: {e}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('admin_settings'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@roles_required("Admin")
def delete_user(user_id: int):
    """Delete a user account."""
    cursor = db.cursor(dictionary=True)
    try:
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found.", "danger")
            cursor.close()
            return redirect(url_for('admin_settings'))
        
        # Prevent deleting yourself
        if session.get('username') == user['username']:
            flash("You cannot delete your own account!", "danger")
            cursor.close()
            return redirect(url_for('admin_settings'))
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        flash(f"User '{user['username']}' deleted successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting user: {e}", "danger")
    finally:
        cursor.close()
    
    return redirect(url_for('admin_settings'))

@app.route('/delete_employee/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_employee(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM employees WHERE id = %s", (id,))
    db.commit()
    cursor.close()

    flash("Employee deleted successfully!", "success")
    return redirect(url_for('employees'))

@app.route('/get_project_payroll/<int:id>', methods=['GET'])
def get_project_payroll(id):
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM payroll WHERE id = %s', (id,))
    record = cursor.fetchone()
    cursor.close()

    if record:
        return jsonify(record)
    else:
        return jsonify({'error': 'Payroll record not found'}), 404



@app.route('/reports')
@roles_required("Admin", "Manager", "Assistant Manager")
def reports():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports ORDER BY report_date DESC")
    report_list = cursor.fetchall()
    
    # Fetch projects for the dropdown
    cursor.execute("SELECT id, project_name FROM projects ORDER BY project_name")
    projects = cursor.fetchall()
    
    cursor.close()

    return render_template('reports.html',
                           reports=report_list,
                           projects=projects,
                           username=session.get('username'),
                           date=date)

@app.route('/generate_report', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def generate_report():
    report_type = request.form['report_type']
    created_by = session.get('username', 'Unknown')
    project_id = request.form.get('project_id')
    title = ""
    description = ""

    # Auto-fill report title and description
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
        # Handle project-specific payroll report
        if not project_id:
            flash("Please select a project for payroll report", "danger")
            return redirect(url_for('reports'))
            
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        
        project_name = project['project_name'] if project else f"Project {project_id}"
        title = f"Payroll Report - {project_name}"
        description = f"Detailed payroll analysis for {project_name}"

    elif report_type == "project_list":
        if not project_id:
            flash("Please select a project for employee list", "danger")
            return redirect(url_for('reports'))
            
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()
        cursor.close()
        
        project_name = project['project_name'] if project else f"Project {project_id}"
        title = f"Project Employee List - {project_name}"
        description = f"Employees assigned to {project_name}"

    # Save into DB with project_id if provided
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO reports (title, description, created_by, project_id)
        VALUES (%s, %s, %s, %s)
    """, (title, description, created_by, project_id))
    db.commit()

    last_id = cursor.lastrowid
    cursor.close()

    flash(f'Report "{title}" generated successfully!', 'success')
    return redirect(url_for('view_report', id=last_id))
@app.route('/report/view/<int:id>')
@roles_required("Admin", "Manager", "Assistant Manager")
def view_report(id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports WHERE id=%s", (id,))
    report = cursor.fetchone()

    if not report:
        cursor.close()
        flash("Report not found!", "danger")
        return redirect(url_for('reports'))

    title = report["title"]
    project_id = report.get("project_id")

    # 1. EMPLOYEE MASTER LIST
    if "Employee Master List" in title:
        cursor.execute("SELECT * FROM employees ORDER BY name")
        employees = cursor.fetchall()
        cursor.close()
        return render_template("report_employee_list.html",
                               employees=employees,
                               report=report)

    # 2. DAILY ATTENDANCE
    elif "Daily Attendance" in title:
        date_str = report["description"].split("for ")[-1] if "for " in report["description"] else date.today().isoformat()
        
        cursor.execute("""
            SELECT e.name, e.department, e.position, a.status, a.date
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.date = %s
            ORDER BY e.name
        """, (date_str,))
        attendance_data = cursor.fetchall()
        cursor.close()
        return render_template("report_attendance_daily.html",
                               attendance_data=attendance_data,
                               date=date_str,
                               report=report)

    # 3. MONTHLY ATTENDANCE
    elif "Monthly Attendance" in title:
        # Default to current month; override with month from description if present
        month = date.today().strftime("%Y-%m")
        description = report.get("description", "")
        if "Month:" in description:
            try:
                # Extract the month value from the description, e.g. "(Month: 2024-05)"
                month_part = description.split("Month:")[-1].strip().rstrip(")")
                month = month_part
            except Exception:
                pass

        cursor.execute(
            """
            SELECT 
                e.id,
                e.name,
                e.department,
                e.position,
                COUNT(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s THEN a.id END) AS days_recorded,
                SUM(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s AND a.status = 'Present' THEN 1 ELSE 0 END) AS days_present,
                SUM(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s AND a.status = 'Absent' THEN 1 ELSE 0 END) AS days_absent,
                SUM(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s AND a.status = 'Late' THEN 1 ELSE 0 END) AS days_late,
                CASE 
                    WHEN COUNT(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s THEN a.id END) > 0 THEN 
                        ROUND(
                            (
                                SUM(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s AND a.status = 'Present' THEN 1 ELSE 0 END) / 
                                COUNT(CASE WHEN DATE_FORMAT(a.date, '%%Y-%%m') = %s THEN a.id END)
                            ) * 100,
                            2
                        )
                    ELSE 0 
                END AS attendance_rate
            FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id
            GROUP BY e.id, e.name, e.department, e.position
            ORDER BY e.department, e.name
        """,
            (month, month, month, month, month, month, month),
        )
        monthly_data = cursor.fetchall()
        cursor.close()

        return render_template(
            "report_attendance_monthly.html",
            month=month,
            monthly_data=monthly_data,
            report=report,
            now=datetime.now(),
        )

    # 4. PAYROLL PER EMPLOYEE
    elif "Payroll Per Employee" in title:
        # Summary per employee
        cursor.execute("""
            SELECT 
                e.id,
                e.name,
                e.department,
                e.position,
                COUNT(p.id) AS pay_records,
                COALESCE(SUM(p.net_pay), 0) AS total_earned,
                COALESCE(AVG(p.net_pay), 0) AS avg_pay,
                MAX(p.pay_period_end) AS latest_pay_period
            FROM employees e
            LEFT JOIN payroll p ON e.id = p.employee_id
            GROUP BY e.id, e.name, e.department, e.position
            ORDER BY total_earned DESC, e.name
        """)
        payroll_summary = cursor.fetchall()

        # Detailed payroll entries
        cursor.execute("""
            SELECT 
                e.name,
                e.department,
                e.position,
                p.pay_period_start,
                p.pay_period_end,
                p.basic_salary,
                p.overtime,
                p.deductions,
                p.net_pay,
                p.status
            FROM payroll p
            JOIN employees e ON p.employee_id = e.id
            ORDER BY p.pay_period_end DESC, e.name
        """)
        payroll_entries = cursor.fetchall()
        cursor.close()

        total_payroll_cost = sum(row['total_earned'] or 0 for row in payroll_summary)
        total_employees = len(payroll_summary)
        employees_with_payroll = len([row for row in payroll_summary if (row['total_earned'] or 0) > 0])
        avg_employee_pay = total_payroll_cost / employees_with_payroll if employees_with_payroll else 0
        latest_pay_period = None
        for row in payroll_summary:
            if row['latest_pay_period']:
                if not latest_pay_period or row['latest_pay_period'] > latest_pay_period:
                    latest_pay_period = row['latest_pay_period']

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
    elif "Payroll Per Project" in title or "Payroll Report -" in title:
        if project_id:
            cursor.execute("""
                SELECT 
                    p.id as project_id,
                    p.project_name,
                    p.department,
                    p.status as project_status,
                    COUNT(DISTINCT pe.employee_id) as assigned_employees,
                    COUNT(pay.id) as payroll_records,
                    COALESCE(SUM(pay.net_pay), 0) as total_payroll_cost,
                    COALESCE(AVG(pay.net_pay), 0) as avg_employee_pay
                FROM projects p
                LEFT JOIN project_employees pe ON p.id = pe.project_id
                LEFT JOIN payroll pay ON p.id = pay.project_id
                WHERE p.id = %s
                GROUP BY p.id, p.project_name, p.department, p.status
                ORDER BY total_payroll_cost DESC
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT 
                    p.id as project_id,
                    p.project_name,
                    p.department,
                    p.status as project_status,
                    COUNT(DISTINCT pe.employee_id) as assigned_employees,
                    COUNT(pay.id) as payroll_records,
                    COALESCE(SUM(pay.net_pay), 0) as total_payroll_cost,
                    COALESCE(AVG(pay.net_pay), 0) as avg_employee_pay
                FROM projects p
                LEFT JOIN project_employees pe ON p.id = pe.project_id
                LEFT JOIN payroll pay ON p.id = pay.project_id
                GROUP BY p.id, p.project_name, p.department, p.status
                ORDER BY total_payroll_cost DESC
            """)
        
        project_data = cursor.fetchall()
        
        total_payroll_cost = sum(project['total_payroll_cost'] for project in project_data)
        total_employees = sum(project['assigned_employees'] for project in project_data)
        total_payroll_records = sum(project['payroll_records'] for project in project_data)
        avg_employee_cost = total_payroll_cost / total_employees if total_employees > 0 else 0
        
        cursor.close()
        return render_template("report_payroll_project.html", 
                             project_data=project_data,
                             total_payroll_cost=total_payroll_cost,
                             total_employees=total_employees,
                             total_payroll_records=total_payroll_records,
                             avg_employee_cost=avg_employee_cost,
                             report=report,
                             now=datetime.now())

    # 6. PROJECT EMPLOYEE LIST
    elif "Project Employee List" in title:
        cursor.execute("""
            SELECT 
                p.id AS project_id,
                p.project_name,
                p.department AS project_department,
                p.status AS project_status,
                e.id AS employee_id,
                e.name AS employee_name,
                e.position AS employee_position,
                e.department AS employee_department
            FROM projects p
            LEFT JOIN project_employees pe ON p.id = pe.project_id
            LEFT JOIN employees e ON pe.employee_id = e.id
            ORDER BY p.project_name, e.name
        """)
        rows = cursor.fetchall()
        cursor.close()

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

    # 7. PAYROLL PER PROJECT (Single Project)
    elif "Payroll Report -" in title:
        if not project_id:
            flash("Project information not found in report", "danger")
            return redirect(url_for('reports'))

        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project_info = cursor.fetchone()

        cursor.execute("""
            SELECT 
                e.id as employee_id,
                e.name,
                e.position,
                p.pay_period_start,
                p.pay_period_end,
                p.basic_salary,
                p.overtime,
                p.deductions,
                p.net_pay,
                p.status,
                p.created_at as payroll_date
            FROM employees e
            JOIN project_employees pe ON e.id = pe.employee_id
            LEFT JOIN payroll p ON e.id = p.employee_id AND p.project_id = %s
            WHERE pe.project_id = %s
            ORDER BY e.name, p.pay_period_end DESC
        """, (project_id, project_id))
        payroll_data = cursor.fetchall()

        total_basic_salary = sum(emp['basic_salary'] or 0 for emp in payroll_data)
        total_overtime = sum(emp['overtime'] or 0 for emp in payroll_data)
        total_deductions = sum(emp['deductions'] or 0 for emp in payroll_data)
        total_net_pay = sum(emp['net_pay'] or 0 for emp in payroll_data)
        
        total_employees = len(set(emp['employee_id'] for emp in payroll_data))
        employees_with_payroll = len([emp for emp in payroll_data if emp['net_pay'] is not None])
        avg_employee_pay = total_net_pay / employees_with_payroll if employees_with_payroll > 0 else 0

        cursor.execute("""
            SELECT 
                pay_period_start,
                pay_period_end,
                COUNT(DISTINCT employee_id) as employee_count,
                SUM(basic_salary) as total_basic_salary,
                SUM(overtime) as total_overtime,
                SUM(deductions) as total_deductions,
                SUM(net_pay) as total_net_pay
            FROM payroll 
            WHERE project_id = %s
            GROUP BY pay_period_start, pay_period_end
            ORDER BY pay_period_end DESC
        """, (project_id,))
        payroll_by_period = cursor.fetchall()

        cursor.close()
        
        return render_template("report_payroll_project.html", 
                             project_info=project_info,
                             payroll_data=payroll_data,
                             payroll_by_period=payroll_by_period,
                             total_basic_salary=total_basic_salary,
                             total_overtime=total_overtime,
                             total_deductions=total_deductions,
                             total_net_pay=total_net_pay,
                             total_employees=total_employees,
                             employees_with_payroll=employees_with_payroll,
                             avg_employee_pay=avg_employee_pay,
                             report=report,
                             now=datetime.now())

    # DEFAULT (Should never happen)
    cursor.close()
    flash("Unknown report type.", "warning")
    return redirect(url_for('reports'))

    # ... rest of existing code ...

def some_function():  # Ensure this code is within a function
    if "Monthly Attendance Summary" in reports["title"]:
        # Get current month if not specified
        current_month = date.today().strftime('%Y-%m')

        Cursor.execute('''
            SELECT 
                e.name,
                e.department,
                e.position,
                COUNT(a.id) as days_recorded,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as days_present,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as days_absent,
                SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as days_late,
                CASE 
                    WHEN COUNT(a.id) > 0 THEN 
                        ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 2)
                    ELSE 0 
                END as attendance_rate
            FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id AND DATE_FORMAT(a.date, '%%Y-%%m') = %s
            GROUP BY e.id, e.name, e.department, e.position
            HAVING days_recorded > 0
            ORDER BY e.department, e.name
        ''', (current_month,))
        monthly_data = Cursor.fetchall()
        Cursor.close()
        return render_template("report_attendance_monthly.html", 
                             monthly_data=monthly_data, 
                             month=current_month,
                             now=datetime.now())

    elif "Payroll Per Employee" in reports["title"]:
        Cursor.execute('''
            SELECT 
                e.id,
                e.name,
                e.position,
                e.department,
                COUNT(p.id) as pay_records,
                COALESCE(SUM(p.net_pay), 0) as total_earned,
                COALESCE(AVG(p.net_pay), 0) as avg_pay,
                COALESCE(MAX(p.pay_period_end), 'No records') as latest_pay_period
            FROM employees e
            LEFT JOIN payroll p ON e.id = p.employee_id
            GROUP BY e.id, e.name, e.position, e.department
            ORDER BY total_earned DESC
        ''')
        payroll_by_employee = Cursor.fetchall()
        Cursor.close()
        return render_template("report_payroll_employee.html", 
                             payroll_data=payroll_by_employee)

    elif "Payroll Per Project" in reports["title"]:
        Cursor.execute('''
            SELECT 
                p.id as project_id,
                p.project_name,
                p.department,
                p.status as project_status,
                COUNT(DISTINCT pe.employee_id) as assigned_employees,
                COUNT(pay.id) as payroll_records,
                COALESCE(SUM(pay.net_pay), 0) as total_payroll_cost,
                COALESCE(AVG(pay.net_pay), 0) as avg_employee_pay
            FROM projects p
            LEFT JOIN project_employees pe ON p.id = pe.project_id
            LEFT JOIN payroll pay ON p.id = pay.project_id
            GROUP BY p.id, p.project_name, p.department, p.status
            ORDER BY total_payroll_cost DESC
        ''')
        payroll_by_project = Cursor.fetchall()
        Cursor.close()
        return render_template("report_payroll_project.html", 
                             project_data=payroll_by_project)

    elif "Project Employee List" in reports["title"]:
        Cursor.execute('''
            SELECT 
                p.id as project_id,
                p.project_name,
                p.department,
                p.status as project_status,
                p.start_date,
                p.end_date,
                GROUP_CONCAT(e.name ORDER BY e.name SEPARATOR ', ') as assigned_employees,
                COUNT(pe.employee_id) as employee_count
            FROM projects p
            LEFT JOIN project_employees pe ON p.id = pe.project_id
            LEFT JOIN employees e ON pe.employee_id = e.id
            GROUP BY p.id, p.project_name, p.department, p.status, p.start_date, p.end_date
            ORDER BY p.project_name
        ''')
        project_assignments = Cursor.fetchall()
        Cursor.close()
        return render_template("report_project_list.html", 
                             projects=project_assignments)

    Cursor.close()
    return f"Report type for '{reports['title']}' is not yet implemented."

@app.route('/download_report/<int:id>')
@roles_required("Admin", "Manager", "Assistant Manager")
def download_report(id):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reports WHERE id=%s", (id,))
        report = cursor.fetchone()
        
        if not report:
            flash("Report not found!", "danger")
            return redirect(url_for('reports'))
        
        # Determine report type and generate appropriate content
        report_title = report["title"]
        
        if "Employee Master List" in report_title:
            cursor.execute("SELECT * FROM employees ORDER BY name")
            data = cursor.fetchall()
            # For now, return a simple text file
            return generate_text_report(f"Employee Master List - {date.today()}", data, ["name", "position", "department", "status"])
        
        elif "Daily Attendance" in report_title:
            date_str = report["description"].split("for ")[-1] if "for " in report["description"] else date.today().isoformat()
            cursor.execute('''
                SELECT e.name, e.department, e.position, a.status, a.date
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.date = %s
                ORDER BY e.name
            ''', (date_str,))
            data = cursor.fetchall()
            return generate_text_report(f"Daily Attendance - {date_str}", data, ["name", "department", "position", "status", "date"])
        
        elif "Monthly Attendance Summary" in report_title:
            current_month = date.today().strftime('%Y-%m')
            cursor.execute('''
                SELECT e.name, e.department, e.position,
                       COUNT(a.id) as days_recorded,
                       SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as days_present,
                       SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as days_absent,
                       SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as days_late
                FROM employees e
                LEFT JOIN attendance a ON e.id = a.employee_id AND DATE_FORMAT(a.date, '%%Y-%%m') = %s
                GROUP BY e.id, e.name, e.department, e.position
                HAVING days_recorded > 0
                ORDER BY e.department, e.name
            ''', (current_month,))
            data = cursor.fetchall()
            return generate_text_report(f"Monthly Attendance Summary - {current_month}", data, 
                                      ["name", "department", "position", "days_recorded", "days_present", "days_absent", "days_late"])
        
        else:
            # Generic report download
            content = f"Report: {report['title']}\n"
            content += f"Description: {report['description']}\n"
            content += f"Created By: {report['created_by']}\n"
            content += f"Date: {report['report_date']}\n"
            return generate_simple_text(content, f"report_{id}.txt")
            
    except Exception as e:
        print(f"Error downloading report: {e}")
        flash("Error downloading report", "danger")
        return redirect(url_for('reports'))
    finally:
        cursor.close()

def generate_text_report(title, data, columns):
    """Generate a text file report from data"""
    from io import StringIO
    import csv
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([title])
    writer.writerow([])
    writer.writerow(columns)
    
    # Write data
    for row in data:
        writer.writerow([row.get(col, '') for col in columns])
    
    content = output.getvalue()
    output.close()
    
    from io import BytesIO
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    
    from flask import send_file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{title.replace(' ', '_')}_{date.today()}.csv",
        mimetype='text/csv'
    )

def generate_simple_text(content, filename):
    
    from io import BytesIO
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    
    from flask import send_file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

@app.route('/delete_report/<int:id>', methods=['POST'])
@roles_required("Admin", "Manager", "Assistant Manager")
def delete_report(id):
    cursor = db.cursor()
    
    try:
        # Delete the report from the database
        cursor.execute("DELETE FROM reports WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        
        flash('Report deleted successfully!', 'success')
    except Exception as e:
        db.rollback()
        cursor.close()
        flash(f'Error deleting report: {str(e)}', 'danger')
    
    return redirect(url_for('reports'))


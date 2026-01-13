-- PostgreSQL-compatible Employee DB with ENUMs converted to CHECKs

-- --------------------------------------------------------
-- Table: employees
-- --------------------------------------------------------
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','leave')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------
-- Table: projects
-- --------------------------------------------------------
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL,
    department VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    status TEXT DEFAULT 'Ongoing' CHECK (status IN ('Ongoing','Completed','On Hold'))
);

-- --------------------------------------------------------
-- Table: attendance
-- --------------------------------------------------------
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL,
    date DATE NOT NULL,
    status TEXT DEFAULT 'Present' CHECK (status IN ('Present','Absent','Leave','Late','Half Day','Sick Leave','Work From Home')),
    CONSTRAINT fk_attendance_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Table: payroll
-- --------------------------------------------------------
CREATE TABLE payroll (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL,
    project_id INT DEFAULT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    position VARCHAR(100) DEFAULT NULL,
    daily_rate DECIMAL(10,2) DEFAULT 0.00,
    meal DECIMAL(10,2) DEFAULT 0.00,
    transpo DECIMAL(10,2) DEFAULT 0.00,
    total_daily_salary DECIMAL(10,2) DEFAULT 0.00,
    days_worked INT DEFAULT 0,
    total_ot_hours DECIMAL(5,2) DEFAULT 0.00,
    ot_amount DECIMAL(10,2) DEFAULT 0.00,
    holiday_pay DECIMAL(10,2) DEFAULT 0.00,
    holiday_pay_amount DECIMAL(10,2) DEFAULT 0.00,
    others DECIMAL(10,2) DEFAULT 0.00,
    cash_advance DECIMAL(10,2) DEFAULT 0.00,
    total_deductions DECIMAL(10,2) DEFAULT 0.00,
    gross_pay DECIMAL(10,2) DEFAULT 0.00,
    net_pay DECIMAL(10,2) DEFAULT 0.00,
    basic_salary DECIMAL(10,2) DEFAULT 0.00,
    overtime DECIMAL(10,2) DEFAULT 0.00,
    deductions DECIMAL(10,2) DEFAULT 0.00,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payroll_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    CONSTRAINT fk_payroll_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Table: project_employees
-- --------------------------------------------------------
CREATE TABLE project_employees (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    employee_id INT NOT NULL,
    CONSTRAINT fk_project_emp_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_project_emp_employee FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Table: reports
-- --------------------------------------------------------
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    report_date DATE DEFAULT CURRENT_DATE,
    description TEXT,
    created_by VARCHAR(100),
    project_id INT,
    CONSTRAINT fk_reports_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Table: users
-- --------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    account_type TEXT DEFAULT 'employee'
);

-- --------------------------------------------------------
-- Example inserts (optional)
-- --------------------------------------------------------
/*
INSERT INTO employees (name, position, department, status) VALUES
('Jefrey', 'manager', 'Marketing', 'leave'),
('Magaling', 'wrds', 'HR', 'inactive'),
('Eddi', 'Sitins', 'Marketing', 'active'),
('Lanz', 'Senior High', 'IT', 'leave');
*/

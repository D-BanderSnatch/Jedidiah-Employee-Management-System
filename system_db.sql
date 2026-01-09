-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 02, 2025 at 01:35 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `employee_db`
--
CREATE DATABASE IF NOT EXISTS `employee_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `employee_db`;

-- --------------------------------------------------------

--
-- Table structure for table `attendance`
--

CREATE TABLE `attendance` (
  `id` int(11) NOT NULL,
  `employee_id` int(11) NOT NULL,
  `date` date NOT NULL,
  `status` enum('Present','Absent','Leave','Late','Half Day','Sick Leave','Work From Home') DEFAULT 'Present'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `attendance`
--

INSERT INTO `attendance` (`id`, `employee_id`, `date`, `status`) VALUES
(12, 3, '2025-11-07', 'Present'),
(13, 5, '2025-11-08', 'Absent'),
(14, 4, '2025-11-08', 'Work From Home'),
(15, 4, '2025-11-30', 'Present');

-- --------------------------------------------------------

--
-- Table structure for table `employees`
--

CREATE TABLE `employees` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `position` varchar(100) NOT NULL,
  `department` varchar(100) NOT NULL,
  `status` enum('active','inactive','leave') DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `employees`
--

INSERT INTO `employees` (`id`, `name`, `position`, `department`, `status`, `created_at`) VALUES
(2, 'Jefrey', 'manager', 'Marketing', 'leave', '2025-09-13 16:43:30'),
(3, 'Magaling', 'wrds', 'HR', 'inactive', '2025-10-30 12:05:57'),
(4, 'Eddi', 'Sitins', 'Marketing', 'active', '2025-10-30 15:28:59'),
(5, 'Lanz', 'Senior High', 'IT', 'leave', '2025-11-07 15:21:43');

-- --------------------------------------------------------

--
-- Table structure for table `payroll`
--

CREATE TABLE `payroll` (
  `id` int(11) NOT NULL,
  `employee_id` int(11) NOT NULL,
  `project_id` int(11) DEFAULT NULL,
  `pay_period_start` date NOT NULL,
  `pay_period_end` date NOT NULL,
  `position` varchar(100) DEFAULT NULL,
  `daily_rate` decimal(10,2) DEFAULT 0.00,
  `meal` decimal(10,2) DEFAULT 0.00,
  `transpo` decimal(10,2) DEFAULT 0.00,
  `total_daily_salary` decimal(10,2) DEFAULT 0.00,
  `days_worked` int(11) DEFAULT 0,
  `total_ot_hours` decimal(5,2) DEFAULT 0.00,
  `ot_amount` decimal(10,2) DEFAULT 0.00,
  `holiday_pay` decimal(10,2) DEFAULT 0.00,
  `holiday_pay_amount` decimal(10,2) DEFAULT 0.00,
  `others` decimal(10,2) DEFAULT 0.00,
  `cash_advance` decimal(10,2) DEFAULT 0.00,
  `total_deductions` decimal(10,2) DEFAULT 0.00,
  `gross_pay` decimal(10,2) DEFAULT 0.00,
  `net_pay` decimal(10,2) DEFAULT 0.00,
  `basic_salary` decimal(10,2) DEFAULT 0.00,
  `overtime` decimal(10,2) DEFAULT 0.00,
  `deductions` decimal(10,2) DEFAULT 0.00,
  `status` varchar(20) DEFAULT 'Pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payroll`
--

INSERT INTO `payroll` (`id`, `employee_id`, `project_id`, `pay_period_start`, `pay_period_end`, `position`, `daily_rate`, `meal`, `transpo`, `total_daily_salary`, `days_worked`, `total_ot_hours`, `ot_amount`, `holiday_pay`, `holiday_pay_amount`, `others`, `cash_advance`, `total_deductions`, `gross_pay`, `net_pay`, `basic_salary`, `overtime`, `deductions`, `status`, `created_at`) VALUES
(2, 3, 3, '2018-01-01', '2250-12-31', '', 0.00, 0.00, 0.00, 0.00, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1999.00, 1999.00, 1999.00, 0.00, 0.00, 'Paid', '2025-11-02 09:31:57'),
(8, 4, NULL, '2025-11-08', '2025-11-30', '', 0.00, 0.00, 0.00, 0.00, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1000.00, 1000.00, 1000.00, 0.00, 0.00, 'Paid', '2025-11-07 17:53:55'),
(10, 5, 10, '2025-11-08', '2025-11-30', '', 0.00, 0.00, 0.00, 5000.00, 0, 0.00, 100.00, 0.00, 0.00, 0.00, 0.00, 2000.00, 5100.00, 3100.00, 5000.00, 100.00, 2000.00, 'Paid', '2025-11-08 10:07:31'),
(11, 2, 10, '2025-11-08', '2025-11-30', '', 0.00, 0.00, 0.00, 10000.00, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 2000.00, 10000.00, 8000.00, 10000.00, 0.00, 2000.00, 'Paid', '2025-11-08 10:10:38'),
(12, 4, 3, '2025-12-11', '2025-12-31', '', 0.00, 0.00, 0.00, 10000.00, 0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 10000.00, 10000.00, 10000.00, 0.00, 0.00, 'Paid', '2025-12-01 10:11:06');

-- --------------------------------------------------------

--
-- Table structure for table `projects`
--

CREATE TABLE `projects` (
  `id` int(11) NOT NULL,
  `project_name` varchar(150) NOT NULL,
  `department` varchar(100) NOT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `status` enum('Ongoing','Completed','On Hold') DEFAULT 'Ongoing'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `projects`
--

INSERT INTO `projects` (`id`, `project_name`, `department`, `start_date`, `end_date`, `status`) VALUES
(3, 'Flood Control Project', 'Department of Public Works and Highways', '2018-01-01', '2250-12-31', 'Ongoing'),
(8, 'Pagasa', 'Vinz', '2025-11-07', '2025-11-30', 'Ongoing'),
(9, 'LAnz', 'IT', '2025-11-26', '2025-11-30', 'Ongoing'),
(10, 'Eron Home', 'Test', '2025-11-08', '2025-12-16', 'Ongoing');

-- --------------------------------------------------------

--
-- Table structure for table `project_employees`
--

CREATE TABLE `project_employees` (
  `id` int(11) NOT NULL,
  `project_id` int(11) NOT NULL,
  `employee_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `project_employees`
--

INSERT INTO `project_employees` (`id`, `project_id`, `employee_id`) VALUES
(13, 3, 3),
(22, 8, 2),
(23, 8, 3),
(24, 8, 4),
(25, 9, 2),
(26, 9, 3),
(27, 9, 4),
(28, 9, 5),
(32, 10, 2),
(33, 10, 3),
(34, 10, 5),
(35, 3, 4);

-- --------------------------------------------------------

--
-- Table structure for table `reports`
--

CREATE TABLE `reports` (
  `id` int(11) NOT NULL,
  `title` varchar(150) NOT NULL,
  `report_date` date DEFAULT curdate(),
  `description` text DEFAULT NULL,
  `created_by` varchar(100) DEFAULT NULL,
  `project_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `reports`
--

INSERT INTO `reports` (`id`, `title`, `report_date`, `description`, `created_by`, `project_id`) VALUES
(40, 'Employee Master List', '2025-12-01', 'Complete list of all employees.', 'admin', 10),
(41, 'Daily Attendance Report - 2025-11-30', '2025-12-01', 'Employee attendance for 2025-11-30', 'admin', 10),
(42, 'Payroll Per Employee', '2025-12-01', 'Payroll records grouped by employee with totals and averages.', 'admin', 10),
(43, 'Payroll Report - Eron Home', '2025-12-01', 'Detailed payroll analysis for Eron Home', 'admin', 10),
(45, 'Project Employee List - Pagasa', '2025-12-01', 'Employees assigned to Pagasa', 'admin', 8);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `account_type` varchar(50) NOT NULL DEFAULT 'employee'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `account_type`) VALUES
(1, 'admin', 'admin123', 'admin'),
(3, 'Ris', '1234', 'manager'),
(4, 'weew', '1234', 'employee');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `attendance`
--
ALTER TABLE `attendance`
  ADD PRIMARY KEY (`id`),
  ADD KEY `employee_id` (`employee_id`);

--
-- Indexes for table `employees`
--
ALTER TABLE `employees`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `payroll`
--
ALTER TABLE `payroll`
  ADD PRIMARY KEY (`id`),
  ADD KEY `employee_id` (`employee_id`),
  ADD KEY `idx_project_id` (`project_id`);

--
-- Indexes for table `projects`
--
ALTER TABLE `projects`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `project_employees`
--
ALTER TABLE `project_employees`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_project` (`project_id`),
  ADD KEY `idx_employee` (`employee_id`);

--
-- Indexes for table `reports`
--
ALTER TABLE `reports`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `attendance`
--
ALTER TABLE `attendance`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT for table `employees`
--
ALTER TABLE `employees`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `payroll`
--
ALTER TABLE `payroll`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT for table `projects`
--
ALTER TABLE `projects`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `project_employees`
--
ALTER TABLE `project_employees`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=36;

--
-- AUTO_INCREMENT for table `reports`
--
ALTER TABLE `reports`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=46;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `attendance`
--
ALTER TABLE `attendance`
  ADD CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `payroll`
--
ALTER TABLE `payroll`
  ADD CONSTRAINT `payroll_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payroll_ibfk_2` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `project_employees`
--
ALTER TABLE `project_employees`
  ADD CONSTRAINT `project_employees_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `project_employees_ibfk_2` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

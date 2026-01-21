-- SQL Script to delete specific academic years from the system
-- This removes the academic years: 2029/2030, 2028/2029, 2027/2028, 2026/2027, and 2025/2026

-- First, let's check what years exist in the database
SELECT * FROM system_academic_years ORDER BY start_year DESC;

-- Delete the specified academic years
DELETE FROM system_academic_years WHERE name = '2029/2030';
DELETE FROM system_academic_years WHERE name = '2028/2029';
DELETE FROM system_academic_years WHERE name = '2027/2028';
DELETE FROM system_academic_years WHERE name = '2026/2027';
DELETE FROM system_academic_years WHERE name = '2025/2026';

-- Verify that the specified years have been removed
SELECT * FROM system_academic_years ORDER BY start_year DESC;

-- Note: This will only remove the academic years from the system_academic_years table
-- Any related data in student_grades or student_attendance tables for these years will also be affected
-- due to foreign key constraints (they will be automatically removed)
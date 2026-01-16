/*
 * Healthcare Outcomes Analysis - Database Schema
 * See README.md for full documentation
 */

-- Drop tables if they exist (for re-run)
DROP TABLE IF EXISTS diagnoses;
DROP TABLE IF EXISTS admissions;
DROP TABLE IF EXISTS patients;

-- Patients Table
-- Stores core demographic information for individuals in the healthcare system
CREATE TABLE patients (
    patient_id      INT PRIMARY KEY AUTO_INCREMENT,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    birth_date      DATE,
    gender          ENUM('M', 'F', 'Other')
);

-- Admissions Table
-- Tracks hospital admissions and their outcomes for analysis of care effectiveness
CREATE TABLE admissions (
    admission_id    INT PRIMARY KEY AUTO_INCREMENT,
    patient_id      INT NOT NULL,
    admission_date  DATE NOT NULL,
    discharge_date  DATE,
    outcome         ENUM('Recovered', 'Readmitted', 'Deceased') NOT NULL,
    hospital        VARCHAR(100),
    CONSTRAINT fk_admissions_patient
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Diagnoses Table
-- Associates ICD-10 diagnosis codes with each admission
-- Supports analysis of conditions vs outcomes and readmission patterns
CREATE TABLE diagnoses (
    diagnosis_id    INT PRIMARY KEY AUTO_INCREMENT,
    admission_id    INT NOT NULL,
    icd_code        VARCHAR(10) NOT NULL,
    is_primary      BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_diagnoses_admission
        FOREIGN KEY (admission_id) REFERENCES admissions(admission_id)
);

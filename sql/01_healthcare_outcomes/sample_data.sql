/*
 * Sample Data - Simple manual INSERT example
 * Small curated dataset (4 patients) demonstrating manual data insertion.
 * For larger test datasets, use populate_mock_data.sql
 * See README.md for full documentation
 */

-- Sample patient records
INSERT INTO patients (first_name, last_name, birth_date, gender) VALUES
('Ali',   'Karimi', '1975-03-12', 'M'),
('Sara',  'Hosseini', '1985-07-25', 'F'),
('John',  'Doe', '1960-11-02', 'M'),
('Neda',  'Rahimi', '1990-01-15', 'F');

-- Sample admission records
INSERT INTO admissions (patient_id, admission_date, discharge_date, outcome, hospital) VALUES
(1, '2024-01-01', '2024-01-10', 'Recovered',  'General Hospital'),
(1, '2024-02-05', '2024-02-12', 'Readmitted', 'General Hospital'),
(2, '2024-01-20', '2024-01-27', 'Recovered',  'City Clinic'),
(3, '2024-01-10', '2024-01-25', 'Deceased',   'General Hospital'),
(4, '2024-03-01', '2024-03-05', 'Recovered',  'City Clinic');

-- Sample diagnoses (includes primary and secondary/comorbid diagnoses)
INSERT INTO diagnoses (admission_id, icd_code, is_primary) VALUES
(1, 'I10', TRUE),      -- Hypertension
(1, 'E11', FALSE),     -- Diabetes
(2, 'I10', TRUE),
(3, 'C34', TRUE),      -- Lung cancer
(4, 'J18', TRUE),      -- Pneumonia
(5, 'I10', TRUE);

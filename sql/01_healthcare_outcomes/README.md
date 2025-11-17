# Healthcare Outcomes Analysis

A comprehensive SQL analysis project for examining hospital admissions, patient outcomes, and healthcare delivery effectiveness. This project demonstrates advanced SQL techniques including CTEs, window functions, stored procedures, and data modeling for healthcare analytics.

## 📊 Project Overview

This project models a healthcare system with three core entities:
- **Patients**: Demographic information and basic records
- **Admissions**: Hospital admission records with outcomes (Recovered, Readmitted, Deceased)
- **Diagnoses**: ICD-10 diagnosis codes associated with each admission (primary and secondary/comorbid conditions)

### Key Relationships
- One patient can have multiple admissions (one-to-many)
- One admission can have multiple diagnoses (one-to-many)
- Supports analysis of readmission patterns, mortality rates, length of stay, and condition outcomes

## 📁 Files Structure

| File | Purpose |
|------|---------|
| `schema.sql` | Database schema definition with tables, constraints, and relationships |
| `sample_data.sql` | Simple example demonstrating manual data insertion (small curated dataset) |
| `populate_mock_data.sql` | Automated mock data generation using stored procedures (200+ patients, 600+ admissions) |
| `analysis_queries.sql` | Analytical queries including mortality rates, length of stay, readmission analysis |

## 🚀 Setup Instructions

### Prerequisites
- MySQL or MariaDB database server
- Access to create databases and stored procedures

### Installation Steps

1. **Create the database and schema:**
   ```sql
   CREATE DATABASE hospital_db;
   USE hospital_db;
   SOURCE schema.sql;
   ```

2. **Populate with data (choose one):**
   
   **Option A: Sample data (quick start, 4 patients):**
   ```sql
   SOURCE sample_data.sql;
   ```
   
   **Option B: Mock data (full dataset, recommended for analysis):**
   ```sql
   SOURCE populate_mock_data.sql;
   ```
   
   The mock data generator creates:
   - 200 patients (ages 14-84, randomized demographics)
   - 600 admissions (~3 per patient on average)
   - 1,200 diagnoses (~2 per admission on average)

3. **Run analysis queries:**
   ```sql
   SOURCE analysis_queries.sql;
   ```

## 📈 Key Features

### Data Generation (`populate_mock_data.sql`)
- **Realistic demographics**: Randomized patient ages, genders, and birth dates
- **Admission patterns**: 7 years of historical data (2018-2024), variable length of stay (0-20 days)
- **Medical coding**: 10 common ICD-10 diagnosis codes across multiple specialties
- **Outcome distribution**: Realistic distribution of Recovered, Readmitted, and Deceased outcomes
- **Active admissions**: 15% of admissions have NULL discharge_date (simulating current patients)

### Analysis Capabilities (`analysis_queries.sql`)
1. **Mortality Analysis**: Mortality rates by primary diagnosis
2. **Length of Stay**: Average LOS by hospital and diagnosis
3. **Readmission Tracking**: 30-day readmission rate calculations using window functions
4. **Hospital Performance**: Stored procedure for hospital-specific summaries
5. **Patient History**: View for latest admission per patient

## 🔍 Example Queries

### Mortality Rate by Diagnosis
```sql
-- Finds which conditions have the highest mortality rates
SELECT
    icd_code,
    COUNT(*) AS admissions_count,
    SUM(CASE WHEN outcome = 'Deceased' THEN 1 ELSE 0 END) AS deaths,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'Deceased' THEN 1 ELSE 0 END) / COUNT(*), 2) AS mortality_rate_pct
FROM diagnoses d
JOIN admissions a ON a.admission_id = d.admission_id
WHERE d.is_primary = TRUE
GROUP BY icd_code
ORDER BY mortality_rate_pct DESC;
```

### 30-Day Readmission Analysis
The project includes a sophisticated query using window functions to calculate readmission rates, identifying patients readmitted within 30 days of discharge.

### Hospital Performance Summary
```sql
-- Get summary statistics for a specific hospital
CALL sp_hospital_summary('General Hospital');
```

## 🎯 Use Cases

This project is designed for:
- **Healthcare Analytics**: Understanding admission patterns and outcomes
- **Quality Improvement**: Identifying high-risk conditions and readmission patterns
- **SQL Learning**: Demonstrating advanced SQL techniques in a real-world domain

## 📚 Technical Highlights

- **Advanced SQL Techniques**:
  - Common Table Expressions (CTEs)
  - Window Functions (ROW_NUMBER, PARTITION BY)
  - Stored Procedures with parameters
  - Views for reusable query patterns
  - Foreign key constraints and referential integrity

- **Data Modeling**:
  - Normalized database design
  - One-to-many relationships
  - Appropriate indexing strategy (via primary keys)
  - Data validation through ENUMs and constraints

## 🔧 Customization

You can adjust the data volumes in `populate_mock_data.sql`:
```sql
CALL populate_patients(500);    -- Change patient count
CALL populate_admissions(1500); -- Change admission count
CALL populate_diagnoses(3000);  -- Change diagnosis count
```

## 📝 Notes

- The sample data file demonstrates manual insertion patterns
- Mock data uses randomization; results will vary between runs
- All dates are historical (2018-2024) to enable trend analysis

## 👤 Author
**Amir Hosein VALIZADEH**  
📧 Email | 🔗 [GitHub](https://github.com/yourusername) | 💼 [LinkedIn](https://linkedin.com/in/yourprofile)

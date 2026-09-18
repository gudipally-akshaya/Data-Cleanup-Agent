# Data Cleanup Agent

## Overview

The Data Cleanup Agent is an intelligent customer-data quality and
deduplication system that converts messy customer records into a clean,
auditable master dataset.

The system accepts CSV, JSON, and XLSX files along with a natural-language
cleanup instruction.

It uses deterministic rules for clear duplicate decisions and uses AI only
for ambiguous candidate pairs that require additional investigation.

---

## Problem

Real-world customer datasets often contain:

- Duplicate records
- Missing values
- Formatting inconsistencies
- Conflicting customer information
- Outdated information
- Slight variations in names and addresses

Blindly merging similar records can result in two different customers being
incorrectly combined.

The Data Cleanup Agent therefore follows a conservative and explainable
cleanup process.

---

## Key Features

- CSV, JSON, and XLSX upload
- Natural-language cleanup instructions
- External customer schema mapping
- Field normalization
- Deterministic duplicate candidate generation
- Similarity scoring
- Conflict detection
- Automatic high-confidence merging
- AI investigation only for ambiguous cases
- Human-in-the-loop review
- Unsafe transitive merge prevention
- Missing-value recovery
- Clean master dataset generation
- Data Quality Report
- Decision audit trail
- CSV export
- XLSX export
- Decision-log export

---

## Processing Pipeline

User Instruction + Dataset
        |
        v
File Reader
        |
        v
Schema Mapping
        |
        v
Field Normalization
        |
        v
Candidate Generation
        |
        v
Similarity + Conflict Analysis
        |
        +-----------------------------+
        |                             |
        v                             v
Clear Decision                  Ambiguous Case
        |                             |
        v                             v
MERGE / KEEP SEPARATE            AI Investigation
                                      |
                                      v
                                 Human Review
                                      |
                                      v
                              Safe Merge Validation
                                      |
                                      v
                              Clean Master Dataset
                                      |
                         +------------+------------+
                         |                         |
                         v                         v
                  Data Quality Report        Decision Log
                         |
                         v
                   CSV / XLSX Export

---

## Safety Strategy

The agent does not automatically merge records based only on name similarity.

Strong identity evidence such as email and phone is considered during
duplicate analysis.

When identifying information conflicts, the system can preserve the records
separately or request human review.

The system also checks connected duplicate relationships before applying a
human-approved merge to prevent unsafe transitive merges.

---

## AI Usage

AI is not called for every customer record.

The deterministic pipeline first identifies candidate duplicate pairs and
classifies clear cases.

AI investigation is used only when a candidate remains ambiguous.

This makes the system more explainable, efficient, and conservative.

---

## Supported Input Formats

- CSV
- JSON
- XLSX

The prototype is designed for customer datasets containing recognizable
identity fields such as:

- Customer ID
- Name
- Email
- Phone
- Address
- City
- Last Updated
- Source

Common alternative column names can be mapped into the agent's internal
customer schema.

---

## Technology Stack

### Frontend

- React
- Vite
- JavaScript
- CSS

### Backend

- Python
- FastAPI
- Pandas
- RapidFuzz
- OpenPyXL

---

## Project Structure

DataCleanupAgent/
|
|-- backend/
|   |-- main.py
|   |-- cleanup.py
|   |-- candidate_generator.py
|   |-- matcher.py
|   |-- ai_reviewer.py
|   |-- master_data.py
|   |-- schema_mapper.py
|   |-- requirements.txt
|
|-- frontend/
|   |-- src/
|   |   |-- App.jsx
|   |   |-- App.css
|   |
|   |-- package.json
|
|-- sample_data/
|
|-- README.md

---

## Running the Backend

Open a terminal:

cd E:\DataCleanupAgent\backend

Activate the virtual environment:

.\venv\Scripts\Activate.ps1

Start FastAPI:

python -m uvicorn main:app

Backend:

http://127.0.0.1:8000

---

## Running the Frontend

Open another terminal:

cd E:\DataCleanupAgent\frontend

Run:

npm run dev

Frontend:

http://localhost:5173

---

## Example Cleanup Instruction

Find duplicate customer records. Merge only when you are confident;
flag uncertain cases.

---

## Output

The system produces:

1. Duplicate candidate analysis
2. Confidence scores
3. Merge / Review / Keep Separate decisions
4. AI investigation for ambiguous cases
5. Human-review controls
6. Data Quality Report
7. Clean master customer dataset
8. Decision audit trail
9. Downloadable CSV/XLSX output

---

## External Dataset Testing

The prototype has been tested with customer data containing:

- Exact duplicates
- Similar names
- Same names belonging to different people
- Conflicting phone numbers
- Missing values
- Address abbreviations
- Email case differences
- Phone-format differences
- Multiple source systems

The agent preserves uncertainty rather than performing unsafe automatic
merges.

---

## Future Scope

Possible production extensions include:

- Larger-scale blocking/indexing for millions of records
- Configurable field mappings
- Database integration
- Batch processing
- Authentication and role-based review
- Learning from approved human decisions
- Additional domain-specific entity resolution
# South African Medical Billing Bureau Platform

An enterprise medical billing bureau management platform built for South African healthcare practices. The system handles client practice management, patient claims processing, Medclaim EDI integration, electronic remittance advice (eRA) reconciliation, and collections.

## Architecture & System Features

- **Direct Switch Integration (Medclaim EDI)**: Integrates directly with BHF-accredited switches (MediSwitch, Healthbridge) via the Medclaim EDI standard, ensuring POPIA compliance, atomic transaction guarantees, and HPCSA-compliant billing pipelines.
- **Modular Switch Adapters**: Decoupled integration adapters using FHIR-inspired Data Transfer Objects (`ClaimDTO`). Enables easy integration of future switch providers.
- **Pre-Scrubbing Rules Engine**: `ClaimScrubber` registry that automatically validates claims for clinical and business rules (e.g., gender-ICD10 mismatch, age-tariff restrictions) *before* generating EDI batches, reducing switch-level rejections and saving costs.
- **POPIA / HIPAA Compliance Engine**: Enforces strict patient privacy via database-level deterministic AES encryption (`EncryptedCharField`) for Patient Health Information (PHI) and intercepts views with a `PHIReadLoggerMiddleware` for complete access auditing.
- **Versioned REST API v1 (`/api/v1/`)**: RESTful API endpoints for claim submission and bedside ward sync with mandatory `Idempotency-Key` headers to prevent duplicate claim rejections.
- **Offline Bedside Ward Sync**: Allows doctors rounding in hospital wards to capture consultations offline and batch-sync encounters atomically once connected to Wi-Fi.
- **eRA Reconciliation Engine**: Automated SFTP polling and multi-pass matching (exact reference, BHF + membership, patient surname, date tolerance) for CSV, XML, and MediSwitch pipe-delimited remittance advice files with database row-level locking (`select_for_update()`).
- **Collections & Commission Engine**: Calculates bureau commission fees (e.g., 2% of collections) per practice, tracks patient liability, and generates statement reminders.

## Tech Stack

- **Backend**: Python 3.12, Django 5.1
- **Task Queue**: Celery 5.4, Redis
- **Integration**: Medclaim EDI, SFTP
- **Database**: PostgreSQL / SQLite
- **Frontend**: Django Templates, Bootstrap 5, HTMX, Jazzmin

## Getting Started

### 1. Prerequisites
- Python 3.12+
- Redis (for Celery background tasks)

### 2. Installation

Clone the repository:
```bash
git clone https://github.com/bumhira27/billing-bureau.git
cd billing-bureau
```

Create and activate a virtual environment:
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Apply database migrations:
```bash
python manage.py migrate
```

Load reference data (ICD-10 codes, tariff codes, rejection codes):
```bash
python manage.py load_icd10
python manage.py load_tariff_codes
python manage.py load_rejection_codes
```

Create a superuser:
```bash
python manage.py createsuperuser
```

### 4. Running the Application

Start the development server:
```bash
python manage.py runserver
```

Start the Celery worker (in a separate terminal):
```bash
celery -A billing_bureau worker -l info
```

### 5. Running Tests

Run the complete automated test suite:
```bash
python manage.py test
```

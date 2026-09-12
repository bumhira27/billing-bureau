# South African Medical Billing Bureau Platform

An enterprise medical billing bureau management platform built for South African healthcare practices. The system handles client practice management, patient claims processing, direct medical scheme portal RPA automation, electronic remittance advice (eRA) reconciliation, and collections.

## Architecture & System Features

- **Direct Scheme Gateway Automation (Zero-Switch Cost)**: Bypasses third-party commercial switching fees by submitting claims directly through scheme provider web portals (Discovery Health, Medscheme/GEMS, Momentum/Metropolitan) using bureau master credentials and headless browser automation.
- **Gateway Circuit Breaker**: Protects bureau credentials and prevents system hang-ups during scheme maintenance windows with automated failure tracking, cooldown periods, and administrative resets.
- **Versioned REST API v1 (`/api/v1/`)**: RESTful API endpoints for claim submission and bedside ward sync with mandatory `Idempotency-Key` headers to prevent duplicate claim rejections (`06: Duplicate claim`). Returns RFC 7807 problem details on errors.
- **Offline Bedside Ward Sync**: Allows doctors rounding in hospital wards to capture consultations offline and batch-sync encounters atomically once connected to Wi-Fi.
- **eRA Reconciliation Engine**: Automated parsing and multi-pass matching (exact reference, BHF + membership, patient surname, date tolerance) for CSV, XML, and MediSwitch pipe-delimited remittance advice files with database row-level locking (`select_for_update()`).
- **Collections & Commission Engine**: Calculates bureau commission fees (e.g., 2% of collections) per practice, tracks patient liability, and generates statement reminders.

## Tech Stack

- **Backend**: Python 3.12, Django 5.1
- **Task Queue**: Celery 5.4, Redis
- **Automation**: Playwright (Headless RPA)
- **Database**: PostgreSQL / SQLite
- **Frontend**: Django Templates, Bootstrap 5, HTMX

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

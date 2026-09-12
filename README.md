# Billing Bureau: South African Medical Billing & EDI Switching Platform

Billing Bureau is an enterprise-grade revenue cycle management and medical claims processing platform tailored to the South African private healthcare system. It automates claims ingestion, pre-submission clinical rule validation, batch Medclaim EDI generation for Board of Healthcare Funders (BHF) accredited switches, multi-pass Electronic Remittance Advice (eRA) reconciliation, and patient liability collections.

The platform provides medical practices and billing bureaus with an auditable, multi-tenant system that enforces strict Protection of Personal Information Act (POPIA) data privacy standards, role-based access isolation, and multi-factor authentication.

## Architecture & System Capabilities

### 1. Direct Switch Integration (Medclaim EDI)
The system formats batches into standardized Medclaim EDI flat-file specifications for transmission to BHF-accredited switches (MediSwitch, Healthbridge). This eliminates brittle browser-based screen scraping, ensures atomic transaction guarantees, and supports direct SFTP file transport pipelines.

### 2. Pre-Submission Clinical Scrubbing Engine
Claims pass through an extensible `ClaimScrubber` rule registry before batch compilation. Scrubbing rules validate clinical and administrative criteria, including:
* Gender-to-diagnosis validation (flags male patients associated with obstetric or gynecological ICD-10 codes).
* Age-to-tariff constraints (restricts pediatric consultation codes 0101-0104 to patients under 12 years of age).
* Stale claim checks (enforces the South African statutory 120-day submission limit).

Failing claims remain in a draft state with validation errors, preventing switch rejection fees.

### 3. Electronic Remittance Advice (eRA) Multi-Pass Reconciliation
The reconciliation engine processes incoming CSV, XML, and MediSwitch pipe-delimited remittance files. It executes multi-pass matching using database row-level locking (`select_for_update`):
* Pass 1 (Exact Match): Reconciles BHF practice number, scheme membership number, dependent code, service date, and tariff code.
* Pass 2 (Fuzzy Date Match): Relaxes service date tolerance to plus or minus three calendar days for hospital encounters.
* Pass 3 (Manual Queue): Routes unallocated remittances to an interactive review interface with audit tracking.

### 4. POPIA Compliance & Deterministic Encryption
Patient Health Information (PHI) fields, including South African national identity numbers and medical scheme membership numbers, are encrypted at rest using deterministic AES-256 CBC encryption. An audit middleware (`PHIReadLoggerMiddleware`) records user access to unmasked medical records.

### 5. Multi-Tenant Role-Based Access Control & MFA
* `BureauAdmin`: Complete access to all managed practices, financial ledgers, switch transmission logs, and system configuration.
* `PracticeUser`: Scoped access strictly limited to claims, patients, and remittances assigned to their registered practice.
* Time-based One-Time Password (TOTP) MFA is enforced for administrative accounts via `django-two-factor-auth`.

### 6. Offline Bedside Ward Sync API (`/api/v1/`)
A versioned REST API facilitates offline clinical encounter capture for rounding physicians. Requests require an `Idempotency-Key` header (UUID v4) to prevent duplicate transaction creation during network reconnects, returning RFC 7807 problem details upon validation failure.

## Component & Tech Stack

| Architectural Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime & Core** | Python | 3.12.10 | Base language runtime |
| **Web Framework** | Django | 5.1.0 | Core backend, ORM, and MVC architecture |
| **Task Queue & Cache** | Celery / Redis | 5.4.0 / 5.0.8 | Asynchronous EDI batching and SFTP file ingestion |
| **Database** | PostgreSQL / SQLite | 16-alpine / 3.45 | Relational persistence with row-level locks |
| **Security & Auth** | django-two-factor-auth | 1.17.0 | RFC 6238 TOTP Multi-Factor Authentication |
| **Data Encryption** | Cryptography (Fernet) | 43.0.0 | AES-256 field-level deterministic encryption |
| **API Layer** | Django REST Framework | 5.1.0 (Native) | RESTful API v1 with RFC 7807 error structures |
| **AI Extraction** | Google GenAI SDK | 1.14.0 | Clinical note ICD-10 extraction pipeline |
| **Client Interface** | Tailwind CSS / Alpine.js | 3.4.1 / 3.14.1 | Utility-first responsive design and lightweight reactive state |
| **Dynamic Delivery** | HTMX | 2.0.1 | Partial DOM updates for live search and claim line additions |

## Environment Configuration & Quick Start

### Prerequisites
* Python 3.12 or higher
* Redis 7.0 or higher
* Git

### 1. Repository Setup
```bash
git clone https://github.com/bumhira27/billing-bureau.git
cd billing-bureau
```

### 2. Environment Isolation & Dependencies
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables
Create a local `.env` configuration file in the project root:
```ini
DJANGO_SECRET_KEY=local-dev-secret-key-replace-in-production-0987654321
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=True
GEMINI_API_KEY=your-optional-gemini-api-key
```

### 4. Database Initialization & Reference Data Seeding
```bash
python manage.py migrate
python manage.py load_icd10
python manage.py load_tariff_codes
python manage.py load_rejection_codes
python manage.py setup_roles
```

### 5. Create Administrative Account
```bash
python manage.py createsuperuser
```

### 6. Start Services
Terminal 1 (Django Development Server):
```bash
python manage.py runserver 0.0.0.0:8000
```

Terminal 2 (Celery Worker):
```bash
celery -A billing_bureau worker -l info
```

### 7. Run Test Suite
```bash
python manage.py test
```

## Core API Contracts

### Claim Ingestion Endpoint
Captures clinical encounters and patient demographics with mandatory idempotency enforcement.

`POST /api/v1/claims/`

#### Request Headers
```http
Content-Type: application/json
Authorization: Bearer <token>
Idempotency-Key: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
```

#### Request Payload
```json
{
  "practice_id": 1,
  "patient": {
    "first_name": "Sipho",
    "last_name": "Nkosi",
    "id_number": "8501015009087",
    "date_of_birth": "1985-01-01",
    "gender": "M",
    "phone": "0825551234",
    "scheme": {
      "scheme_name": "Discovery Health",
      "membership_number": "901234567",
      "dependent_code": "00"
    }
  },
  "date_of_service": "2026-09-12",
  "referring_doctor_bhf": "0140002",
  "line_items": [
    {
      "tariff_code": "0190",
      "tariff_description": "Consultation established patient",
      "icd10_primary": "J06.9",
      "quantity": 1,
      "amount_billed": "650.00"
    }
  ]
}
```

#### Success Response (201 Created)
```json
{
  "status": "success",
  "claim_id": 1042,
  "status_code": "draft",
  "scrubbing_passed": true,
  "total_billed": "650.00",
  "currency": "ZAR",
  "validation_warnings": []
}
```

#### Error Response: Clinical Scrubbing Violation (422 Unprocessable Entity)
```json
{
  "type": "https://billingbureau.co.za/errors/scrubbing-failed",
  "title": "Claim Pre-Scrubbing Validation Failed",
  "status": 422,
  "detail": "Claim violates clinical billing constraint rules.",
  "errors": [
    {
      "field": "line_items[0].icd10_primary",
      "rule": "GENDER_ICD10_MISMATCH",
      "message": "Diagnosis code O80 (Single spontaneous delivery) is invalid for biological male patients."
    }
  ]
}
```

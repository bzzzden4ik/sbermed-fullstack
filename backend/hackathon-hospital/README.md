# Appointment Booking & Clinic Management System

This is a premium, enterprise-ready backend platform built with **FastAPI** and **PostgreSQL** that enables clinics to seamlessly manage doctors, patients, appointments, prescriptions, and medical records with robust authentication, role-based authorization, and automated background tasks.

---

## Features Matrix & Role-Based Access Control (RBAC)

The system enforces strict RBAC checking at the API level:

| Feature / Action | API Endpoint | Admin | Doctor | Patient |
| :--- | :--- | :---: | :---: | :---: |
| **Manage Doctors** | `POST/PUT/DELETE /doctors` | ✅ Yes | ❌ No | ❌ No |
| **View Doctors List** | `GET /doctors` | ✅ Yes | ✅ Yes | ✅ Yes |
| **Create Patient Profile** | `POST /patients` | ✅ Yes | ❌ No | ✅ Own profile |
| **Update Patient Details**| `PUT /patients/{id}` | ✅ Yes | ❌ No | ✅ Own profile |
| **View Patient Details** | `GET /patients/{id}` | ✅ Yes | ✅ Yes | ✅ Own profile |
| **Book Appointment** | `POST /appointments` | ✅ Yes | ❌ No | ✅ For self |
| **View/Export Appointments** | `GET /appointments`, `GET /appointments/export/csv` | ✅ Yes | ✅ Own | ✅ Own |
| **Reschedule Appointment**| `PUT /appointments/{id}` | ✅ Yes | ❌ No | ✅ Own |
| **Cancel Appointment** | `PUT /appointments/{id}` (Status: Cancelled) | ✅ Yes | ❌ No | ✅ Own |
| **Complete Appointment** | `PUT /appointments/{id}` (Status: Completed) | ✅ Yes | ✅ Yes | ❌ No |
| **Create Prescriptions** | `POST /prescriptions` | ❌ No | ✅ Yes | ❌ No |
| **View Prescriptions** | `GET /prescriptions` | ✅ Yes | ✅ Own | ✅ Own |
| **Upload Medical Reports**| `POST /medical-records/upload` | ✅ Yes | ❌ No | ✅ Own |
| **View/Download Medical Reports**| `GET /medical-records/{patient_id}`, `GET /medical-records/download/{id}` | ✅ Yes | ✅ Yes | ✅ Own |
| **View Reports Dashboard**| `GET /reports/dashboard` | ✅ Yes | ❌ No | ❌ No |

### Account Registration and Admin Provisioning

Public `POST /auth/register` accepts `patient` and `doctor` roles only; attempts to register with `role: "admin"` are rejected with HTTP 422. Admin accounts must be provisioned directly in the database, and no unauthenticated API endpoint creates admin users. Doctors may register through `/auth/register`, while administrators can continue to create doctor accounts and profiles through the admin-protected `POST /doctors` endpoint.

Patients first register an account with the `patient` role, then create one patient profile through `POST /patients`. That profile is linked to the account. Patient requests may omit `patient_id` when booking appointments or uploading records; the API resolves it from the authenticated account. Patients can access and modify only their own profile and data. Existing patient profiles remain unlinked after migration; an administrator can associate one by updating it with the registered patient's `user_id` using `PUT /patients/{id}`.

---

## Technical Stack

- **Framework**: FastAPI (Asynchronous framework with standard lifespan)
- **Database**: PostgreSQL (Production) / SQLite (In-Memory for unit test speed)
- **ORM**: SQLAlchemy 2.0 (Modern type-safe declarative mapping)
- **Database Migrations**: Alembic
- **Authentication**: JWT bearer tokens & Argon2id password hashing (`argon2-cffi`)
- **Background Tasks**: FastAPI `BackgroundTasks` for appointment and prescription email notifications
- **Testing**: Pytest (With full coverage integration tests)
- **Dockerization**: Multi-stage Dockerfile and Docker Compose support

---

## Database Schema Diagram

```mermaid
erDiagram
    User {
        int id PK
        string email UK
        string password_hash
        string full_name
        string role "admin / doctor / patient"
        datetime created_at
    }
    Doctor {
        int id PK
        int user_id FK "Users"
        string specialization
        string qualification
        string phone_number
        string email UK
        float consultation_fee
        string available_timings "JSON or text list"
    }
    Patient {
        int id PK
        int user_id FK "Users, unique, nullable for admin-created or legacy profiles"
        string full_name
        int age
        string gender
        string phone_number
        string address
        string blood_group
        string emergency_contact
        datetime created_at
    }
    Appointment {
        int id PK
        string appointment_number UK
        int patient_id FK "Patients"
        int doctor_id FK "Doctors"
        date appointment_date
        string time_slot
        string reason_for_visit
        string status "Scheduled / Confirmed / Completed / Cancelled / No Show"
        datetime created_at
        datetime updated_at
    }
    Prescription {
        int id PK
        int appointment_id FK "Appointments"
        int doctor_id FK "Doctors"
        int patient_id FK "Patients"
        string diagnosis
        string medicines "JSON array"
        string dosage
        string instructions
        date follow_up_date
        datetime created_at
    }
    MedicalRecord {
        int id PK
        int patient_id FK "Patients"
        string file_name
        string file_path
        string file_type "pdf / jpg / png"
        datetime uploaded_at
    }
    AuditLog {
        int id PK
        int appointment_id FK "Appointments"
        string action "Booked / Rescheduled / Cancelled / Completed / Status Updated"
        string changed_by "role + name"
        string previous_status
        string new_status
        datetime timestamp
    }
```

---

## Core Business Logic

1. **Doctor Double-Booking Prevention**: During appointment scheduling or rescheduling (`POST /appointments`, `PUT /appointments/{id}`), the system queries for any existing appointments on the same date and time slot for the selected doctor with active status (excluding Cancelled/No Show). If a conflict exists, a `400 Bad Request` is returned.
2. **Automatic Appointment Completion**: When a doctor writes a prescription for an appointment via `POST /prescriptions`, the system automatically marks the corresponding appointment status as `Completed`.
3. **Audit Log Generation**: Every change to an appointment (creation, rescheduling, cancellation, completion) generates an entry in the `AuditLog` mapping the user's role and name who triggered the update, along with status transitions.
4. **FastAPI Background Tasks**: Sends appointment confirmations, reminders, and prescription notifications to linked patient email addresses through authenticated SMTP.

---

## Setup & Running Locally

### Prerequisites

- Python 3.10+
- PostgreSQL database service running

### 1. Clone & Setup Environment

Copy or create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg2://postgres:vinod123@localhost:5432/clinic_db
SECRET_KEY=supersecretkeyclinicmanagement12345!@#$%
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=uploads
SMTP_HOST=smtp.mail.ru
SMTP_PORT=465
SMTP_USERNAME=your-mailbox@bk.ru
SMTP_PASSWORD=your-mailbox-app-password
SMTP_FROM_EMAIL=your-mailbox@bk.ru
OPENAI_API_KEY=your-openai-api-key
MCP_SERVER_URL=http://127.0.0.1:8000/mcp
CLINIC_NAME=Название клиники
CLINIC_CITY=Казань
CLINIC_ADDRESS=Улица и номер дома
CLINIC_CONTACT_PHONE=+7 (915) 163-07-01
```

SMTP notifications use SSL on port 465; other configured ports use STARTTLS. Set these values in the ignored `.env` file or environment variables. Do not commit mail credentials; use a dedicated app password and revoke any credential that has been exposed.

### 2. Install Dependencies

Create a virtual environment and install the required modules:

```bash
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

Apply the database schema versioning:

```bash
python -m alembic upgrade head
```

### 4. Start the Application

Launch the development server:

```bash
uvicorn app.main:app --reload
```

The interactive OpenAPI / Swagger documentation will be available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## Running with Docker (Optional)

We provide a full containerized solution containing PostgreSQL and the FastAPI application.

```bash
# Build and run the services
docker-compose up --build -d
```

- The API will be available at `http://localhost:8000`
- The database port is mapped to `5433` on the host machine to avoid local service collisions.

---

## Running Tests

We use Pytest for our automated test suite. Tests are run on an in-memory SQLite database to keep executions fast, isolated, and side-effect free:

```bash
$env:PYTHONPATH="."
python -m pytest -v
```

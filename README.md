# ClassPulse

ClassPulse is a small Django classroom attendance MVP. Monitors manage every
course, promote students to CR assistants, review reports and audit history.
CRs manage their assigned courses, enroll students, create sessions, mark
attendance, show short-lived QR codes, and close sessions.

The app is intentionally simple: Django templates, Django forms, Django Unfold
for the admin UI, PostgreSQL for normal development, and Django tests.

## Requirements

- Python 3.12+
- PostgreSQL

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy the example environment file:

```bash
cp .env.example .env
```

For local development, `config.settings.development` reads `.env` automatically.
Production should provide environment variables directly and use
`config.settings.production`.

## Environment Variables

Expected local variables:

```text
SECRET_KEY=replace-with-a-secure-random-value
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=classpulse
POSTGRES_USER=classpulse
POSTGRES_PASSWORD=classpulse
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

QR_TOKEN_TTL_SECONDS=30
LATE_THRESHOLD_MINUTES=5
```

`QR_TOKEN_TTL_SECONDS` controls how quickly QR codes expire. The default is 30
seconds. `LATE_THRESHOLD_MINUTES` controls when a QR scan becomes `LATE`
instead of `PRESENT`.

## Database Setup

Create a local PostgreSQL database and user:

```sql
CREATE USER classpulse WITH PASSWORD 'classpulse';
CREATE DATABASE classpulse OWNER classpulse;
```

Apply migrations:

```bash
python manage.py migrate
```

Create an admin user if you want to use Django admin:

```bash
python manage.py createsuperuser
```

Optional sample data for trying the app locally:

```bash
python manage.py seed_sample_data
```

The sample command creates one Monitor, three students, one course, active
enrollments, and one active sample session. It can be run more than once without
duplicating the sample records.

## Run The App

Start the development server:

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Open `http://127.0.0.1:8000/admin/` for the Unfold-powered Django admin.
The admin home page includes a ClassPulse dashboard with Monitor shortcuts for
courses, sessions, QR check-in, and attendance reports.

Sample login data created by `seed_sample_data`:

```text
Monitor: sample_monitor
Students: sample_student_1, sample_student_2, sample_student_3
Password: classpulse123
```

The sample Monitor is marked as staff so they can sign in to `/admin/` and use
the Monitor dashboard. All users can sign in through `/accounts/login/`.

Roles and permissions:

```text
ADMIN    Full administrative access
MONITOR  Access to every course, reports, CR promotion, and audit history
CR       Access to assigned courses; sessions, QR, enrollment, and attendance
STUDENT  QR attendance for courses where the student is actively enrolled
```

A CR may edit ordinary students and their own attendance, but cannot edit or
remove another CR. CRs cannot open reports or the attendance audit log.

CRs also have a course-scoped Students page. They can create a Student while
assigning them to one of their courses and edit ordinary Students enrolled in
their courses. They cannot see unrelated Students, edit CR accounts, or globally
deactivate accounts. Removing course access remains available from the roster.

Monitors manage student accounts at `/accounts/students/`. They can create and
edit Students or safely deactivate/restore accounts. Deactivation also removes
active course access while preserving attendance and audit history.

Monitors and Admins generate reports from `/reports/`. The report center offers
an interactive course report, a calculated summary CSV, or a detailed raw
attendance CSV from one searchable course selector.

## Basic Usage Flow

1. Sign in as a Monitor or assigned CR.
2. As a Monitor, create student accounts from the Students page.
3. Create a course from the course workspace if needed.
4. Open a course, assign students, and create a class session.
5. Open the session detail page.
6. Mark attendance manually, or open the QR page for an active session.
7. Students sign in and scan the QR code while it is valid.
8. Close the session to mark missing section records as `ABSENT`.
9. As a Monitor, open the Reports page, choose a course and output, then
   generate the report.
10. Open the audit log when you need to review attendance changes.

Attendance is recorded per section. One session has exactly 3 sections, each
section counts as 1 attendance hour, and every 3 `LATE` records count as 1
absence equivalent in reports. `LEAVE` is tracked separately as excused absence.

## Tests

Tests use an isolated in-memory SQLite database, so they do not require a
running PostgreSQL server:

```bash
python manage.py test
```

Check for missing migrations:

```bash
python manage.py makemigrations --check --dry-run
```

## Project Structure

```text
accounts/    Roles, login/logout, CR promotion, and permission helpers
attendance/  Sessions, attendance, QR flow, audit history, and services
config/      Project settings, URLs, and deployment entry points
courses/     Courses, enrollments, session form, and sample data command
reports/     Attendance report services, views, and CSV exports
templates/   Shared Django templates
static/      Responsive ClassPulse design system
```

# ClassPulse — Codex Context

ClassPulse is a Django + PostgreSQL classroom attendance MVP using Django
templates, forms, a custom user model, Django Unfold, and QR codes.

## Roles and access

* `ADMIN`: full administrative access.
* `MONITOR`: accesses every course, manages CR promotion, can manage attendance,
  student accounts, and can view reports, exports, and audit history.
* `CR`: a promoted student. An active `Enrollment` assigns the CR to a course.
  CRs can manage sessions, QR codes, ordinary student accounts/enrollments,
  ordinary student attendance, and their own attendance only for assigned
  courses. New Students created by a CR must be assigned to one of those courses.
* `STUDENT`: can record their own QR attendance when actively enrolled.

A CR cannot view unrelated Students, edit or deactivate another CR, globally
deactivate accounts, or view reports, exports, or audit history. `Course.monitor`
records who created the course but all Monitors can access all courses.

Student deletion is implemented as safe deactivation: deactivate the user and
active enrollments, but retain the user, attendance records, and audit history.

## Attendance rules

* Every session has exactly three sections.
* Every section is 45 physical minutes and one counted attendance hour.
* Statuses: `PRESENT`, `LATE`, `ABSENT`, `LEAVE`.
* A student has at most one attendance record per section.
* Three `LATE` sections equal one absence equivalent.
* `LEAVE` is tracked separately.
* Closing an active session creates missing `ABSENT` records without overwriting
  existing records.
* QR tokens use secure randomness, expire quickly, and work only for active
  sessions and active course enrollments.

## Architecture

```text
accounts/    roles, login/logout, CR promotion, permission helpers
courses/     courses, enrollments, session creation, enrollment management
attendance/  sessions, records, QR flow, audit model, business services
reports/     calculations, report pages, CSV exports
```

Monitor/Admin report generation starts at `/reports/`, where a course and one of
three existing outputs (interactive, summary CSV, detailed CSV) are selected.

Attendance writes belong in `attendance/services.py`; reports belong in
`reports/services.py`. Views coordinate HTTP and permissions. Preserve database
constraints and transactions.

## Audit history

Successful manual, QR, system-close, and Django-admin attendance writes create
`AttendanceAuditLog` rows containing the record context, old/new status, actor,
method, note, and timestamp. Audit entries are read-only in admin and the web
audit page is Monitor/Admin-only.

## Verification

Run after meaningful changes:

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
```

Keep `PROJECT_STATE.md` current.

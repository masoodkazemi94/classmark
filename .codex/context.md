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

The `/` homepage is role-aware. Monitor/CR dashboards show operational metrics,
today/upcoming sessions, and missing attendance; Monitor also sees recent audit
activity. Students see their schedule and personal attendance. The management
calendar is at `/courses/calendar/` and must always respect CR course scope.

Students and CRs receive durable notifications at `/accounts/notifications/`.
New sessions notify the active roster, attendance service writes notify the
affected student, and course managers can send a custom class update from a
session. SMTP settings come only from environment variables. Delivery runs on
transaction commit, records sent/skipped/failed status, and must never roll back
the related class or attendance write.

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

## Production deployment

The current production deployment is at `http://84.200.192.35/` under
`/opt/classpulse`. Docker Compose runs Gunicorn/Django, PostgreSQL 16, and Nginx
with persistent named volumes. `.env.production` is root-readable only and is
not committed. The database was deployed without seed data and contains only
one Admin superuser. Native Nginx/PostgreSQL services are disabled; Docker owns
the production services. The firewall permits only SSH and HTTP. HTTPS remains
pending until a domain is available.

Pushes to `main` use `.github/workflows/deploy.yml`: tests and migration checks
must pass before an immutable release is uploaded with the dedicated `deploy`
SSH account. Secrets are scoped to the GitHub `production` environment. The
server keeps its environment file under `/opt/classpulse/shared` and releases
under `/opt/classpulse/releases`; Docker project name `classpulse` preserves the
existing volumes across releases.

# PROJECT_STATE.md — ClassPulse

Last updated: 2026-06-05

## Project status

Status: Phase 18 Unfold teacher admin dashboard complete; local PostgreSQL sample data seeded

ClassPulse is a Django + PostgreSQL attendance management MVP.

The app is intended for a teacher who wants QR-based and manual attendance tracking.

## Current stack

Actual stack:

```text
Backend: Django 5.2
Database: PostgreSQL via psycopg
Test database: SQLite in memory
Frontend: Django templates
Admin UI: Django Unfold
Authentication: Django custom user model
Environment loading: python-dotenv
QR generation: qrcode
Tests: Django test framework
```

## Current apps

Actual apps:

```text
accounts
courses
attendance
reports
```

## Current business rules

These rules are confirmed:

```text
1 class session = 3 sections
1 section = 45 physical minutes
1 section = 1 counted attendance hour
attendance is tracked per section
every 3 late records = 1 absence equivalent
leave/excused absence is counted separately
```

Attendance statuses:

```text
PRESENT
LATE
ABSENT
LEAVE
```

Session statuses:

```text
DRAFT
ACTIVE
CLOSED
```

Attendance record methods:

```text
MANUAL
QR
SYSTEM
```

## Implemented features

* Django project named `config`
* Environment-based development and production settings
* PostgreSQL database configuration
* Isolated SQLite test configuration
* Custom `accounts.User` model with ADMIN, TEACHER, and STUDENT roles
* Student code and optional phone number account fields
* Student code validation and custom user admin integration
* Course and enrollment models with role validation and database constraints
* Course and enrollment Django admin integration
* Class session and three-section structure with transactional section creation
* Session and section Django admin integration
* Attendance records with status and recorded-method choices
* Attendance enrollment and course/session/section relationship validation
* Attendance record database constraints and Django admin integration
* Attendance services for manual section/session marking, manual corrections, and
  transactional missing-record absent marking
* Teacher dashboard with course list, course detail, session creation, and
  session detail pages
* Teacher-only dashboard permissions with course and session ownership checks
* Session attendance matrix showing active enrolled students and each section's
  current attendance status
* Session-scoped manual attendance form for marking one section or all three
  sections, with optional notes and success/error messages
* POST-only manual attendance updates with CSRF protection, active enrollment
  validation, and teacher ownership checks
* Temporary attendance tokens linked to a course, session, and optional section
* Secure random attendance token generation with configurable short-lived expiry
* Attendance token validity checks for expiry, active state, and active sessions
* Teacher QR display page for active sessions
* QR refresh action that creates a new short-lived token and deactivates older
  tokens for the same session
* QR images rendered from `/attendance/scan/<token>/` URLs
* Student QR scan route with login, token, enrollment, expiry, active-session,
  and duplicate-scan checks
* QR scans record `PRESENT` or `LATE` attendance from a configurable late
  threshold without overwriting existing attendance records
* Student scan confirmation and clear invalid, inactive, expired, unauthorized,
  and closed-session error pages/messages
* Teacher session closing action for active sessions
* Transactional session closing that marks missing active-enrollment section
  records as `ABSENT` without overwriting existing attendance
* Idempotent closed-session handling so repeated close attempts do not duplicate
  attendance records
* Closed sessions continue to allow teacher manual attendance corrections while
  rejecting QR scans
* Report services that calculate present, late, absent, and leave sections from
  attendance records
* Report calculations for absence hours, late-equivalent absences, and total
  absence equivalent using integer math
* Teacher course report page showing each active student's raw section counts
  and calculated absence totals
* Per-student report detail page showing calculated totals and raw attendance
  records
* Teacher-only report permissions with course ownership checks
* Teacher course report summary CSV export with student identity, section counts,
  absence hours, late-equivalent absences, and total absence equivalent
* Teacher course detailed attendance CSV export with session, section, student,
  status, recorded method, and note fields
* CSV export response, header, permission, and calculated-value tests
* Idempotent `seed_sample_data` management command that creates one demo teacher,
  three demo students, a demo course, active enrollments, and one active sample
  session with three sections
* README documentation covering project purpose, local setup, environment
  variables, database setup, tests, sample data, and basic usage flow
* Light shared template styling for readable pages, messages, forms, tables,
  and mobile-width layouts
* Additional permission and error-message tests for QR pages, session closing,
  report exports, student report detail access, invalid session creation, and
  sample data creation
* Clear success/error messages for session creation
* Polish review found no dead project code that needed removal
* Requested Django app structure
* Basic shared templates and project home page
* Initial boot, account, course, session, section, attendance record model, and
  attendance service, teacher dashboard, manual attendance view, token, QR
  display, QR scan, session closing, and report tests
* Setup documentation and `.env.example`
* Local `.env` created for development and local PostgreSQL migrations applied
  to the `classpulse` database
* Django Unfold admin UI with ClassPulse branding, Unfold `ModelAdmin`
  integration, styled auth forms, cleaner changelists, improved filters/search,
  status badges, and registered attendance token management
* Development settings reload the local `.env` with override enabled so local
  values such as `DEBUG=True` are not masked by ambient shell variables
* Local PostgreSQL database seeded with the demo teacher, three demo students,
  one demo course, three active enrollments, and one active sample session
* Unfold admin index dashboard with role-aware teacher/global stats, quick
  access cards, recent sessions, QR shortcuts, attendance report links, course
  summaries, and students needing attendance review
* Sample data command marks the demo teacher as staff so the teacher can sign in
  to the admin dashboard without granting broad model permissions
* Persian demo flow document added at `docs/demo_flow_fa.md` with frontend URL
  list, suggested walkthrough, and screenshot checklist

## Pending feature checklist

### Phase 1 — Project foundation

* [x] Create Django project named `config`
* [x] Configure PostgreSQL
* [x] Add environment-based settings
* [x] Add `.env.example`
* [x] Add README
* [x] Add base tests

### Phase 2 — Accounts

* [x] Create custom user model
* [x] Add roles: ADMIN, TEACHER, STUDENT
* [x] Add student code field
* [x] Add admin integration
* [x] Add account tests

### Phase 3 — Courses

* [x] Create `Course` model
* [x] Create `Enrollment` model
* [x] Add teacher ownership validation
* [x] Add student enrollment validation
* [x] Add uniqueness constraints
* [x] Add course tests

### Phase 4 — Sessions and sections

* [x] Create `ClassSession`
* [x] Create `SessionSection`
* [x] Auto-create 3 sections per session
* [x] Add session statuses
* [x] Add constraints
* [x] Add tests

### Phase 5 — Attendance records

* [x] Create `AttendanceRecord`
* [x] Add statuses: PRESENT, LATE, ABSENT, LEAVE
* [x] Add recorded methods: MANUAL, QR, SYSTEM
* [x] Enforce one record per student per section
* [x] Validate enrollment
* [x] Add tests

### Phase 6 — Attendance services

* [x] Add `attendance/services.py`
* [x] Mark one student for one section
* [x] Mark one student for all 3 sections
* [x] Update existing record safely
* [x] Bulk mark missing records absent
* [x] Add service tests

### Phase 7 — Teacher UI

* [x] Course list page
* [x] Course detail page
* [x] Create session page
* [x] Session detail page
* [x] Permission checks
* [x] View tests

### Phase 8 — Manual attendance UI

* [x] Manual attendance form
* [x] Mark one section
* [x] Mark all sections
* [x] Optional note field
* [x] Messages
* [x] Tests

### Phase 9 — QR token system

* [x] Create `AttendanceToken`
* [x] Add secure token generation
* [x] Add expiry logic
* [x] Add active/inactive logic
* [x] Add token tests

### Phase 10 — Teacher QR display

* [x] Generate QR for session
* [x] Display QR code
* [x] Refresh QR token
* [x] Deactivate old tokens
* [x] Add permission tests

### Phase 11 — Student QR scan flow

* [x] Add `/attendance/scan/<token>/`
* [x] Require login
* [x] Validate enrollment
* [x] Validate token
* [x] Reject expired tokens
* [x] Reject closed sessions
* [x] Record present/late
* [x] Add tests

### Phase 12 — Session closing

* [x] Close active session
* [x] Fill missing records as ABSENT
* [x] Preserve existing records
* [x] Reject QR scans after close
* [x] Add tests

### Phase 13 — Reports

* [x] Add report services
* [x] Calculate present sections
* [x] Calculate late sections
* [x] Calculate absent sections
* [x] Calculate leave sections
* [x] Calculate absence hours
* [x] Calculate late-equivalent absences
* [x] Calculate total absence equivalent
* [x] Add tests

### Phase 14 — CSV export

* [x] Export summary report CSV
* [x] Export detailed attendance CSV
* [x] Add permission tests
* [x] Add CSV content tests

### Phase 15 — Polish

* [x] Add sample data command
* [x] Improve README
* [x] Review permissions
* [x] Improve error messages
* [x] Improve basic styling
* [x] Remove dead code
* [x] Run full test suite

## Current data model

Implemented models:

```text
User
  role: ADMIN, TEACHER, or STUDENT
  student_code: unique and required by model validation for students
  phone_number: optional

Course
  title
  code
  teacher: must have TEACHER role
  start_date
  end_date: must be on or after start_date
  is_active

Enrollment
  course
  student: must have STUDENT role
  created_at
  is_active
  unique per course/student

ClassSession
  course
  date
  start_time
  end_time: optional and after start_time when provided
  status: DRAFT, ACTIVE, or CLOSED
  unique per course/date
  creates exactly 3 sections transactionally on initial save

SessionSection
  session
  section_number: 1, 2, or 3 and unique per session
  duration_minutes: fixed at 45
  counted_hours: fixed at 1

AttendanceRecord
  student: must have an active enrollment in course
  course
  session: must belong to course
  section: must belong to session and unique per student
  status: PRESENT, LATE, ABSENT, or LEAVE
  recorded_by: optional user reference
  recorded_method: MANUAL, QR, or SYSTEM
  recorded_at
  note: optional

AttendanceToken
  course
  session: must belong to course
  section: optional and must belong to session
  token: unique secure random value
  created_at
  expires_at
  is_active
  is_expired: calculated from the timezone-aware current time
  is_valid: active, unexpired, and linked to an active session
```

## Current URLs

Implemented URLs:

```text
/
/admin/
/courses/
/courses/<course_id>/
/courses/<course_id>/sessions/create/
/attendance/sessions/<session_id>/
/attendance/sessions/<session_id>/close/
/attendance/sessions/<session_id>/manual/
/attendance/sessions/<session_id>/qr/
/attendance/scan/<token>/
/reports/courses/<course_id>/
/reports/courses/<course_id>/export.csv
/reports/courses/<course_id>/details.csv
/reports/courses/<course_id>/students/<student_id>/
```

## Current management commands

Implemented management commands:

```text
seed_sample_data
  creates one sample teacher, three sample students, one sample course, active
  enrollments, and one active sample session
  uses the password classpulse123 for sample users
  is safe to run repeatedly without creating duplicate sample records
```

Planned URLs may include:

```text
/accounts/login/
/accounts/logout/
```

## Current services

Implemented attendance services:

```text
mark_student_for_section
  validates status, active enrollment, session/course, and section/session
  creates or updates one manual attendance record

mark_student_for_session
  validates status, active enrollment, session/course, and the 3-section structure
  transactionally creates or updates all 3 manual attendance records

bulk_mark_missing_students_absent
  validates session/course and the 3-section structure
  transactionally creates SYSTEM/ABSENT records for missing active-enrollment records
  preserves all existing attendance records

close_session
  explicitly transitions ACTIVE sessions to CLOSED
  transactionally fills missing active-enrollment section records as SYSTEM/ABSENT
  preserves existing records and treats repeated close attempts as a safe no-op

change_attendance_record_manually
  validates the existing record relationships and new status
  safely changes the existing record to a manual correction

create_attendance_token
  validates course/session and optional section relationships
  deactivates existing active tokens for the same session
  creates a secure random token with settings-driven short-lived expiry

build_attendance_scan_url
  builds the student scan path for an attendance token

build_qr_code_data_url
  renders a QR PNG data URL from the scan path

create_qr_attendance_from_token
  validates token existence, active state, expiry, active session, and active
  student enrollment
  records QR attendance as PRESENT within the late threshold and LATE afterward
  records all 3 sections for session-level tokens or the selected section for
  section-level tokens
  leaves existing records unchanged so duplicate scans are safely idempotent
```

Implemented report services:

```text
calculate_attendance_totals
  calculates report formulas from per-status section counts

get_course_report
  returns each active enrolled student's section counts, absence hours,
  late-equivalent absences, and total absence equivalent

get_student_report
  returns one student's calculated totals and raw attendance records for a course

get_course_attendance_records
  returns ordered raw attendance records for detailed course CSV export
```

## Current permissions

Implemented teacher dashboard permissions:

* anonymous users are redirected to login from teacher dashboard pages
* non-teacher users receive a forbidden response from teacher dashboard pages
* teachers see only their own courses in the course list
* teachers receive a not-found response for another teacher's course, session
  creation page, or session detail page
* teachers can submit manual attendance only for their own sessions
* teachers can generate and refresh QR codes only for their own active sessions
* teachers can close only their own active sessions
* manual attendance accepts only students with an active enrollment in the
  session's course and sections belonging to that session
* anonymous users are redirected to login before QR scanning
* students can scan QR only for courses where they have an active enrollment
* invalid, expired, inactive, unauthorized, and closed-session QR scans do not
  expose private course/session details
* teachers can view reports only for their own courses
* teachers can export summary and detailed attendance CSV reports only for their
  own courses
* teacher report pages are inaccessible to students
* teacher CSV export endpoints are inaccessible to students
* anonymous users are redirected to login before CSV export endpoints
* students cannot view per-student report detail pages
* students cannot access teacher QR display pages
* session closing requires POST and does not close sessions from GET requests

Course ownership and enrollment roles remain validated at the model level.

## Configuration assumptions

Expected environment variables:

```text
SECRET_KEY
DEBUG
ALLOWED_HOSTS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
QR_TOKEN_TTL_SECONDS
LATE_THRESHOLD_MINUTES
```

Current local development note:

```text
The ignored `.env` file points `POSTGRES_HOST` to the project-local PostgreSQL
socket directory at `/home/masood/workspace/classmark/.postgres`.
The project-local PostgreSQL data directory is ignored by git.
Development settings intentionally let the local `.env` override ambient shell
variables.
```

Default business settings:

```text
QR_TOKEN_TTL_SECONDS = 30
LATE_THRESHOLD_MINUTES = 5
SESSION_SECTION_COUNT = 3
SECTION_DURATION_MINUTES = 45
SECTION_COUNTED_HOURS = 1
```

These can be changed later if the teacher wants 10 minutes instead of 5 minutes for late threshold.

## Known decisions

### Decision: Track attendance per section

Reason:

The teacher must calculate absence hours, and one session has 3 sections. Tracking per section gives accurate reports.

### Decision: Keep `LEAVE` separate

Reason:

Leave means excused absence. It should not be mixed with unexcused absence unless requirements change.

### Decision: Use short-lived QR tokens

Reason:

The teacher wants to reduce screenshot sharing between students.

Token values use secure randomness and expire after the configurable
`QR_TOKEN_TTL_SECONDS` interval, which defaults to 30 seconds.

### Decision: Keep frontend simple

Reason:

This is a DIY MVP. Django templates are enough.

### Decision: Use Django Unfold for admin UI

Reason:

The user explicitly requested Unfold. It keeps the admin inside Django's admin
surface while providing a polished UI without adding React, Vue, or a separate
frontend application.

### Decision: Keep admin dashboard actions routed through existing teacher views

Reason:

QR display, manual attendance, and reports already have teacher ownership checks.
The Unfold dashboard links to those existing views for teacher workflows instead
of duplicating attendance or reporting behavior inside admin templates.

### Decision: Filter teacher dashboard objects by ownership

Reason:

Filtering course and session lookups by the signed-in teacher prevents private
course details from being revealed and keeps permission checks explicit.

### Decision: Keep account roles on the custom user model

Reason:

The MVP needs only simple role checks and student-specific identifiers, so
separate profile tables would add unnecessary complexity.

### Decision: Create session sections during initial session save

Reason:

Creating all three fixed sections in the same database transaction keeps session
creation predictable and prevents a partially created session from persisting.

### Decision: Validate attendance relationship consistency

Reason:

Attendance records keep course, session, and section references for direct
queries, so model validation ensures the session belongs to the course, the
section belongs to the session, and the student has an active course enrollment.

### Decision: Keep attendance writes idempotent and transactional

Reason:

Manual section and session marking update an existing student/section record
instead of creating duplicates. Multi-record session marking and missing-record
absent marking run in transactions so partial attendance writes are rolled back.

### Decision: Scope manual attendance forms to the selected session

Reason:

Limiting student and section choices to the selected teacher-owned session keeps
invalid relationships out of the view while attendance services remain the final
business-rule validation layer.

## Known risks

* QR codes cannot fully prevent cheating.
* Students can still send screenshots quickly.
* Stronger anti-cheating features like GPS, Wi-Fi restriction, or device binding are outside the MVP.
* Authentication and permissions must be tested carefully.
* The custom user model exists from project start; future account fields should be
  added before dependent domain models.

## Test command

Expected command:

```bash
python manage.py test
```

Last result on 2026-06-05 using `.venv/bin/python manage.py test`:

```text
Ran 117 tests in 4.738s
OK
```

Migration check on 2026-06-05 using
`.venv/bin/python manage.py makemigrations --check --dry-run`:

```text
No changes detected
```

The migration check emitted a warning because the local PostgreSQL default
database connection was unavailable in this environment, but the command exited
successfully and detected no migration changes.

If pytest is added later:

```bash
pytest
```

## How agents should update this file

After every meaningful implementation step, update:

* `Last updated`
* `Project status`
* `Implemented features`
* `Pending feature checklist`
* `Current data model`
* `Current URLs`
* `Current services`
* `Current permissions`
* `Known decisions`
* `Known risks`

Do not mark a feature complete unless it is implemented and tested.

Do not claim tests pass unless they were actually run.

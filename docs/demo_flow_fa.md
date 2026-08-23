# راهنمای دمو ClassPulse

این متن برای ارسال به دوستت آماده شده و مسیر پیشنهادی دمو را مرحله‌به‌مرحله توضیح می‌دهد.

## اطلاعات ورود نمونه

```text
آدرس اجرا: http://127.0.0.1:8000/
ورود ادمین/مدرس: http://127.0.0.1:8000/admin/login/

Monitor username: sample_monitor
Password: classpulse123
```

دانشجوهای نمونه:

```text
sample_student_1
sample_student_2
sample_student_3
Password: classpulse123
```

نکته: در نسخه فعلی، ورود عملی برای دمو از مسیر ادمین انجام می‌شود. مدرس نمونه `is_staff=True` است و می‌تواند وارد پنل ادمین شود. برای دمو کامل اسکن QR از سمت دانشجو، بهتر است بعدا یک صفحه ورود عمومی برای دانشجو اضافه شود؛ چون دانشجوی نمونه staff نیست و نمی‌تواند از صفحه ورود ادمین وارد شود.

## لینک‌های مهم برای دمو

لینک‌های عمومی:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/login/
http://127.0.0.1:8000/admin/
```

لینک‌های مدرس:

```text
http://127.0.0.1:8000/courses/
http://127.0.0.1:8000/courses/<course_id>/
http://127.0.0.1:8000/courses/<course_id>/sessions/create/
http://127.0.0.1:8000/attendance/sessions/<session_id>/
http://127.0.0.1:8000/attendance/sessions/<session_id>/qr/
http://127.0.0.1:8000/reports/courses/<course_id>/
http://127.0.0.1:8000/reports/courses/<course_id>/export.csv
http://127.0.0.1:8000/reports/courses/<course_id>/details.csv
```

در دیتابیس تازه seed شده، معمولا مقدارها این‌ها هستند:

```text
course_id = 1
session_id = 1
```

پس لینک‌های سریع احتمالی برای دیتابیس تازه:

```text
http://127.0.0.1:8000/courses/1/
http://127.0.0.1:8000/attendance/sessions/1/
http://127.0.0.1:8000/attendance/sessions/1/qr/
http://127.0.0.1:8000/reports/courses/1/
```

لینک‌های پنل ادمین Unfold:

```text
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/admin/accounts/user/
http://127.0.0.1:8000/admin/courses/course/
http://127.0.0.1:8000/admin/courses/enrollment/
http://127.0.0.1:8000/admin/attendance/classsession/
http://127.0.0.1:8000/admin/attendance/sessionsection/
http://127.0.0.1:8000/admin/attendance/attendancerecord/
http://127.0.0.1:8000/admin/attendance/attendancetoken/
```

لینک دانشجو برای اسکن QR:

```text
http://127.0.0.1:8000/attendance/scan/<token>/
```

این لینک از داخل صفحه QR ساخته می‌شود و token کوتاه‌مدت است؛ بنابراین برای دمو باید همان لحظه از صفحه QR لینک یا کد را باز کرد.

## سناریوی پیشنهادی دمو

### 1. معرفی کوتاه

ClassPulse یک سیستم ساده حضور و غیاب کلاسی با Django است. مدرس می‌تواند درس‌ها، دانشجوها، جلسه‌ها، حضور هر بخش کلاس، QR کوتاه‌مدت و گزارش غیبت را مدیریت کند.

قانون اصلی سیستم:

```text
هر جلسه دقیقا 3 بخش دارد.
هر بخش 45 دقیقه است.
هر بخش 1 ساعت حضور حساب می‌شود.
هر 3 تا LATE برابر 1 غیبت معادل است.
LEAVE غیبت موجه است و جدا حساب می‌شود.
```

### 2. ورود به پنل ادمین

ابتدا وارد این صفحه شو:

```text
http://127.0.0.1:8000/admin/login/
```

با کاربر نمونه وارد شو:

```text
sample_monitor
classpulse123
```

بعد از ورود، صفحه داشبورد Unfold را می‌بینی. این داشبورد برای مدرس طراحی شده و دسترسی سریع به دوره‌ها، جلسه‌ها، QR و گزارش‌ها می‌دهد.

### 3. داشبورد مدرس در ادمین

در صفحه اصلی ادمین این موارد را نشان بده:

```text
Active courses
Active sessions
Enrolled students
Open QR tokens
Missing attendance
```

بعد کارت‌های Quick access را نشان بده:

```text
Monitor courses
Course workspace
Create session
Attendance report
Show QR code
Manual attendance
```

اینجا ارزش اصلی سیستم مشخص می‌شود: مدرس لازم نیست بین مدل‌های خام بگردد؛ از داشبورد مستقیم به کارهای مهم می‌رود.

### 4. صفحه دوره‌ها

از داشبورد یا مستقیم این صفحه را باز کن:

```text
http://127.0.0.1:8000/courses/
```

بعد دوره نمونه را باز کن:

```text
DEMO-101 - Sample Attendance Course
```

در صفحه جزئیات دوره می‌توانی دانشجوهای ثبت‌نام‌شده و جلسه‌های دوره را ببینی.

### 5. صفحه جلسه و ثبت دستی حضور

صفحه جلسه را باز کن:

```text
http://127.0.0.1:8000/attendance/sessions/<session_id>/
```

در این صفحه ماتریس حضور دانشجوها برای 3 بخش کلاس نمایش داده می‌شود. مدرس می‌تواند برای یک دانشجو، یک بخش یا همه بخش‌های جلسه را با یکی از وضعیت‌های زیر ثبت کند:

```text
PRESENT
LATE
ABSENT
LEAVE
```

### 6. صفحه QR

صفحه QR را باز کن:

```text
http://127.0.0.1:8000/attendance/sessions/<session_id>/qr/
```

اینجا سیستم یک QR کوتاه‌مدت برای حضور می‌سازد. نکات مهم:

```text
token امن و تصادفی است.
token خیلی سریع منقضی می‌شود.
QR فقط برای جلسه فعال کار می‌کند.
بعد از بسته شدن جلسه، QR رد می‌شود.
```

اگر دکمه refresh یا تولید مجدد QR را بزنی، token قبلی غیرفعال می‌شود.

### 7. گزارش غیبت

صفحه گزارش دوره را باز کن:

```text
http://127.0.0.1:8000/reports/courses/<course_id>/
```

در گزارش، برای هر دانشجو این موارد محاسبه می‌شود:

```text
Present sections
Late sections
Absent sections
Leave sections
Absence hours
Late equivalent absences
Total absence equivalent
```

فرمول مهم:

```text
late_equivalent_absences = late_sections // 3
total_absence_equivalent = absent_sections + late_equivalent_absences
```

### 8. خروجی CSV

دو خروجی CSV برای گزارش وجود دارد:

```text
http://127.0.0.1:8000/reports/courses/<course_id>/export.csv
http://127.0.0.1:8000/reports/courses/<course_id>/details.csv
```

اولی خلاصه گزارش هر دانشجو را می‌دهد. دومی رکوردهای خام حضور را برای بررسی دقیق‌تر خروجی می‌گیرد.

## فهرست اسکرین‌شات‌های پیشنهادی

در این محیط امکان گرفتن اسکرین‌شات واقعی مسدود شد، چون دانلود مرورگر Chromium برای Playwright توسط محدودیت ابزار رد شد. برای نسخه نهایی قابل ارسال، این اسکرین‌شات‌ها را بگیر و به همین ترتیب داخل فایل اضافه کن:

```text
01-admin-login.png
صفحه ورود ادمین Unfold

02-admin-dashboard.png
داشبورد مدرس با کارت‌های آماری و Quick access

03-course-list.png
لیست دوره‌های مدرس

04-course-detail.png
جزئیات دوره DEMO-101، دانشجوها و جلسه‌ها

05-session-detail.png
ماتریس حضور جلسه و فرم ثبت دستی

06-session-qr.png
صفحه QR کوتاه‌مدت برای حضور

07-course-report.png
گزارش غیبت و late equivalent

08-admin-attendance-records.png
لیست Attendance records داخل پنل ادمین
```

## متن کوتاه برای معرفی به دوستت

این پروژه یک MVP برای حضور و غیاب کلاسی است. مدرس می‌تواند دوره بسازد، دانشجوها را ثبت‌نام کند، جلسه سه‌بخشی ایجاد کند، حضور هر بخش را دستی یا با QR ثبت کند، جلسه را ببندد و گزارش غیبت بگیرد. QRها کوتاه‌مدت و امن هستند و گزارش‌ها late را طبق قانون هر 3 تا late برابر 1 غیبت معادل محاسبه می‌کنند. پنل ادمین با Django Unfold زیباتر شده و داشبورد مدرس دسترسی سریع به QR، جلسه‌ها و گزارش‌ها می‌دهد.

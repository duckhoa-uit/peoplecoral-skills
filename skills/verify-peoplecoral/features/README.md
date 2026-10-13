# PeopleCoral feature map

One file per user-facing feature. Smoke is employee-only. It walks Home tiles and tabs an employee account shows. Manager and HR Home is Approvals plus Chat only. A missing Time Off tile on those roles is role gating, not an app fail. Overtime, sick leave, chat, and expenses hide on policy flags. `smoke.py` records those missing tiles as `valid-empty`. Check-in and check-out are untested, not in the sweep.

| Feature | Route | Entry | Test | Status |
| --- | --- | --- | --- | --- |
| [login](login.md) | `/login` | app start | review-account-fill.sh | tested |
| [home](home.md) | `/home` | after login or `bottom-tab-home` | on_home (`Hi `) | tested |
| [time-off](time-off.md) | `/general_requests?type=timeoff_request` | `home-tile-timeOff` | smoke.py | tested |
| [remote-work](remote-work.md) | `/general_requests?type=remote_request` | `home-tile-remote` | smoke.py | tested |
| [sick-leave](sick-leave.md) | `/general_requests?type=sick_leave_request` | `home-tile-sickLeave` | smoke.py | tested |
| [overtime](overtime.md) | `/general_requests?type=overtime_request` | `home-tile-overtime` | smoke.py | tested |
| [chat](chat.md) | `/chat` | `home-tile-chat` | smoke.py | tested |
| [contact](contact.md) | `/contact` | `home-tile-contact` | smoke.py | tested |
| [expenses](expenses.md) | `/reimbursements` | `home-tile-expense` | smoke.py | tested |
| [payslips](payslips.md) | `/payslips` | `home-tile-payslips` | smoke.py | tested |
| [calendar](calendar.md) | `/attendance_history` | `bottom-tab-history` | smoke.py | tested |
| [notifications](notifications.md) | `/notifications` | `bottom-tab-notifications` | smoke.py | tested |
| [profile](profile.md) | `/profile` | `bottom-tab-profile` | smoke.py | tested |
| [approvals](approvals.md) | `/time_off_approvals` | `home-tile-timeOffApprovals` | none | untested |
| check-in / out | `/qr_scan` | `home-tile-checkIn` / `home-tile-checkOut` | none | untested |
| forgot-password | `/forgot_password` | login Forgot Password | none | untested |
| account-details | `/account_details` | SettingsSheet | none | untested |
| add-expense | `/add_expense` | expenses FAB | none | untested |
| submit time off | `/submit_timeoff` | general-requests FAB | none | untested |
| submit sick leave | `/submit_sick_leave` | general-requests FAB | none | untested |
| submit overtime | `/submit_overtime` | general-requests FAB | none | untested |
| submit remote work | `/submit_remote_work` | general-requests FAB | none | untested |
| legacy time off | `/time_off` | notification deep link | none | untested |

Login and home are preconditions. They are not `smoke.py` SWEEP rows. Sweep order is time-off, remote-work, sick-leave, overtime, chat, contact, expenses, payslips, calendar, notifications, profile.

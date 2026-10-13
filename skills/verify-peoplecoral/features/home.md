# Home dashboard

After login the employee Home greets the user and shows request, chat, contact, expense, and payslip tiles. Check In and Check Out sit at the top when built-in attendance is on. Manager and HR Home is Approvals plus Chat only.

## Sub-features

Greeting `Hi <name>!`. Employee tiles Check In, Check Out, Time Off, Remote Work, Overtime, Sick Leave, Chat, Contact, Expenses, Payslips. Manager or HR tiles Approvals and Chat. Bottom tabs Home, Calendar, Notification, Profile.

## How to get to it (user POV)

After login, or the Home tab.

## Driving it with agent-device

Preconditions. Session on the dashboard after a successful login.

- Confirm Home. Snapshot text starts with `Hi ` or contains `\nHi `. Time Off list is not Home.
- Open a tile by id. `press id=home-tile-timeOff` (also `remote`, `overtime`, `sickLeave`, `chat`, `contact`, `expense`, `payslips`). Older builds use the label. On iOS press the image node.
- Return Home. `press id=bottom-tab-home`.
- Do not press `id=home-tile-checkIn` or `id=home-tile-checkOut` in a read-only sweep. They open `/qr_scan`.
- Approvals. `press id=home-tile-timeOffApprovals` only on manager or HR.

## Proof

Greeting `Hi ` and the tiles for that role. Fail when the greeting is missing, an error banner shows, or an employee is missing a tile that the account's flags should show. Missing Time Off on manager or HR is role, not a fail.

## Charters

```
home-greeting|ios|skeptic|Logged-in Home is the Hi greeting, not a Time Off list
home-role-grid|ios|fuzzer|Manager Home shows Approvals and Chat only
```

## Gotchas

Chat unread sits in a `MergeSemantics` sibling. The label is not guaranteed to be `Chat\n2`. Prefer `id=home-tile-chat`. Payslips can sit below the fold. `scroll down --until 'label="Payslips"'`. Overtime and sick leave hide on policy flags. Chat and expenses hide when those built-ins are off. Check In and Check Out hide when `useBuiltInCheckinOut` is false.

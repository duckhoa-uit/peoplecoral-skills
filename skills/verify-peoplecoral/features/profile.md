# Profile

The Profile tab shows Personal Info and Payroll. The Settings icon opens Settings. Language, night mode, Account Details, change password, 2FA, and Log Out are writes. Leave them in a read-only sweep.

## Sub-features

Tabs Personal Info and Payroll. SettingsSheet with Account Details, Change Password, Two-factor authentication, Language, Night Mode, Log Out.

## How to get to it (user POV)

Bottom tab Profile.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `.

- Open the tab. `press id=bottom-tab-profile`. Tabs Personal Info and Payroll.
- Open Settings only if the change is the sheet. Settings icon on the AppBar (tooltip Settings). Do not change language, night mode, password, 2FA, or log out in a sweep.

## Proof

Settled screen shows `Personal Info` or `Payroll` or `Profile`. Fail when error text shows, or those tabs are missing.

## Charters

```
profile-tabs|ios|skeptic|Profile tab shows Personal Info and Payroll without opening Settings
```

## Gotchas

Older builds without the id use x = 84%, y = 94%. Prefer the id. Screenshots contain personal data. Keep them private.

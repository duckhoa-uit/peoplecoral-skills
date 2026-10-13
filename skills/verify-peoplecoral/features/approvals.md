# Approvals

Manager and HR Home shows an Approvals tile that opens the approval inbox. Employees do not have this tile. Do not approve or reject.

## Sub-features

Title Approvals. Route `/time_off_approvals`. Tabs Pending, Approved, Rejected. Search and filter. Approve and reject actions on a pending row.

## How to get to it (user POV)

Home tile Approvals on a manager or HR account.

## Driving it with agent-device

Preconditions. Logged-in manager or HR Home with `Hi `.

- Open the inbox. `press id=home-tile-timeOffApprovals`. Title Approvals. Tabs Pending, Approved, Rejected.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected.
- Do not approve or reject.

## Proof

Settled screen shows `Pending`, `Approved`, `Rejected`. An empty tab is valid. Fail when error text shows. Missing tile on an employee account is verified-unreachable, not a fail.

## Charters

```
approvals-tabs|ios|skeptic|Manager Approvals tile opens Pending Approved Rejected without acting
```

## Gotchas

Not in `smoke.py` SWEEP. Drive this file only when the account is manager or HR.

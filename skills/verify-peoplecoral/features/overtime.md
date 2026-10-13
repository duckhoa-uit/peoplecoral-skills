# Overtime

The Home Overtime tile opens the same general-requests list as Time Off, locked to overtime requests. There is no balance chart.

## Sub-features

`GeneralRequestPage` at `/general_requests?type=overtime_request`. Tabs Pending, Approved, Rejected. Plus FAB opens `/submit_overtime`. Hidden when `hasOvertimePolicy` is false.

## How to get to it (user POV)

Home tile Overtime.

## Driving it with agent-device

Preconditions. Logged-in employee Home with `Hi `. Tile present.

- Open the list. `press id=home-tile-overtime`. Title Overtime. Tabs Pending, Approved, Rejected. No balance chart.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected.
- Leave the FAB alone. Do not submit.

## Proof

Settled screen shows `Pending`, `Approved`, `Rejected`. Fail when error text shows, those tabs are missing, or a balance chart appears. Missing tile on an employee is verified-unreachable (policy), not a fail of the app.

## Charters

```
overtime-tabs|ios|skeptic|Overtime tile opens Pending Approved Rejected with no balance chart
```

## Gotchas

Shares `GeneralRequestPage` with the other request tiles. The query is `overtime_request`. Smoke records a missing overtime tile as `valid-empty`.

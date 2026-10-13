# Sick Leave

The Home Sick Leave tile opens the same general-requests list as Time Off, locked to sick-leave requests. There is no balance chart.

## Sub-features

`GeneralRequestPage` at `/general_requests?type=sick_leave_request`. Tabs Pending, Approved, Rejected. Plus FAB opens `/submit_sick_leave`. Hidden when `hasSickLeavePolicy` is false.

## How to get to it (user POV)

Home tile Sick Leave.

## Driving it with agent-device

Preconditions. Logged-in employee Home with `Hi `. Tile present.

- Open the list. `press id=home-tile-sickLeave`. Title Sick Leave. Tabs Pending, Approved, Rejected. No balance chart.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected.
- Leave the FAB alone. Do not submit.

## Proof

Settled screen shows `Pending`, `Approved`, `Rejected`. Fail when error text shows, those tabs are missing, or a balance chart appears. Missing tile on an employee with no sick-leave policy is verified-unreachable, not a fail.

## Charters

```
sick-leave-tabs|ios|skeptic|Sick Leave tile opens Pending Approved Rejected with no balance chart
```

## Gotchas

Shares `GeneralRequestPage` with the other request tiles. The query is `sick_leave_request`, not `sick_leave`. Smoke treats a missing tile as blocked, so skip sick-leave on accounts without the policy.

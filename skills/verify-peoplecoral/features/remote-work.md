# Remote Work

The Home Remote Work tile opens the same general-requests list as Time Off, locked to remote requests. There is no balance chart.

## Sub-features

`GeneralRequestPage` at `/general_requests?type=remote_request`. Tabs Pending, Approved, Rejected. Plus FAB opens `/submit_remote_work`.

## How to get to it (user POV)

Home tile Remote Work.

## Driving it with agent-device

Preconditions. Logged-in employee Home with `Hi `.

- Open the list. `press id=home-tile-remote`. Title Remote Work. Tabs Pending, Approved, Rejected. No balance chart.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected.
- Leave the FAB alone. Do not submit.

## Proof

Settled screen shows `Pending`, `Approved`, `Rejected`. Fail when error text shows, those tabs are missing, or a balance chart appears.

## Charters

```
remote-work-tabs|ios|skeptic|Remote Work tile opens Pending Approved Rejected with no balance chart
```

## Gotchas

Shares `GeneralRequestPage` with Time Off, Sick Leave, and Overtime. The query is `remote_request`.

# Time Off

The Home Time Off tile opens the general-requests list for time-off requests. A notification deep link can still open the legacy Time Off page. The two screens share a title and must not be blended.

## Sub-features

Home path. `GeneralRequestPage` at `/general_requests?type=timeoff_request`. Tabs Pending, Approved, Rejected. No balance chart. Plus FAB opens `/submit_timeoff`.

Legacy path. `TimeOffPage` at `/time_off`. Tabs Pending, Planned, History. Balance chart under the list.

## How to get to it (user POV)

Home tile Time Off. Or a time-off notification whose path is `/time_off`.

## Driving it with agent-device

Preconditions. Logged-in employee Home with `Hi `.

- Open the Home list. `press id=home-tile-timeOff`. Title Time Off. Tabs Pending, Approved, Rejected. No balance chart.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected. List may be empty.
- Leave the FAB alone. It opens the submit form. Do not submit.
- Legacy deep link only when the change is `/time_off`. Title Time Off. Tabs Pending, Planned, History. A balance chart is present.

## Proof

Home tile screen. `Pending`, `Approved`, `Rejected` on the snapshot. Fail when error text shows, those tabs are missing, or a Planned / History / balance-chart layout appears on this path.

Legacy screen. `Pending`, `Planned`, `History` plus a chart. Fail when that path opens the general-requests tabs instead.

## Charters

```
time-off-tabs|ios|skeptic|Home Time Off tile shows Pending Approved Rejected and no balance chart
legacy-time-off|ios|fuzzer|Notification path /time_off opens Planned History plus a balance chart
```

## Gotchas

Both pages title themselves Time Off. Judge by tabs and chart, not the title. Lists on the Home path are general requests locked to `timeoff_request`.

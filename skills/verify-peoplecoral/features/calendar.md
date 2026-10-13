# Calendar

The Calendar tab shows a week of attendance history titled Calendar. Workday chips and day rows sit under the week range.

## Sub-features

Title Calendar. Week range with previous and next arrows. Day chips. Attendance history rows for the selected day.

## How to get to it (user POV)

Bottom tab Calendar.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `.

- Open the tab. `press id=bottom-tab-history`. Title Calendar.
- Stay on the current week in a read-only sweep.

## Proof

Settled screen shows `Calendar`. Fail when error text shows.

## Charters

```
calendar-title|ios|skeptic|History tab opens a screen titled Calendar
```

## Gotchas

The tab enum and id are `history`. The screen title is Calendar. Older builds without the id use x = 37%, y = 94%. Prefer the id.

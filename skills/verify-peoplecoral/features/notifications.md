# Notification

The Notification tab shows the inbox titled Notification. Opening the list does not mark rows read. Tapping one unread row marks that row. Mark all is an AppBar write.

## Sub-features

Title Notification. Unread row tint. AppBar mark-all button (tooltip Mask All As Read). Optional tabs Check In, Check Out, Other when `useBuiltInCheckinOut` is true. Without that flag only the Other list shows.

## How to get to it (user POV)

Bottom tab Notification.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `.

- Open the tab. `press id=bottom-tab-notifications`. Title Notification. Unread rows stay unread until tapped.
- Tap one unread row only if the change needs a read-state check. That marks that row.
- Leave the AppBar mark-all button alone in a read-only sweep.

## Proof

Settled screen shows `Notification`. An empty list is valid. Fail when error text shows, or opening the tab clears every unread mark without a tap.

## Charters

```
notifications-open|ios|skeptic|Opening Notification does not mark rows read
```

## Gotchas

Older builds without the id use x = 61%, y = 94%. Prefer the id. Attendance-off accounts have no Check In or Check Out tabs.

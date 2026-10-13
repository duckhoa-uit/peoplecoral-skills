# Payslips

The Home Payslips tile opens a yearly payslip list titled Payslips. Year chips change the list. Do not download.

## Sub-features

Title Payslips. Year chips. Sort. Monthly rows. Preview sheet. Download is a write.

## How to get to it (user POV)

Home tile Payslips. Scroll down if the tile is below the fold.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `.

- Reveal the tile if needed. `scroll down --until 'label="Payslips"'`.
- Open the list. `press id=home-tile-payslips`. Title Payslips.
- Leave download and preview actions alone in a sweep.

## Proof

Settled screen shows `Payslip` (title Payslips). No payslips for the year is valid. Fail when error text shows.

## Charters

```
payslips-list|ios|skeptic|Payslips tile opens a list titled Payslips without downloading
```

## Gotchas

The tile often sits below Check In, request tiles, Chat, Contact, and Expenses.

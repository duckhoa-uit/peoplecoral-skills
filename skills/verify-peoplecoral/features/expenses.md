# Expenses

The Home Expenses tile opens Expense Reimbursement. Status tabs and a date filter change the list. Do not submit a new expense.

## Sub-features

Title Expense Reimbursement. Tabs Pending, Approved, Rejected. Search. Filter sheet with Today, This Week, Reset All. Plus FAB opens `/add_expense`. Hidden when `useBuiltInExpense` is false.

## How to get to it (user POV)

Home tile Expenses.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `. Tile present.

- Open the list. `press id=home-tile-expense`. Title Expense Reimbursement. Tabs Pending, Approved, Rejected.
- Switch a tab. `press label=Approved` or `label=Rejected`. That tab stays selected.
- Open the filter only if the change needs it. Today, This Week, Reset All. Do not submit an expense.

## Proof

Settled screen shows `Expense Reimbursement`. An empty list is valid. Fail when error text shows.

## Charters

```
expenses-tabs|ios|skeptic|Expenses opens Expense Reimbursement with Pending Approved Rejected
```

## Gotchas

FAB is a write path. Leave it in a read-only sweep.

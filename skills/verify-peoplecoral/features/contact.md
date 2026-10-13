# Contact

The Home Contact tile opens a directory titled Contact. Function contacts sit under Your Contacts. Company rows sit under Contact Info.

## Sub-features

App bar Contact. Section Your Contacts. Section Contact Info. Call, email, and message actions on a row.

## How to get to it (user POV)

Home tile Contact.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `.

- Open the screen. `press id=home-tile-contact`. Title Contact.
- Confirm sections that exist. Your Contacts only when function contacts are present. Contact Info only when company contacts are present.
- Do not press call, email, or message actions.

## Proof

Settled screen shows `Contact`. `Your Contacts` when function contacts exist. Fail when error text shows. An empty directory is valid.

## Charters

```
contact-sections|ios|skeptic|Contact title stays Contact, with Your Contacts for function rows
```

## Gotchas

Smoke accepts `Contact` or `Your Contacts`. A company-only directory still titles itself Contact.

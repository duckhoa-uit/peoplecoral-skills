# Login and first launch

A signed-out launch shows username or email, password, Log In, and Forgot Password. A 2FA challenge replaces the form when the account requires it.

## Sub-features

Username or email field. Password field. Log In. Forgot Password. Language picker. 2FA prompt when the account has it.

## How to get to it (user POV)

App start without a session. A fresh install waits up to 5s for Remote Config, then falls back to the bundled `.env` backend.

## Driving it with agent-device

Preconditions. App in front on the login screen (`Log In` or `Username or email`). Fields have no `Semantics.identifier`.

- Review account. `$HOME/.agents/skills/peoplecoral-release/scripts/review-account-fill.sh --version-id <id> --platform ios|android --session <s> [--udid|--serial] --submit`.
- Other accounts. The user types them. Never pass credentials to agent-device.
- Wait for Home. Greeting `Hi `.

## Proof

Settled Home with `Hi `. Fail when the unrecognized-username banner stays up, or Home never appears. Do not treat a first-launch banner as a wrong password until a second launch on the Remote Config backend.

## Charters

```
login-review-fill|ios|skeptic|Review fill reaches Home with a Hi greeting
login-banner|ios|fuzzer|Any login error shows the unrecognized-username banner
```

## Gotchas

The error banner is always `We don't recognize your username or email`. First-launch only on that string means the account is missing on the fallback backend. Relaunch once to confirm. The review account lives on the production or Remote Config backend. iOS simulator first launch after a host reboot can stay white for a minute.

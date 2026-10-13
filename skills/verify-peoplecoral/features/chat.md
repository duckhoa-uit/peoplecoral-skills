# Chat

The Home Chat tile opens the conversation list titled Chat with a Search field. Opening a row marks that conversation read. Never send.

## Sub-features

Conversation list. Search hint Search. Conversation detail. Hidden when `useBuiltInChat` is false.

## How to get to it (user POV)

Home tile Chat.

## Driving it with agent-device

Preconditions. Logged-in Home with `Hi `. Tile present.

- Open the list. `press id=home-tile-chat`. Title Chat. Search field visible. Do not expect Messages.
- Open one conversation only if a row exists. That marks it read. Never send.

## Proof

Settled list shows `Chat` and `Search`. An empty list is valid. Fail when an error banner or endless spinner stays up, or the screen is titled Messages.

## Charters

```
chat-list|ios|skeptic|Chat tile shows title Chat and a Search field, not Messages
```

## Gotchas

Opening a conversation is a small write on shared data. Mention it. Chat text can contain the word "failed". Judge by the UI, not a regex alone. Prefer `id=home-tile-chat` over a `Chat\n2` label.

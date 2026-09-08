# Telegram notifications

A sweep that runs overnight should tell you how it went — and if the
measurement computer dies at 2 a.m., something should tell you *that*, which
is the one thing a notifier running on that computer can never do.

Unisweep offers two ways to be told. The first is the default and is what
this document is about.

| | **Unisweep bot** (default) | **My own bot** |
|---|---|---|
| set-up | send a six-digit code to the bot | paste a @BotFather token and your chat id |
| needs | the group's bot service | nothing |
| tells you | sweep end (with a plot), errors, guard trips, the rig going silent, optional progress | sweep end, optionally errors |
| you can ask it for | status, the data table, statistics, a line plot, a 2-D map | — |
| several people | yes, each with their own settings | no |
| remote pause / stop | optional, off by default | no |

---

## Setting it up (the default)

On the measurement computer, **Settings → Notifications**:

1. Leave **Unisweep bot** selected and tick **Report this setup to the
   Unisweep bot**.
2. Give the setup a name — it is what everyone sees in Telegram.
3. Press **Generate code**.
4. Open the bot (the **Open** button, or **Copy link**) and send it the six
   digits.

Your Telegram account appears in **Linked Telegram users** and the bot
writes to you from then on. Anyone else in the group does the same with
their own code; each person's notification choices are their own.

Nothing else is configured here. What you are told about, and everything
you can ask for, lives in the chat:

```
/menu      everything, with buttons
/status    state, progress, ETA, the latest readings
/table     the tail of the data table
/plot      a parameter against the fast axis, as a picture
/map       a parameter over the 2-D grid, as a picture
/stats     min / max / mean per parameter
/notify    choose what I am told about
/control   pause / stop  (only if this setup allows it)
/unlink    stop receiving anything from this setup
```

### Removing somebody

Select them in **Linked Telegram users** and press **Remove**. The bot stops
sending them anything about this setup at once and tells them so. They can
come back with a new code; there is no way for anyone to add themselves.

### Why a code rather than a chat id

A Telegram chat id is permanent and known to anyone you have ever messaged,
so a field that accepts one is a field where somebody can sign *you* up. A
pairing code expires in ten minutes, can be spent once, and is replaced
whenever a new one is generated — the only person who can use it is
somebody standing in front of the screen that produced it.

---

## What gets sent, and what does not

While reporting is on, Unisweep sends the service, every fifteen seconds
during a sweep (once a minute when idle):

* what the sweep is doing — state, progress, ETA, the axis instructions;
* the latest measured row;
* about once a minute, a **decimated copy** of what the live plots are
  showing: the current fast-axis walk (≤ 800 points), the map matrices
  (≤ 160 × 160 per read), the last fifteen rows of the table, and
  per-parameter statistics.

Plots are drawn on the server from that copy, which is why asking for a
different parameter is instant and costs the measurement computer nothing.

Not sent: your data files, the raw full-resolution data, instrument
addresses, or anything at all when reporting is switched off. Nothing is
delivered to anyone who is not in the linked list.

### Remote control

**Allow pause / stop / ramp-to-zero from Telegram** is off by default. With
it on, a linked person can do exactly three things, after a confirmation
tap: pause/resume, stop, or stop and ramp to zero — the same buttons as the
Sweep page. The bot can never set a value, change a sweep, or start one,
and every action is reported back to whoever pressed it.

---

## When things go wrong

**"nobody linked yet — press Generate code"** — the setup is reporting but
no one has used a code yet.

**"problem: …"** in the status line — the service could not be reached.
Unisweep keeps retrying with a growing delay and nothing is lost:
notifications stay queued until they get through, and each carries a
sequence number so a retry after a timeout cannot produce a duplicate
message.

**The bot says a setup "went silent"** — it was sweeping and stopped
reporting for four minutes. Usually the computer slept, lost its network,
or crashed. Quitting Unisweep normally does *not* trigger this: it sends a
final heartbeat on the way out.

**"This lab has no bot address configured yet"** — nobody has deployed the
service, or this machine has not been pointed at it. See
[`server/README.md`](../server/README.md); the address goes in *Service
address* at the bottom of the notifications card.

---

## For the person who runs the service

The bot itself is in [`server/`](../server) and deploys to Railway with a
Postgres database. It is one bot for the whole group; each measurement
computer registers itself the first time it reports, with a token it
generates locally. The database password never leaves the server, and
nothing ever connects *into* the lab network — commands travel back as the
reply to the rig's own outbound heartbeat.

The lab-side half is `unisweep/core/telegram_link.py`: one daemon thread
that can neither block a measurement (the GUI's event pump only appends to
a queue) nor lose a notification (they stay queued until a push succeeds).

# Telegram notifications

A sweep that runs overnight should tell you how it went — and if the
measurement computer dies at 2 a.m., something should tell you *that*, which
is the one thing a notifier running on that computer can never do.

There is one bot for the whole group, running on the group's own server, and
every Unisweep installation is built already knowing where it is. Nothing to
install, no address to type, no token to paste.

---

## Connecting yourself to a setup

On the measurement computer, **Settings → Telegram notifications**:

1. Press **Generate code**.
2. Open the bot (the **Open** button, or **Copy link** and paste it into
   Telegram) and send it the six digits.

That is the whole sign-up. Your Telegram account appears in **Linked
Telegram users**, and the bot writes to you from then on. Anyone else does
the same with their own code; each person's notification choices are their
own.

One person can be linked to as many setups as they like — `/setups` switches
between them, and every question (`/status`, `/line`, …) answers about
whichever one is selected.

**The setup's name must be unique across the lab.** It is how people tell
setups apart in the chat, so a second "ATTODRY" is refused and the Settings
page says so; give it a different name and try again.

Everything else lives in the chat. Commands do the asking:

```
/status    how the sweep is going, and the latest numbers
/line      line scan of one parameter
/map       2-D map of one parameter
/stats     smallest, largest, average
/setups    your setups, and which one it answers about
/alerts    what it messages you about
/unlink    stop messages from this setup
/help      the list above
```

None of them needs an argument. Buttons do the picking: `/line` draws
whatever you looked at last and lists the other parameters underneath —
tap one and the picture is swapped in place rather than piling up a new
message. `/alerts` does the same for the switches: each one is a button
that flips between 🔔 and 🔕.

Anything a button does can also be typed, which matters because a keyboard
more than two days old can no longer be edited and Telegram's search does
not find buttons. `/line lockin.y`, `/line curr` or `/line 2` picks a
parameter — any case, part of the name, or its position in the list.
`/alerts errors off` flips a switch and `/alerts progress 30` asks for an
update every half hour.

What there is *not* is a keyboard standing in for a command: no menu, no
navigation, no "back to the main screen". Notifications the bot sends you
carry no buttons at all — nobody taps a three-day-old "sweep finished".

With remote control allowed there is also `/pause`, `/resume`, `/stop` and
`/zero`. Stopping asks twice: send the same command again within a minute.

### Unbinding, from either side

* **In Unisweep** — select the person in **Linked Telegram users** and press
  **Remove**. The bot stops sending them anything about this setup at once
  and tells them so.
* **In Telegram** — `/unlink`, twice.

Either way the database is what changes, so both sides agree immediately.
The list in Unisweep refreshes on every heartbeat; **Update info** asks
right now, for when you have just added or removed somebody.

Nobody can add themselves: the only way in is a code that a setup's own
screen produced.

### Why a code rather than a chat id

A Telegram chat id is permanent and known to anyone you have ever messaged,
so a field that accepts one is a field where somebody can sign *you* up. A
pairing code expires in ten minutes, can be spent once, and is replaced
whenever a new one is generated — the only person who can use it is somebody
standing in front of the screen that produced it.

---

## What gets sent, and what does not

From launch, Unisweep reports to the service every fifteen seconds during a
sweep (once a minute when idle):

* what the sweep is doing — state, progress, ETA, the axis instructions;
* the latest measured row;
* about once a minute, a **decimated copy** of what the live plots are
  showing: the current fast-axis walk (≤ 800 points), the map matrices
  (≤ 160 × 160 per read), and per-parameter statistics.

Plots are drawn on the server from that copy, which is why asking for a
different parameter is instant and costs the measurement computer nothing.
They come back at about 15 kB — sized for a phone and palette-reduced —
so asking for one costs you nothing either.

The sweep-ended message is **text**. A picture is thousands of times the
bytes of the sentence you actually read, so it is not attached by default;
`/alerts picture on` turns it on for anyone who wants one every time, and
`/line` or `/map` is always one message away.

Not sent: your data files, the raw full-resolution data, or instrument
addresses. And nothing is *delivered* to anybody until they hold a code —
an unpaired setup reports into a database that no one is reading.

### Addresses and links

The service address is compiled into
`unisweep/core/telegram_link.py` (`DEFAULT_SERVICE_URL`). That is safe and
deliberate: it is a public HTTPS endpoint, like a website address, and
nothing behind it opens without a rig token that the lab machine generated
for itself. The two real secrets — the Telegram bot token and the database
password — live only in the server's environment variables and never reach a
lab computer.

The bot's own `@name` is **not** compiled in. The service asks Telegram for
it at start-up and returns it on every heartbeat, so renaming the bot can
never leave a stale link in the software.

Running your own copy: set `UNISWEEP_BOT_URL` in the environment, or
`tg_service_url` in `config/settings.json`. Both override the built-in
address; neither is needed in normal use.

### Remote control

**Allow pause / stop / ramp-to-zero from Telegram** is off by default. With
it on, a linked person can do exactly three things: pause/resume, stop, or
stop and ramp to zero — the same buttons as the Sweep page. Stopping asks
twice. The bot can never set a value, change a sweep, or start one, and
every action is reported back to whoever pressed it.

---

## When things go wrong

**"nobody linked yet — press Generate code"** — the setup is reporting and
nobody has used a code yet.

**"another setup is already called X"** — the name is taken. Change it in
**This setup is called** and it re-registers on its own.

**"problem: …"** — the service could not be reached. Unisweep keeps retrying
with a growing delay and nothing is lost: notifications stay queued until
they get through, and each carries a sequence number so a retry after a
timeout cannot produce a duplicate message.

**"Sweep ended — last update 4 m ago"** — the setup was sweeping and stopped
reporting. Closing Unisweep ends the measurement, so that is what it says;
the timestamp is there for the times it was really a sleeping laptop or a
dropped network. Quitting Unisweep normally sends a proper sweep-ended
message on the way out and never reaches this path.

---

## For the person who runs the service

The bot is in [`server/`](../server) and deploys to Railway with a Postgres
database — see [`server/README.md`](../server/README.md). Each measurement
computer registers itself the first time it reports, with a token it
generates locally. Nothing ever connects *into* the lab network: commands
and the list of linked people travel back as the reply to the setup's own
outbound heartbeat.

The lab-side half is `unisweep/core/telegram_link.py`: one daemon thread
that can neither block a measurement (the GUI's event pump only appends to a
queue) nor lose a notification (they stay queued until a push succeeds).

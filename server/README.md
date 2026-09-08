# Unisweep measurement bot

The always-on half of Unisweep's Telegram notifications: one bot, shared by
the whole group, running on your own Railway service next to a Postgres
database. Measurement computers push to it over HTTPS; people talk to it in
Telegram.

It exists as a separate service for one reason: **the failure you most want
to hear about is the measurement computer going quiet**, and a notifier
living inside Unisweep cannot report that Unisweep has died. This one
notices and says so.

---

## What it does

| In Telegram | |
|---|---|
| `/status` | state, progress, the latest readings |
| `/data` | the most recent measured rows |
| `/line` | one parameter against the **fast (innermost) axis**, as a PNG |
| `/map` | one parameter over the 2-D grid, as a PNG |
| `/stats` | min / max / mean / last per parameter |
| `/setups` | list the setups this chat holds codes for, and switch |
| `/alerts` | which events to receive, per person, per setup |
| `/pause` `/resume` `/stop` `/zero` | only if the setup allows it; stopping asks twice |
| `/unlink`, `/help`, `/id` | |

No inline keyboards anywhere, and no `/link`: six digits *is* a pairing
code, so the plain-text handler takes it. The older command names
(`/table`, `/plot`, `/rigs`, `/notify`, `/menu`) still work as aliases.

Unprompted, it writes when a sweep **finishes or is stopped**, when an
**error or a guard** stops one, and when a setup that was sweeping **stops
reporting**. All of those are text. Every one is a per-person toggle; the
noisy ones (sweep started, each new file, progress pings) are off by
default, and so is attaching a plot to the sweep-ended message — the
sentence is what you read at 3 a.m., and `/plot` is a tap away when you
want the picture.

Plots are drawn here, from a decimated copy of the data the setup pushes,
so asking for a different parameter costs the measurement computer
nothing. They are sized for a phone (about 800 px) and re-encoded down to
a reduced palette, which puts a line plot or a heat map at roughly 15 kB
instead of 70.

---

## Deploying on Railway

1. **Create a Postgres service** in your Railway project. Nothing to
   configure; the schema is created on first start.

2. **Create a bot** with [@BotFather](https://t.me/BotFather) and keep the
   token.

3. **Add a service from this repository** and set its **Root Directory** to
   `server`. Railway then finds `requirements.txt` and `railway.json` here
   and starts `python -m unisweep_bot.main`.

4. **Variables** (Settings → Variables):

   ```
   TELEGRAM_BOT_TOKEN = 123456:ABC...        from @BotFather
   DATABASE_URL       = ${{Postgres.DATABASE_URL}}
   PUBLIC_URL         = https://<your service>.up.railway.app
   TZ_NAME            = Asia/Singapore
   ```

   `PORT` is injected by Railway. Everything else has a default — see
   `.env.example`.

5. **Generate a domain** (Settings → Networking → Generate Domain). That
   URL is what the lab computers talk to, and it is what goes into
   Unisweep's Settings page.

6. **Point Unisweep at it.** In `unisweep/core/telegram_link.py` set

   ```python
   DEFAULT_SERVICE_URL = "https://<your service>.up.railway.app"
   ```

   That one line is what makes every installation in the group work out of
   the box — there is no address field in the software. Committing it is
   safe and intended: it is a public HTTPS endpoint, and nothing behind it
   opens without a rig token that each lab machine generated for itself.
   The two real secrets stay in Railway's variables. For a private copy,
   `UNISWEEP_BOT_URL` in the environment overrides it.

Health check: `GET /healthz` returns `{"ok": true, ...}` and is what
Railway watches.

### If every request comes back 502

A 502 in a few milliseconds is Railway's router failing to reach the
container — the app is fine, the port is wrong. The start-up log says
which port it bound:

```
ingest API listening on 0.0.0.0:8080
```

Make Railway's domain point at that number: **Settings → Networking →**
the domain **→ target port**. Setting a `PORT` variable and redeploying
works too — the service binds whatever `PORT` says, and falls back to 8080.

### Cost and scale

One Railway instance and a small Postgres handle a group's worth of rigs
comfortably. A rig sends about 2 KB every 15 s while sweeping (a minute
apart when idle) and a decimated data snapshot — tens of KB — about once a
minute. Snapshots are one row per rig, overwritten in place, so storage
does not grow with the length of a measurement.

---

## How a person signs up

There is no chat id to look up and nothing to type on the lab computer:

1. In Unisweep: **Settings → Notifications → Generate code**.
2. Send the six digits to the bot.

Setup names must be unique across the service — they are how people tell
setups apart in the chat — so a second setup calling itself "ATTODRY" is
refused with `409 name_taken` and the Settings page explains it. One
person may be linked to any number of setups and switches between them
with `/rigs`.

The code is valid for ten minutes, can be spent once, and is replaced
whenever a new one is generated. That is the whole authentication —
possession of a code that the rig's own screen just showed. Wrong codes
are rate-limited per chat, so the 900 000 possibilities cannot be searched.

To cut somebody off, select them in the Settings page's list of linked
users and press **Remove**: they stop receiving anything about that setup
immediately and are told it happened. `/unlink` in the chat does the same
from their side.

---

## Architecture

```
 lab computer                       Railway                     Telegram
 ┌──────────────┐   HTTPS out    ┌──────────────┐            ┌──────────┐
 │  Unisweep    │ ─────────────► │  ingest API  │            │          │
 │              │   heartbeat    │      │       │            │  people  │
 │ telegram_    │   + events     │      ▼       │            │          │
 │   link.py    │   + snapshot   │  Postgres    │            └────┬─────┘
 │              │ ◄───────────── │      ▲       │                 │
 └──────────────┘   commands,    │      │       │  getUpdates     │
                    roster       │  bot polling │ ◄───────────────┘
                                 └──────────────┘
```

Nothing connects *into* the lab. Commands (pause / stop / "send fresh
data") ride back as the reply to the rig's own heartbeat, so the
measurement network needs no inbound rule and no port forwarding, and the
database password never leaves this service — a lab machine holds only its
own rig token.

### Modules

| file | what it is |
|---|---|
| `config.py` | environment only; a missing token or DSN is a fatal start-up error, never a silent default |
| `db.py` | every query. A failure returns `None`, an empty result returns an empty container — see below |
| `ingest.py` | the five rig-facing endpoints |
| `handlers.py` | commands, buttons, pairing |
| `dispatch.py` | the three background jobs |
| `render.py` | the figures |
| `formatting.py` | the text people read; every timestamp in the lab's zone |
| `main.py` | lifecycle: `run_polling` plus the HTTP listener on the same loop |

### The practices this is built on

Carried over from the booking-monitor bot, because each one is a bug that
was actually paid for:

* **A database error is not "nobody is subscribed."** Every reader returns
  `None` on failure and an empty container on an empty result. Conflating
  them is what turns a thirty-second blip into monitoring that is silently
  off for good.
* **Jobs are scheduled once, in `post_init`** — never from a command
  handler — so monitoring survives every restart and redeploy and no
  duplicate job can stack up. Each job has a name and decides for itself
  whether there is work.
* **Unlink actually `DELETE`s.** A row merely flagged inactive comes back
  to life on the next restart.
* **One row per write.** No whole-table saves, so two people editing their
  own settings cannot lose each other's update.
* **Notifications are de-duplicated by key.** The rig numbers its events;
  a push retried after a timeout inserts nothing the second time.
* **`Forbidden` removes the user.** Somebody who blocked the bot stops
  being work, forever.
* **`RetryAfter` is respected** and long messages are split below
  Telegram's 4096-character limit.
* **Every date and time is computed in `TZ_NAME`**, not in the container's
  UTC.
* **A global error handler**, and callbacks that survive `None` messages,
  double taps ("message is not modified") and keyboards older than 48 h.
* **`run_polling` owns the lifecycle** — including shutdown, so a restart
  never leaves a second poller fighting the first for `getUpdates`.
* **No credential in source.** Both secrets come from the environment.

Two more the measurement case needed:

* **A bad snapshot is never diffed against.** If a rig cannot be reached
  or sends nothing parsable, the previous state stands rather than
  generating a wave of false notifications.
* **The rig can go quiet.** The watchdog stamps `silent_since` in the same
  statement that selects, so a silence is announced exactly once however
  often the job runs.

---

## Local development

```bash
cd server
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=... DATABASE_URL=postgresql://localhost/unisweep
python -m unisweep_bot.main
```

Then point a Unisweep instance at `http://localhost:8080` in its Settings
page. Only one process may poll a given bot token at a time — stop the
deployed one, or use a second test bot.

The tests that do not need Postgres or a token live in the repository root:

```bash
python tests/test_telegram_service.py
python tests/test_telegram_link.py
xvfb-run -a python tests/gui_smoke_telegram.py
```

"""Unisweep measurement bot — the always-on half of Unisweep's Telegram
notifications.

Deployed on Railway next to a Postgres database.  Measurement computers
push to it over HTTPS; people talk to it in Telegram.  Nothing in this
package holds a credential: the bot token and the database URL arrive
through the environment.
"""

__version__ = "1.0.0"

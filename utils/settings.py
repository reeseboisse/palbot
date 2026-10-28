"""
Server-specific settings that used to be hardcoded in the cogs.

Each can be set in config/config.py. The defaults are the original hardcoded
values, so a config without these keys behaves exactly as before.
"""

DEFAULTS = {
    # The guild where the sports and Gemini channel restrictions apply
    "home_guild_id": 124572142485504002,
    # Sports channel: exempt from the global sports cooldown in the home guild
    "sports_channel_id": 1243723119567310858,
    # Gemini !chat channels; the first is the one users are pointed to
    "gemini_chat_channels": [985728639981211728, 1333677981322969149, 1337293879153791036],
    # The user who gets boiled beef from !brak
    "brak_beef_user_id": 167670602507747328,
}


def setting(bot, name):
    return getattr(bot.config, name, DEFAULTS[name])

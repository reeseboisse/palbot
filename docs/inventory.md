# Behaviour inventory

The fork's compatibility contract: everything here must keep working exactly
as it does in upstream [iamsix/palbot](https://github.com/iamsix/palbot) at
`e923b9a`. Change any of it only on purpose.

The machine-checked version of this list is `tests/snapshots/inventory.json`,
which `tests/test_inventory.py` compares against a fresh offline load of the
bot. That snapshot covers every prefix command (name, aliases, signature, help
text, checks, cooldowns), app commands, cog listeners, background loops and
the sqlite schemas created on load. This page is a readable summary of it plus
the parts a snapshot can't capture.

Run the checks with:

```sh
pip install -r requirements-dev.txt
pytest                                   # offline; network tests skipped
PALBOT_NETWORK_TESTS=1 pytest            # include live-API tests
python tests/inventory.py --update       # after an intentional surface change
```

## Bot core (`palbot.py`, `utils/`)

- Prefix `!`, case-insensitive commands, default help command (`dm_help=None`,
  checks not verified in help).
- All intents enabled (`members` and `message_content` included).
- Every `modules/*.py` is loaded as an extension at startup. A failed module
  is logged to stderr and skipped, and the bot keeps running.
- **Edit tracking:** the last 10 command messages are remembered with the
  bot's reply. Editing a command message re-runs it and **edits the existing
  reply** in place (stopping any paginator). Deleting the command message
  deletes the bot's reply. Editing a message that wasn't a command, so that it
  now starts with `!`, runs it as a new command.
- **Custom commands:** an unknown `!word` is looked up in
  `data/customcommands.sqlite`. If it exists there it's handled by the Chat
  cog and not logged as an error.
- Shared aiohttp session: IPv4 only, 10 connections per host, 5s total
  timeout, header/line limits doubled to 16380 bytes.
- Logging goes to `logfiles/debug.log` at INFO level.

## Background loops

| Cog | Loop | Started on load |
|---|---|---|
| Chat | `check_userthings` | yes |
| Reminder | `check_timers` | yes |
| Twitter | `tweet_subscriptions` | no (start is commented out upstream) |

Wotd also starts a one-off `load_wotd` task on load.

## Event listeners

| Cog | Events |
|---|---|
| Chat | `on_message`, `on_reaction_add` |
| Gemini | `on_message` |
| Logger | `on_message`, `on_message_edit`, `on_message_delete`, `on_reaction_add`, `on_member_update`, `on_guild_channel_update` |
| Persona | `on_ready` |
| Stars | `on_reaction_add` |
| Trivia | `on_message` |
| UsefulEvents (owner.py) | `on_reaction_add`, `on_reaction_remove` |
| Vids | `on_message` |
| VoiceTTS | `on_message`, `on_voice_state_update` |
| Wotd | `on_message` |

The `on_message` listeners do content-triggered work, such as answering
trivia, wotd hits, link previews, logging and TTS. The snapshot only records
that these listeners exist, not what they do, so this behaviour needs
targeted tests before those cogs are refactored.

## App commands

Synced globally by the owner-only `!synctree` command, which has to be run in a guild.

| Name | Kind |
|---|---|
| `/command` | slash: "Do a custom command" |
| `/remind` | slash: "Set a reminder to yourself" |
| Age | user context menu |
| Strava | user context menu |
| React Command | message context menu |

## Persistent data

The deployment mounts `config/`, `data/` and `logfiles/`. The new version must
read existing files as they are, with no migration.

| File | Owner | Tables |
|---|---|---|
| `data/customcommands.sqlite` | Chat, core | `commands`, `cfind*` (FTS) |
| `data/tags.sqlite` | Chat | `tags` |
| `data/reminders.sqlite` | Reminder | `reminders` |
| `data/stars.sqlite3` | Stars | `posts`, `settings` |
| `data/triviascores.sqlite` | Trivia | `scores` |
| `data/wotd.sqlite` | Wotd | `hitlog`, `settings` |
| `logfiles/ai_cache.db` | AICache (Copilot, Gemini, Persona) | `ai_acl`, `ai_acl_config`, `compaction_cache`, `migrations`, `personas`, `settings`, `usage_log`, `user_prompts` |
| `data/clues.db` | Trivia (read-only) | external, built by [jeopardy-parser](https://github.com/iamsix/jeopardy-parser) |
| `data/userinfo.sqlite` | `utils.context` (User, Weather, …) | created lazily, not in snapshot |
| `data/gemini_settings.sqlite` | Gemini | created lazily, not in snapshot |
| `logfiles/guild_<id>_log.sqlite` | Logger | per guild, created lazily, not in snapshot |
| `logfiles/gemini_<channel>.pkl` | Gemini | pickled chat history |
| `data/github-copilot.token.json`, `config/auth-profiles.json` | Copilot | auth tokens (paths from config) |

## Configuration (`config/config.py`)

Every key the code reads, as documented in `config/config.py.example`.
`tests/test_config_example.py` keeps the example and the code in sync.

`token`, `gsearchcx`, `gsearchapi`, `gsearch2`, `bravesearch`, `timezonedb`,
`forecast_io_key`, `accuweather_key`, `weathercom_key`, `vcrossing_key`,
`aqicn`, `spoontacular_key`, `untappd_clientid`, `untappd_clientsecret`,
`distillertoken`, `wolframAPIkey`, `mc_api_key`, `rt_url_1`, `rt_url_2`,
`rt_headers`, `wotd_whitelist`, `lastfm_api_key`, `stravaToken`,
`twitterconsumerkey`, `twitterconsumersecret`, `twitter_subscriptions`,
`reddituser`, `redditpw`, `redditclient`, `redditsecret`, `gemini_keys`,
`github_copilot_token_path`, `github_copilot_auth_profile_path`.

## Prefix commands

168 including subcommands. "Restrictions" are discord.py check predicates:
`is_owner` is the bot owner, `is_bot_admin` is Copilot/Gemini admin,
`has_any_role` is role-gated, and `Gemini.chat_channel` limits a command to a hardcoded channel allowlist in one guild (ID `124572142485504002`). Subcommands
also inherit their parent group's checks.

### Chat — `modules.chat`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!addcmd` |  |  |  |
| `!ban` | `!onions` |  | hidden |
| `!bot` |  |  |  |
| `!delcmd` |  | `has_any_role` |  |
| `!describecommand` |  |  | hidden |
| `!find` |  |  |  |
| `!fruits` |  |  |  |
| `!mermaid` |  |  |  |
| `!mock` |  |  |  |
| `!pdl` |  |  |  |
| `!poll` |  |  |  |
| `!qp` |  |  |  |
| `!tag` |  | `has_any_role` |  |
| `!testbutton` |  |  | hidden |
| `!translate` | `!tr` |  |  |
| `!xkcd` |  |  |  |

### Copilot — `modules.copilot`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!clai` |  |  |  |
| `!clai-acl` |  | `is_bot_admin` |  |
| `!claiconfig` |  | `is_bot_admin` |  |
| `!claihelp` |  |  |  |
| `!claireset` |  | `is_bot_admin` |  |
| `!claistatus` |  |  |  |
| `!claisummary` |  | `is_bot_admin` |  |
| `!claiuserprompt` |  |  |  |
| `!copilot-auth` |  | `is_bot_admin` |  |
| `!copilot-auth-status` |  | `is_bot_admin` |  |
| `!copilot-deauth` |  | `is_bot_admin` |  |
| `!glm` |  |  |  |
| `!glmconfig` |  | `is_bot_admin` |  |
| `!sclai` |  |  |  |
| `!sglm` |  |  |  |

### Finance — `modules.finance`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!coin` |  |  |  |
| `!stock` | `!stocks`, `!stonks` |  |  |

### Food — `modules.food`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!ba` |  |  |  |
| `!beer` |  |  |  |
| `!drink` |  |  |  |
| `!spirits` | `!booze`, `!liquor`, `!spirit` |  |  |
| `!wfd` |  |  |  |
| `!wine` |  |  |  |

### Games — `modules.games`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!cs2` |  |  |  |
| `!mtg` |  |  |  |
| `!owl` |  |  |  |

### Gemini — `modules.gemini`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!ai` |  |  |  |
| `!aiconfig` |  | `is_bot_admin` |  |
| `!aistats` |  |  | hidden |
| `!chat` |  | `Gemini.chat_channel` | hidden |
| `!dbgchat` |  |  | hidden |
| `!listenall` |  |  | hidden |
| `!newchat` |  | `Gemini.chat_channel` |  |
| `!sai` |  |  |  |

### Internets — `modules.internets`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!google` | `!gwiki` |  |  |
| `!ud` |  |  |  |
| `!wiki` |  |  |  |
| `!wolfram` | `!c` |  |  |

### Lounge<C++> — `modules.lounge`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!coliru` |  |  |  |
| `!cpp` |  |  |  |

### Lyrics — `modules.lrclib`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!lyrics` |  |  |  |

### Media — `modules.media`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!book` | `!gr` |  |  |
| `!imdb` |  |  |  |
| `!mc` |  |  |  |
| `!oc` |  |  |  |
| `!rt` |  |  |  |
| `!rttv` |  |  |  |

### News — `modules.news`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!bnews` |  |  |  |
| `!news` |  |  |  |

### Owner Commands — `modules.owner`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!die` |  | `is_owner` | hidden |
| `!infotest` |  |  | hidden |
| `!load` |  | `is_owner` | hidden |
| `!loglevel` |  | `is_owner` | hidden |
| `!nick` |  | `is_owner` | hidden |
| `!playing` |  | `is_owner` | hidden |
| `!reload` |  | `is_owner` | hidden |
| `!reload all` |  |  | hidden |
| `!reload config` |  |  | hidden |
| `!reload utils` |  |  | hidden |
| `!say` |  | `is_owner` | hidden |
| `!synctree` |  | `guild_only`, `is_owner` |  |
| `!unload` |  | `is_owner` | hidden |
| `!uptime` |  | `is_owner` | hidden |
| `!watching` |  | `is_owner` | hidden |

### Persona — `modules.persona`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!claipersona` |  |  |  |

### Pics — `modules.picsandvids`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!bimage` |  |  |  |
| `!image` | `!gif`, `!pic` |  |  |
| `!rpics` | `!birds`, `!cats`, `!dogs`, `!rats`, `!sloths` |  |  |

### Vids — `modules.picsandvids`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!yt` |  |  |  |

### Randomizers — `modules.randomizers`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!8=D` | `!udp` |  |  |
| `!bbnet` |  |  |  |
| `!brak` |  |  |  |
| `!cactus` |  |  |  |
| `!developers` |  |  |  |
| `!error` |  |  |  |
| `!mba` |  |  |  |
| `!roll` |  |  |  |
| `!wfl` |  |  |  |
| `!ziti` |  |  |  |

### Reminder — `modules.reminder`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!remindme` | `!remind` | `guild_only` |  |
| `!timetest` |  |  | hidden |

### Sports — `modules.sports`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!mlb` |  |  |  |
| `!nba` | `!wnba` |  |  |
| `!nba2` |  |  |  |
| `!nbat` |  |  | hidden |
| `!ncaa` | `!ncaahockey` |  |  |
| `!nfl` | `!cfb`, `!cfl`, `!ufl`, `!xfl` |  |  |
| `!nhl` |  |  |  |
| `!nhlt` |  |  | hidden |

### Stars — `modules.stars`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!starboard` |  | `has_any_role` |  |
| `!starlimit` |  | `has_any_role` |  |

### Strava — `modules.strava`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!strava` |  |  |  |
| `!strava activity` |  |  |  |
| `!strava set` |  |  |  |

### InfiniteTicTacToe — `modules.tictactoe`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!tictactoe` | `!ttt` |  |  |

### Trivia — `modules.trivia`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!hint` |  |  |  |
| `!trivia` |  |  |  |
| `!trivia autohint` |  |  |  |
| `!trivia delay` |  |  |  |
| `!trivia hard` |  |  |  |
| `!trivia help` |  |  | hidden |
| `!trivia round` |  |  |  |
| `!trivia score` |  |  |  |
| `!trivia stop` |  |  |  |
| `!trivia time` |  |  |  |

### Twitter — `modules.twitter`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!bsky` |  |  |  |
| `!kexp` |  |  | hidden |
| `!lasttweet` |  |  | hidden |
| `!musk` |  |  | hidden |
| `!trump` |  |  | hidden |
| `!twitter_token` |  | `is_owner` | hidden |

### User — `modules.user`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!age` |  |  |  |
| `!beats` |  |  |  |
| `!bounce` |  |  |  |
| `!np` |  |  |  |
| `!set` |  |  |  |
| `!set birthday` | `!age` |  |  |
| `!set last.fm` | `!lastfm`, `!np` |  |  |
| `!set location` |  |  |  |
| `!set strava` |  |  |  |
| `!time` |  |  |  |
| `!whopper` |  |  |  |

### VoiceTTS — `modules.voice_tts`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!tts` |  |  |  |
| `!tts join` |  |  |  |
| `!tts leave` |  |  |  |
| `!tts set` |  |  |  |
| `!tts skip` |  |  |  |
| `!tts status` |  |  |  |
| `!tts voice` |  |  |  |
| `!tts voices` |  |  |  |

### Weather — `modules.weather`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!aqi` |  |  |  |
| `!metar` |  |  |  |
| `!piw` | `!ppiw` |  |  |
| `!sun` | `!moon`, `!sunrise`, `!sunset` |  |  |
| `!vc` | `!pvc` |  |  |
| `!w` | `!forecast`, `!pw` |  |  |
| `!wc` | `!pwc` |  |  |
| `!wemojitest` |  | `is_owner` | hidden |
| `!wq` |  |  |  |
| `!yr` | `!pyr` |  |  |

### WorldCup — `modules.worldcup`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!worldcup` | `!wc2026` |  | cooldown 3/60s per user |
| `!worldcupgroup` | `!wcgroup` |  | cooldown 3/60s per user |
| `!worldcupschedule` | `!wcfixtures`, `!wcschedule` |  | cooldown 3/60s per user |
| `!worldcupstandings` | `!wcstandings`, `!wctable` |  | cooldown 3/60s per user |

### Wotd — `modules.wotd`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!checkwotd` |  | `is_owner` | hidden |
| `!newwotd` |  |  | hidden |
| `!wordcount` | `!fullwordcount` |  | hidden |
| `!wotd` | `!gotd` |  |  |
| `!wotdhint` |  |  | hidden |
| `!wotdstats` |  | `is_owner` | hidden |
| `!wotdtest` |  | `is_owner` | hidden |

### (built-in) — `discord.ext.commands`

| Command | Aliases | Restrictions | Notes |
|---|---|---|---|
| `!help` |  |  |  |


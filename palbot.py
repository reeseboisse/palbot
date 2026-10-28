from socket import AF_INET
from aiohttp import ClientSession, ClientTimeout, TCPConnector

import discord
from discord.ext import commands
import config.config as config

from pathlib import Path

import datetime
import sys, traceback
import logging
import aiosqlite


FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"


class PalBot(commands.Bot):

    def __init__(self):
        help_command = commands.DefaultHelpCommand(dm_help=None)
        help_command.verify_checks = False
        super().__init__(command_prefix=["!"],
                description="https://github.com/iamsix/palbot/ by six",
                case_insensitive=True,
                help_command=help_command,
                intents=discord.Intents.all())

        self.logger = logging.getLogger("palbot")
        self.moddir = "modules"
        self.config = config
        self.utils = __import__('utils')
        # for the custom commands so I don't need to reopen the db each time
        self.cc_conn = None
        # This contains a tuple indexed by user-message-id where:
        #  [0] = the bot's response Message obj
        #  [1] = Paginator (None if not paginating)
        self.recent_posts = self.utils.LimitedSizeDict(maxlen=10)

    async def setup_hook(self):
        connector = TCPConnector(family=AF_INET, limit_per_host=10)
        timeout = ClientTimeout(total=5)
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            max_line_size=8190 * 2,
            max_field_size=8190 * 2,
            )
        for module in Path(self.moddir).glob('*.py'):
            try:
                await self.load_extension("{}.{}".format(self.moddir, module.stem))
            except Exception as e:
                print(f'Failed to load cog {module}', file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        if 'Chat' in self.cogs:
            self.cc_conn = await aiosqlite.connect("data/customcommands.sqlite")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound) and self.cc_conn:
            # shouldn't happen too often.. I think checking the sqlite is better than
            # storing the entire command list in memory, even though it's likely small
            async with self.cc_conn.execute(
                "SELECT cmd FROM commands WHERE cmd = (?)",
                [ctx.invoked_with.lower()]) as c:

                result = await c.fetchone()
                if result:
                    return
            self.logger.info(error)

        if hasattr(ctx.command, 'on_error'):
            return
        cog = ctx.cog
        if cog:
            if commands.Cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.now(datetime.timezone.utc)
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_message(self, message):
        ctx = await self.get_context(message, cls=self.utils.MoreContext)
        await self.invoke(ctx)

    async def on_message_delete(self, message):
        if message.id in self.recent_posts:
            bot_msg, _ = self.recent_posts[message.id]
            await bot_msg.delete()
            self.recent_posts.pop(message.id)

    async def on_message_edit(self, before, after):
        # Check if this was a tracked message (bot already responded)
        if before.id in self.recent_posts:
            bot_msg, pg = self.recent_posts[before.id]
            if pg:
                pg.stop()
            ctx = await self.get_context(after, cls=self.utils.MoreContext)
            ctx.override_send_for_edit = (after, bot_msg)
            await self.invoke(ctx)
            return

        # If not tracked, treat edited message as a new command
        # (handles case where user corrects a typo in command)
        if after.content.startswith(tuple(self.command_prefix)):
            ctx = await self.get_context(after, cls=self.utils.MoreContext)
            await self.invoke(ctx)

    def run(self):
        super().run(config.token, reconnect=True)

    async def close(self):
        await super().close()
        sys.exit()


def main():
    logging.basicConfig(filename='logfiles/debug.log', level=logging.INFO, format=FORMAT)
    PalBot().run()


if __name__ == "__main__":
    main()

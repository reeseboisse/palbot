import asyncio
import aiohttp

import discord
from discord.ext import commands
import config

from pathlib import Path
# instead of a userlocation see about subclassing my own discord user class

import datetime
import sys, traceback
import logging
from collections import deque



FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
logging.basicConfig(filename='debug.log',level=logging.INFO, format=FORMAT)


class PalBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix=["$"], 
                description="https://github.com/iamsix/palbot/", 
                pm_help=None, help_attrs=dict(hidden=True), 
                fetch_offline_members=False)
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.logger = logging.getLogger("palbot")
        self.moddir = "modules"
        

        for module in Path(self.moddir).glob('*.py'):
            try:
                self.load_extension("{}.{}".format(self.moddir,module.stem))
            except Exception as e:
                print(f'Failed to load cog {module}', file=sys.stderr)
                traceback.print_exec()

#        self.lastresponses = None #deque (command, myresponse)
#        look in to the internal message cache
#        https://discordpy.readthedocs.io/en/latest/api.html#discord.Client.cached_messages


#       self.pagedposts = None #deque (just a simple list of my posts?)
        # may move pagedposts in to a utils module
        # have the pagedpost thing keep all the data itself

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        print(f'Ready: {self.user} (ID: {self.user.id})')

    def run(self):
        super().run(config.token, reconnect=True)

    @property
    def utils(self):
        return __import__('utils')

    @property
    def config(self):
        return __import__('config')


bot = PalBot()
bot.run()

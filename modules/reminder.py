from discord.ext import commands, tasks
import discord
import asyncio
import sqlite3
from datetime import datetime
from dataclasses import dataclass
import pytz
import dateparser
from zoneinfo import ZoneInfo
# 'when' is not stricyly necessary here, just a convenience thing
# timestamp | Channel | userid | when | remindertext

@dataclass
class ReminderItem:
    channel: int
    user: int
    when: datetime
    message: str


class Reminder(commands.Cog):
    reminders = set()
    def __init__(self, bot):
        self.bot = bot

        self.conn = sqlite3.connect("reminders.sqlite")
        self.c = self.conn.cursor()

        q = '''CREATE TABLE IF NOT EXISTS 'reminders' ("timestamp" integer, "channel" integer, "user" integer, "when" text, "reminder" text);'''
        self.c.execute(q)
        self.conn.commit()
        self.check_timers.start()


    async def start_timer(self, reminder):
        seconds = max(0,int((reminder.when - datetime.utcnow()).total_seconds()))
        await asyncio.sleep(seconds)
        await self.call_reminder(reminder)


    async def save_timer(self, reminder):
        q = "INSERT INTO reminders VALUES (?, ?, ?, ?, ?)"
        self.c.execute(q, (int(reminder.when.timestamp()), 
                           reminder.channel, reminder.user, 
                           str(reminder.when), reminder.message))
        self.conn.commit()

    @tasks.loop(minutes=(60 * 24))
    async def check_timers(self):
        print("remindme loop")
        ts = int(datetime.utcnow().timestamp())
        ts += 24*60*60
        q = 'SELECT timestamp, channel, user, reminder FROM reminders WHERE timestamp <= ?'
        res = self.c.execute(q, [(ts)])
        for row in res:
            when = datetime.fromtimestamp(row[0])
            reminder = ReminderItem(row[1], row[2], when, row[3])
            await self.set_timer(reminder)


    async def set_timer(self, reminder):
        task = asyncio.create_task(self.start_timer(reminder))
        self.reminders.add(task)
        task.add_done_callback(self.reminders.discard)


    @commands.command()
    async def timetest(self, ctx, *, time):
        tz = ctx.author_info.timezone
        date = dateparser.parse(time, settings={'TIMEZONE': tz, 
                                      'PREFER_DATES_FROM': 'future'})
        if tz and date:
            ntz = ZoneInfo(tz)
            utc = ZoneInfo("UTC")
            date = date.replace(tzinfo=ntz).astimezone(tz=utc).replace(tzinfo=None)
        await ctx.send(f"<t:{int(date.timestamp())}>")

    @commands.command()
    async def remindme(self, ctx, *, message: commands.clean_content):
        try:
            when, what = message.split(" to ", 1)
        except ValueError:
            await ctx.reply("You're probably missing a 'to' - format is `!remindme <when> to <what>`")
            return

        tz = ctx.author_info.timezone
        date = dateparser.parse(when, settings={'TIMEZONE': tz, 
                                      'PREFER_DATES_FROM': 'future'})
        if not date:
            await ctx.reply("I don't understand when you want this done. Try something like `tomorrow at 8pm` or `jan 3rd 2pm` or `in 5 minutes` - format is `!remindme <when> to <what>`")
            return

        if tz:
            ntz = ZoneInfo(tz)
            utc = ZoneInfo("UTC")
            date = date.replace(tzinfo=ntz).astimezone(tz=utc).replace(tzinfo=None)
        seconds = int((date - datetime.utcnow()).total_seconds())
        reminder = ReminderItem(ctx.channel.id, ctx.author.id, date, what)
        if seconds < 0:
            await ctx.send("I can't remind you of something in the past")
            return
        elif seconds > (24 * 60 * 60):
            #save this for later
            pass
        else:
            #this is today so set the timer immediately
            await self.set_timer(reminder)
        await self.save_timer(reminder)


        await ctx.send (f"I will remind you on <t:{int(date.timestamp())}> to: {what}")

    async def call_reminder(self, reminder):
        channel = self.bot.get_channel(reminder.channel)
        msg = f'<@{reminder.user}>: {reminder.message}'

        await channel.send(msg)

        q = 'DELETE FROM reminders WHERE timestamp <= ?'
        self.c.execute(q, [(int(reminder.when.timestamp()))])
        self.conn.commit()


    async def cog_unload(self):
        for reminder in self.reminders:
            # cancel all the timers here
            reminder.cancel()

async def setup(bot):
    await bot.add_cog(Reminder(bot))

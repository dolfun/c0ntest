from contest_database import ContestDatabase
from contest_platform import get_platforms
from discord.ext import tasks
import discord
import os

class C0ntestClient(discord.Client):
  def __init__(self, channel_id, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.channel_id = int(channel_id)

    os.makedirs('database', exist_ok=True)
    self.database = ContestDatabase(
      filename='database/contest',
      platforms=get_platforms()
    )

  async def setup_hook(self):
    self.background_task.start()

  @tasks.loop(minutes=10)
  async def background_task(self):
    self.database.update()

    channel = self.get_channel(self.channel_id)
    for notification in self.database.notifications():
      await channel.send(notification)

  @background_task.before_loop
  async def before_background_task(self):
    await self.wait_until_ready()

if __name__ == '__main__':
  token = os.getenv('token')
  channel_id = os.getenv('channel_id')

  client = C0ntestClient(channel_id=channel_id, intents=discord.Intents.default())
  client.run(token, root_logger=True)
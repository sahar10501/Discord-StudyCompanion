import json
import os
import asyncio
import aiohttp
from aiohttp.client import ClientSession
from quart.wrappers import response
from werkzeug.datastructures import Headers

class AsyncHttpRequest:

    def __init__(self):
        self.session = None
        self.headers = {"Authorization": 'Bot {}'.format(os.getenv("TOKEN"))}


    async def create_dm_channel(self, user_id):
        if self.session is None:
            self.session = ClientSession()
        async with self.session.post(url="https://discord.com/api/users/@me/channels",
                                 json={"recipient_id": user_id}, headers={"Authorization": 'Bot {}'.format(os.getenv("TOKEN"))}) as response:
            return await response.json()

    async def init_dm_channels(self, users_id):
            results = await asyncio.gather(*[self.create_dm_channel(user) for user in users_id], return_exceptions=True)
            return results

    async def get_guild_member(self, cur_sess, guild_id):
        async with self.ses.get(url=f'https://discord.com/api/guilds/{guild_id}/members', headers=self.headers,
                                params={"limit": 1000}) as response:
            return await response.json()

    async def send_dm(self, chat_ids):
        if self.session is None:
            self.sessions = ClientSession()
        async with self.session.post(url=f"https://discord.com/api/channels/{chat_ids}/messages",
                                 json={"content": "hello!!!!!!"}, headers={"Authorization": 'Bot {}'.format(os.getenv("TOKEN"))}) as response:
            return await response.json()
    
    async def inv_multiple_users(self, chat_ids):
            results = await asyncio.gather(*[self.send_dm(chat_ids) for id in chat_ids], return_exceptions=True)
            return results

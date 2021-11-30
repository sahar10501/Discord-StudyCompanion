import json
import os
import asyncio
import aiohttp
from aiohttp.client import ClientSession
from dotenv.main import load_dotenv
from quart.wrappers import response
from werkzeug.datastructures import Headers

class AsyncHttpRequest:

    def __init__(self):
        load_dotenv()
        self.session = None
        token = os.getenv("TOKEN")
        self.headers = {"Authorization": f'Bot {token}'}
        self.base_url = "https://discord.com/api"


    async def create_dm_channel(self, user_id):
        if self.session is None:
            self.session = ClientSession()
        async with self.session.post(url=f"{self.base_url}/users/@me/channels",
                                 json={"recipient_id": user_id}, headers=self.headers) as response:
            return await response.json()

    async def init_dm_channels(self, users_id):
            """ requesting multiple create channel requets """
            results = await asyncio.gather(*[self.create_dm_channel(user) for user in users_id], return_exceptions=True)
            return results

    async def get_guild_members(self, guild_id):
        if self.session is None:
            self.session = ClientSession()
        async with self.session.get(url=f"{self.base_url}/guilds/{guild_id}/members", headers=self.headers,
                                params={"limit": 1000}) as response:
            return await response.json()

    async def send_dm(self, chat_ids, invite):
        if self.session is None:
            self.session = ClientSession()
        async with self.session.post(url=f"{self.base_url}/channels/{chat_ids}/messages",
                                 json={"content": f"Your Friend is inviting you to study {invite}"}, headers=self.headers) as response:
            return await response.json()
    
    async def inv_multiple_users(self, chat_ids, invite):
            results = await asyncio.gather(*[self.send_dm(id, invite) for id in chat_ids], return_exceptions=True)
            return results
    
    async def create_channel(self, guild_id, channel_name):
        """ Creates a voice channel for the invited users to study in """
        if self.session is None:
            self.session = ClientSession()
        channel = {
            "name": channel_name,
            "type": 2,
            "user_limit": 4,
        }
        async with self.session.post(url=f"{self.base_url}/guilds/{guild_id}/channels", headers=self.headers,
                                json=channel) as response:
            return await response.json()

    async def create_invite(self, channel_id):
        if self.session is None:
            self.session = ClientSession()
        invite = {
            "max_age": 900,
            "max_uses": 2,
        }
        async with self.session.post(url=f"{self.base_url}/channels/{channel_id}/invites", headers=self.headers,
                                json=invite) as response:
            response = await response.json()
            inv_code = response["code"]
            invite_msg = f"https://discord.gg/{inv_code}"
            return invite_msg

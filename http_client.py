import os
import asyncio
import aiohttp


class AsyncHttpRequest:

    async def __aenter__(self):
        self.ses = aiohttp.ClientSession()
        return self.ses

    async def __aexit__(self, *err):
        await self._session.close()
        self._session = None






    async def get_guild_member(self, cur_sess, guild_id):
        async with self._session.get(url=f'https://discord.com/api/guilds/{guild_id}/members', headers=self.headers,
                                params={"limit": 1000}) as response:
            return await response.json()


    async def create_dm_channel(self, user_id):
        async with self._session.post(url="https://discord.com/api/users/@me/channels",
                                 json={"recipient_id": user_id}, headers=self.headers) as response:
            return await response.text()

    async def fetch_all(self, users_id):
            results = await asyncio.gather(*[self.create_dm_channel(user) for user in users_id], return_exceptions=True)
            return results

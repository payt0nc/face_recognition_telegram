from telethon import TelegramClient
import asyncio

# FILL these in
api_id = 0
api_hash = ''

async def main():
    client = TelegramClient(
                'user',
                api_id,
                api_hash
            )
    await client.start()

asyncio.get_event_loop().run_until_complete(main())


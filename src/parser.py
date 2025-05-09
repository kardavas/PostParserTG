import os
from telethon.sync import TelegramClient
from telethon.tl.types import MessageService
import pandas as pd
from datetime import datetime
import asyncio
import aiohttp
from telethon.sessions import StringSession
from telethon import connection

class PostParser:
    def __init__(self, api_client):
        self.api_client = api_client

    def fetch_posts(self, channel_id, start_date, end_date):
        posts = []
        # Logic to connect to the Telegram channel and fetch posts
        # based on the specified dates would go here.
        # For each post, determine if it's an original or a repost
        # and get the view count.
        
        # Example structure of a post:
        # post = {
        #     'content': 'Post content here',
        #     'type': 'original' or 'repost',
        #     'views': 123
        # }
        
        return posts

    def determine_post_type(self, post):
        # Logic to determine if the post is original or a repost
        pass

    def get_view_count(self, post):
        # Logic to retrieve the view count for the post
        pass

# Ваши данные для Telethon
API_ID = 28578374
API_HASH = "269d9efb4a74a9167bc106260d3f7bd7"
PHONE_NUMBER = "+79850809094"  # Добавлен номер для автоматической передачи

# Функция для парсинга постов из канала на заданную дату
# Возвращает путь к CSV-файлу

async def parse_channel_posts(channel, date_from_str, date_to_str=None):
    date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
    if date_to_str:
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
    else:
        date_to = date_from
    session_name = os.path.join(os.path.dirname(__file__), "tg_session")
    client = TelegramClient(
        session_name,
        API_ID,
        API_HASH,
        connection=connection.ConnectionTcpAbridged,
        connection_retries=5,
        timeout=120
    )
    posts = []
    async with client:
        if not await client.is_user_authorized():
            await client.start(phone=PHONE_NUMBER)
        async for message in client.iter_messages(channel):  # reverse=False по умолчанию
            if isinstance(message, MessageService):
                continue
            msg_date = message.date.date()
            if msg_date < date_from.date():
                break  # дальше только старее, можно остановить цикл
            if msg_date > date_to.date():
                continue  # пропускаем слишком новые
            text = message.text or "[без текста]"
            is_repost = "репост" if message.fwd_from else "оригинал"
            views = message.views if message.views is not None else 0
            posts.append({
                "date": message.date.strftime("%Y-%m-%d %H:%M"),
                "text": text,
                "type": is_repost,
                "views": views
            })
    df = pd.DataFrame(posts)
    if date_to_str:
        csv_path = os.path.join(os.path.dirname(__file__), f"posts_{date_from_str}_to_{date_to_str}.csv")
    else:
        csv_path = os.path.join(os.path.dirname(__file__), f"posts_{date_from_str}.csv")
    df.to_csv(csv_path, index=False)
    return csv_path
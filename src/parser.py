import os
from telethon.sync import TelegramClient
from telethon.tl.types import MessageService, ChannelForbidden, User, Channel # Added User, Channel
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

ORGANIZATIONAL_KEYWORDS = [
    "официальный", "ведомство", "министерство", "государственный", "служба",
    "департамент", "администрация", "компания", "организация", "пресс-служба",
    "новости", "тв", "радио", "газета", "журнал", "банк", "фонд", "партия",
    "завод", "институт", "университет", "школа", "бренд", "магазин", "сеть",
    "official", "department", "ministry", "government", "service", "company",
    "organization", "press service", "news", "tv", "radio", "gazette", "journal",
    "bank", "foundation", "party", "brand", "store", "chain", "ltd", "inc", "corp",
    "гос", "муп", "гуп", "фгуп", "фгбу", "мбу", "мку"
]

async def is_organizational_channel(client, channel_entity): # Changed to accept entity
    """Checks if a channel seems to be organizational based on its info."""
    # No longer needs to call client.get_entity here, assumes channel_entity is already a valid entity
    # However, the original function design might be called with username string elsewhere,
    # so for safety, we can add a check or ensure it's always called with an entity.
    # For now, let's assume it's called with an entity that is a Channel.

    title = channel_entity.title.lower() if hasattr(channel_entity, 'title') and channel_entity.title else ""
    about = channel_entity.about.lower() if hasattr(channel_entity, 'about') and channel_entity.about else ""

    # Check for keywords in title
    for keyword in ORGANIZATIONAL_KEYWORDS:
        if keyword in title:
            return True

    # Check for keywords in description (about)
    for keyword in ORGANIZATIONAL_KEYWORDS:
        if keyword in about:
            return True
            
    # Optionally, consider verified status, but it's tricky as individuals can be verified.
    # if hasattr(entity, 'verified') and entity.verified:
    #     # This might be too broad, many public figures are verified.
    #     # Consider if specific keywords are ALSO present.
    #     pass

    return False

# Функция для парсинга постов из канала на заданную дату
# Возвращает путь к CSV-файлу или специальную строку, если канал организационный
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
            # Consider how to handle this in a deployed bot - manual intervention might be needed.
            # For now, let it try to start, but this might fail on a server without input.
            try:
                await client.start(phone=PHONE_NUMBER)
            except RuntimeError as e:
                print(f"ERROR: Could not authorize Telethon client: {e}. Ensure session is valid or can be created.")
                return "error_telethon_auth" # New error type

        try:
            entity = await client.get_entity(channel)
        except ValueError: # Channel not found
            print(f"ERROR: Channel or user '{channel}' not found.")
            return "error_channel_not_found"
        except Exception as e: # Other potential errors like network issues
            print(f"ERROR: Could not get entity for '{channel}': {e}")
            return "error_getting_entity"

        # SECURITY CHECK: Ensure the entity is a public channel
        if not isinstance(entity, Channel) or not entity.username:
            print(f"ERROR: '{channel}' is not a public channel (it might be a user, private group/channel, or invalid).")
            return "error_not_public_channel" # New error type for bot.py to handle

        # Now that we have the entity and it's a public channel, pass it to is_organizational_channel
        if await is_organizational_channel(client, entity): # Pass the entity directly
            return "error_organizational"

        async for message in client.iter_messages(entity): # Use the validated entity
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
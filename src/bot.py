import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from parser import parse_channel_posts
import asyncio

load_dotenv()

# Replace hardcoded token with environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHANNEL, DATE_FROM, DATE_TO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text("Привет! Для парсинга напиши /parse")

async def parse_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришли ссылку на канал или username (например, https://t.me/durov или durov):")
    return CHANNEL

async def get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = update.message.text.strip()
    if channel.startswith("https://t.me/"):
        channel = channel.replace("https://t.me/", "")
    if channel.startswith("@"):
        channel = channel[1:]
    context.user_data['channel'] = channel
    await update.message.reply_text("Теперь пришли начальную дату (ГГГГ-ММ-ДД):")
    return DATE_FROM

async def get_date_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_from = update.message.text.strip()
    context.user_data['date_from'] = date_from
    await update.message.reply_text("Теперь пришли конечную дату (ГГГГ-ММ-ДД):")
    return DATE_TO

async def get_date_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_to = update.message.text.strip()
    channel = context.user_data['channel']
    date_from = context.user_data['date_from']
    await update.message.reply_text("Парсинг начался, пожалуйста, подождите...", reply_markup=ReplyKeyboardRemove())
    try:
        logger.info(f"Парсим канал: {channel} с {date_from} по {date_to}")
        csv_path = await parse_channel_posts(channel, date_from, date_to)
        await update.message.reply_document(open(csv_path, "rb"))
        logger.info(f"Файл {csv_path} отправлен пользователю {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        await update.message.reply_text(f"Ошибка при парсинге: {str(e)}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("parse", parse_start)],
        states={
            CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channel)],
            DATE_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_from)],
            DATE_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_to)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()
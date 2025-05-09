import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction # Removed ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from parser import parse_channel_posts
import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
# Removed re import as it's no longer needed

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # Assuming logger is defined globally or passed appropriately if this is an issue.
    # For now, using print for critical startup error if logger isn't ready.
    print("ERROR: GEMINI_API_KEY не найден в переменных окружения.")


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHANNEL, DATE_FROM, DATE_TO = range(3)
MAX_MESSAGE_LENGTH = 4096

# Removed escape_md_v2 function
# Removed process_gemini_tagged_text function

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_user.id}")
    keyboard = [
        [InlineKeyboardButton("Анализ психо-профиля", callback_data="start_profile_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Нажми кнопку ниже, чтобы начать анализ психологического профиля автора по постам из Telegram-канала.",
        reply_markup=reply_markup
    )

async def analysis_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the inline button press and starts the conversation for analysis."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query
    
    logger.info(f"Inline button 'start_profile_analysis' pressed by {query.from_user.id}")
    
    # Remove the inline keyboard from the original message
    # await query.edit_message_reply_markup(reply_markup=None) # Optional: remove keyboard after click

    await query.message.reply_text( # Send a new message
        "Пожалуйста, пришлите ссылку на публичный Telegram-канал (например, @example_channel или https://t.me/example_channel), и я проанализирую его посты за последние 2 года.",
        reply_markup=ReplyKeyboardRemove() # In case any old reply keyboard was somehow active
    )
    return CHANNEL # Transition to the state where bot expects channel input

async def send_long_message(update: Update, text_to_send: str, prefix="", parse_mode=None, reply_markup=None): # parse_mode will be None
    """Sends a long message by splitting it into parts if necessary."""
    
    # Removed conditional processing for ParseMode.MARKDOWN_V2
    processed_text = text_to_send

    if not processed_text: # Check processed_text (which is now same as text_to_send)
        await update.message.reply_text(prefix + "Нет данных для отображения.", reply_markup=reply_markup)
        return

    full_text = prefix + processed_text
    
    if len(full_text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(full_text, reply_markup=reply_markup) # Removed parse_mode
    else:
        current_pos = 0
        if prefix:
            await update.message.reply_text(prefix) # Removed parse_mode
            text_to_chunk = processed_text 
        else:
            text_to_chunk = full_text 

        for i in range(0, len(text_to_chunk), MAX_MESSAGE_LENGTH):
            chunk = text_to_chunk[i:i + MAX_MESSAGE_LENGTH]
            is_last_chunk = (i + MAX_MESSAGE_LENGTH >= len(text_to_chunk))
            current_reply_markup = reply_markup if is_last_chunk else None
            await update.message.reply_text(chunk, reply_markup=current_reply_markup) # Removed parse_mode

async def get_channel_and_parse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_input = update.message.text.strip()
    chat_id = update.effective_chat.id

    if channel_input.startswith("https://t.me/"):
        channel = channel_input.replace("https://t.me/", "")
    elif channel_input.startswith("@"):
        channel = channel_input[1:]
    else:
        channel = channel_input

    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=2*365)).strftime('%Y-%m-%d')

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await update.message.reply_text(
        f"Проверяю канал {channel} и начинаю парсинг за последние 2 года: с {date_from} по {date_to}. Это может занять некоторое время..."
    )

    try:
        logger.info(f"Парсим канал: {channel} с {date_from} по {date_to}")
        result = await parse_channel_posts(channel, date_from, date_to)

        if result == "error_organizational":
            keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Канал \"{channel}\" выглядит как канал организации. Пожалуйста, предоставьте ссылку на личный канал.", reply_markup=reply_markup)
            return ConversationHandler.END
        
        csv_path = result

        if not csv_path or not os.path.exists(csv_path):
            keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Не удалось получить файл с постами. Попробуйте другой канал или проверьте настройки.", reply_markup=reply_markup)
            return ConversationHandler.END

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await update.message.reply_text("Посты собраны. Начинаю анализ с помощью Gemini...")

        csv_content = ""
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()

        if not csv_content.strip():
            keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Файл с постами пуст. Анализ невозможен.", reply_markup=reply_markup)
            return ConversationHandler.END
        
        if not GEMINI_API_KEY:
            keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Ошибка: Ключ GEMINI_API_KEY не настроен. Анализ невозможен.", reply_markup=reply_markup)
            return ConversationHandler.END

        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Updated prompt for Gemini to request plain text
        prompt = f'''Проанализируй предоставленные тексты постов для составления гипотетического психологического портрета их автора.
Ответ предоставь в виде ОБЫЧНОГО НЕФОРМАТИРОВАННОГО ТЕКСТА. НЕ ИСПОЛЬЗУЙ Markdown или какое-либо другое форматирование (например, жирный шрифт, курсив, списки, заголовки).
Просто изложи анализ как сплошной текст, разделяя абзацы пустыми строками, если это необходимо для читаемости.

Включи в анализ следующие аспекты, основываясь исключительно на тексте постов:

1.  Основные темы и их эмоциональная окраска.
2.  Стиль письма и речевые особенности.
3.  Предполагаемые ценности и убеждения.
4.  Возможные интересы и увлечения.
5.  Социальное взаимодействие (если применимо из текстов).
6.  Общий вывод.

Пожалуйста, помни, что это анализ на основе текстовых данных и не является клинической оценкой.

Данные постов (в формате CSV):
{csv_content[:100000]}
'''
        analysis_result = ""
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            response = await model.generate_content_async(prompt)
            analysis_result = response.text
        except Exception as e:
            logger.error(f"Ошибка при вызове Gemini API: {e}")
            error_details = getattr(e, 'message', str(e.args[0] if e.args else e))
            keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Произошла ошибка при анализе данных с помощью Gemini: {error_details}. Попробуйте позже.", reply_markup=reply_markup)
            return ConversationHandler.END

        keyboard_after_analysis = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
        reply_markup_after_analysis = InlineKeyboardMarkup(keyboard_after_analysis)
        
        # Removed parse_mode=ParseMode.MARKDOWN_V2
        await send_long_message(update, analysis_result, f"Результаты анализа канала {channel}:\n\n", reply_markup=reply_markup_after_analysis)
        logger.info(f"Анализ канала {channel} отправлен пользователю {update.effective_user.id}")

    except FileNotFoundError:
        logger.error(f"Файл CSV не найден после парсинга: {csv_path}")
        keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Произошла ошибка: не удалось найти файл с данными после парсинга.", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Критическая ошибка в get_channel_and_parse: {e}", exc_info=True)
        keyboard = [[InlineKeyboardButton("🔍 Новый анализ", callback_data="start_profile_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Произошла непредвиденная ошибка: {str(e)}", reply_markup=reply_markup)

    return ConversationHandler.END

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
        entry_points=[CallbackQueryHandler(analysis_button_callback, pattern='^start_profile_analysis$')],
        states={
            CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channel_and_parse)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    logger.info("Бот запускается...")
    app.run_polling()
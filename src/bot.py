import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from parser import parse_channel_posts
import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai

load_dotenv()

# Replace hardcoded token with environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("GEMINI_API_KEY не найден в переменных окружения.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHANNEL, DATE_FROM, DATE_TO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text("Привет! Для парсинга напиши /parse")

async def parse_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/parse_analyze command from {update.effective_user.id}")
    await update.message.reply_text(
        "Привет! Пришли мне ссылку на публичный Telegram-канал (например, @example_channel или https://t.me/example_channel), и я проанализирую его посты за последние 2 года.",
        reply_markup=ReplyKeyboardRemove()
    )
    return CHANNEL

async def get_channel_and_parse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_input = update.message.text.strip()
    if channel_input.startswith("https://t.me/"):
        channel = channel_input.replace("https://t.me/", "")
    elif channel_input.startswith("@"):
        channel = channel_input[1:]
    else:
        channel = channel_input

    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=2*365)).strftime('%Y-%m-%d')

    await update.message.reply_text(
        f"Начинаю парсинг канала {channel} за последние 2 года: с {date_from} по {date_to}. Это может занять некоторое время..."
    )

    try:
        logger.info(f"Парсим канал: {channel} с {date_from} по {date_to}")
        # Убедимся, что parse_channel_posts возвращает путь к файлу
        csv_path = await parse_channel_posts(channel, date_from, date_to)
        
        if not csv_path or not os.path.exists(csv_path):
            await update.message.reply_text("Не удалось получить файл с постами. Попробуйте другой канал или проверьте настройки.")
            return ConversationHandler.END

        await update.message.reply_text("Посты собраны. Начинаю анализ с помощью Gemini...")

        # Читаем содержимое CSV файла
        csv_content = ""
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()

        if not csv_content.strip():
            await update.message.reply_text("Файл с постами пуст. Анализ невозможен.")
            return ConversationHandler.END
        
        if not GEMINI_API_KEY:
            await update.message.reply_text("Ошибка: Ключ GEMINI_API_KEY не настроен. Анализ невозможен.")
            return ConversationHandler.END

        # Анализ с помощью Gemini
        model = genai.GenerativeModel('gemini-1.5-flash') # Изменено с gemini-pro
        
        # Формируем промпт для Gemini
        # Важно: Gemini может иметь ограничения на длину входных данных.
        # Если CSV очень большой, его нужно будет разбить на части или предварительно обработать.
        prompt = f'''Проанализируй предоставленные тексты постов для составления гипотетического психологического портрета их автора.
Включи в анализ следующие аспекты, основываясь исключительно на тексте постов:

1.  **Основные темы и их эмоциональная окраска**: Какие темы чаще всего поднимает автор? Каков эмоциональный тон этих тем (позитивный, негативный, нейтральный, амбивалентный)?
2.  **Стиль письма и речевые особенности**: Использует ли автор формальный или неформальный язык? Есть ли характерные слова, фразы, метафоры или обороты речи? Как это может характеризовать автора?
3.  **Предполагаемые ценности и убеждения**: Какие ценности, взгляды или убеждения можно предположить на основе содержания постов?
4.  **Возможные интересы и увлечения**: О чем автор пишет с энтузиазмом или часто упоминает, что может указывать на его интересы?
5.  **Социальное взаимодействие (если применимо из текстов)**: Как автор взаимодействует с аудиторией или другими людьми в своих постах (если это отражено)?
6.  **Общий вывод**: Сформулируй краткое резюме о предполагаемом психологическом портрете автора, основываясь на вышеперечисленных пунктах.

Пожалуйста, помни, что это анализ на основе текстовых данных и не является клинической оценкой. Все выводы должны быть подкреплены примерами или отсылками к тексту постов, если это возможно.

Данные постов (в формате CSV):
{csv_content[:100000]}
'''
        # Ограничиваем размер промпта для API, если csv_content слишком большой

        try:
            response = await model.generate_content_async(prompt)
            analysis_result = response.text
        except Exception as e:
            logger.error(f"Ошибка при вызове Gemini API: {e}")
            # Попытка получить более детальную информацию об ошибке, если доступно
            error_details = ""
            if hasattr(e, 'message'):
                error_details = e.message
            elif hasattr(e, 'args') and e.args:
                error_details = e.args[0]
            await update.message.reply_text(f"Произошла ошибка при анализе данных с помощью Gemini: {error_details}. Попробуйте позже.")
            return ConversationHandler.END


        await update.message.reply_text(f"Результаты анализа канала {channel}:\n\n{analysis_result}")
        logger.info(f"Анализ канала {channel} отправлен пользователю {update.effective_user.id}")

    except FileNotFoundError:
        logger.error(f"Файл CSV не найден после парсинга: {csv_path}")
        await update.message.reply_text("Произошла ошибка: не удалось найти файл с данными после парсинга.")
    except Exception as e:
        logger.error(f"Критическая ошибка в get_channel_and_parse: {e}", exc_info=True)
        await update.message.reply_text(f"Произошла непредвиденная ошибка: {str(e)}")

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
    
    # Обновляем ConversationHandler для новой логики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("parse_analyze", parse_start)], # Новая команда для запуска
        states={
            CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channel_and_parse)],
            # Удаляем DATE_FROM и DATE_TO, так как даты теперь вычисляются автоматически
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start)) # Оставляем команду /start
    # Удаляем старый conv_handler, если он был добавлен отдельно
    # app.remove_handler(conv_handler) # Если был старый обработчик с командой /parse
    app.add_handler(conv_handler) # Добавляем новый обработчик
    
    logger.info("Бот запускается...")
    app.run_polling()
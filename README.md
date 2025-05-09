# Telegram Post Parser Bot

This project is a Telegram bot designed to parse posts from open Telegram channels based on specified dates. It collects the posts, determines whether they are original or reposts, and retrieves the view counts for each post. The parsed data is then exported to a CSV file for easy access and analysis.

## Описание на русском языке

Этот проект представляет собой Telegram-бота, предназначенного для парсинга постов из открытых Telegram-каналов на основе указанных дат. Он собирает посты, определяет, являются ли они оригинальными или репостами, и получает количество просмотров для каждого поста. Собранные данные экспортируются в CSV-файл для удобного доступа и анализа.

## Features

- Connects to specified Telegram channels.
- Fetches posts based on user-defined dates.
- Identifies whether each post is an original or a repost.
- Retrieves the view count for each post.
- Exports the collected data to a CSV file.

## Project Structure

```
telegram-post-parser-bot
├── src
│   ├── bot.py            # Main logic for the Telegram bot
│   ├── parser.py         # Handles post fetching and parsing
│   ├── csv_exporter.py   # Exports parsed data to CSV
│   └── utils.py          # Utility functions
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd telegram-post-parser-bot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Создайте файл `.env` в корне проекта и добавьте ваш Telegram Bot API токен:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   ```

2. Убедитесь, что все зависимости установлены:
   ```
   pip install -r requirements.txt
   ```

3. Запустите бота:
   ```
   python src/bot.py
   ```

3. Interact with the bot in Telegram to specify the channels and dates for parsing posts.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
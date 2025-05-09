def format_date(date):
    from datetime import datetime
    return datetime.strptime(date, "%Y-%m-%d").date()

def log_message(message):
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(message)

def validate_date(date):
    from datetime import datetime
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except ValueError:
        return False
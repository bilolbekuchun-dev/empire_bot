import logging
import re
from logging.handlers import RotatingFileHandler

# Necha soniyadan oshsa "sekin" deb hisoblasin? (masalan 0.4 soniya)
SLOW_QUERY_THRESHOLD = 0.4

class SlowQueryFilter(logging.Filter):
    """
    Tortoise log xabaridan (0.0012s) ko'rinishidagi vaqtni ajratib olib,
    faqat sekinlarini o'tkazuvchi filtr.
    """
    def filter(self, record):
        message = record.getMessage()
        # Tortoise log formati: "(0.000123s) SELECT ..."
        # Muntazam ifoda yordamida qavs ichidagi vaqtni olamiz
        match = re.search(r"\((\d+\.\d+)s\)", message)
        
        if match:
            duration = float(match.group(1))
            return duration >= SLOW_QUERY_THRESHOLD
        
        return False

def setup_db_logging():
    # 1. Tortoise DB loggerini olish
    logger = logging.getLogger("tortoise.db_client")
    logger.setLevel(logging.DEBUG)

    # 2. Faylga yozuvchi handler
    file_handler = RotatingFileHandler(
        "slow_queries.log", 
        maxBytes=10*1024*1024, # 10 MB
        backupCount=5, 
        encoding="utf-8"
    )

    # 3. Formatni sozlash (Vaqt va SQL xabarining o'zi)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    file_handler.setFormatter(formatter)

    # 4. Sekin so'rovlar filtrini qo'shish
    slow_filter = SlowQueryFilter()
    file_handler.addFilter(slow_filter)

    # 5. Handlerni loggerga ulaymiz
    if not logger.handlers:
        logger.addHandler(file_handler)
        
    print(f"INFO: Database profiling yoqildi. Threshold: {SLOW_QUERY_THRESHOLD}s")
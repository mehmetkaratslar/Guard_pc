# guard_pc_app/utils/logger.py
import logging
import sys
import os
from datetime import datetime

def setup_logger():
    """
    Loglama sistemini yapılandırır.
    
    Özellikler:
    - Konsolda ve dosyada loglama
    - Tarih/saat formatı
    - Renkli log seviyeleri (konsol)
    - Log dosyası otomatik rotasyonu
    """
    # Temel loglama formatı
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Root logger'ı yapılandır
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Ana seviye
    
    # Tüm handler'ları temizle
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Konsol çıktısı
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Encoding hatalarını ele alma
    console_handler.setFormatter(
        logging.Formatter(log_format, date_format)
    )
    
    logger.addHandler(console_handler)
    
    # Dosya çıktısı
    try:
        # Logs klasörü oluştur
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Şimdiki tarih ve saat
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"guard_{current_time}.log")
        
        # Dosya handler'ı
        file_handler = logging.FileHandler(
            log_file, 
            mode='a',
            encoding='utf-8'  # UTF-8 kodlaması kullan
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(log_format, date_format)
        )
        
        logger.addHandler(file_handler)
        
    except Exception as e:
        print(f"Log dosyası oluşturulurken hata: {e}")
    
    # İlk log mesajı
    logging.info("Logger başlatıldı - Seviye: INFO")
    
    return logger
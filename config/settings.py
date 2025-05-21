# guard_pc_app/config/settings.py
import os

# Uygulama ayarları
APP_NAME = "Guard - Düşme Algılama Sistemi"
APP_VERSION = "1.0.0"

# Kamera ayarları
CAMERA_INDEX = 0  # Varsayılan kamera indeksi
FRAME_WIDTH = 640  # değiştirildi: 640x640 frame boyutu
FRAME_HEIGHT = 640  # değiştirildi: 640x640 frame boyutu
FRAME_RATE = 30

# YOLOv11 Ayarları
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "resources", 
    "models", 
    "fall_model.pt"  # YOLOv11 model dosyası
)
CONFIDENCE_THRESHOLD = 0.6  # YOLOv11 için güven eşiği

# API sunucusu ayarları
API_HOST = "127.0.0.1"
API_PORT = 8002

# Bildirim ayarları
EMAIL_SUBJECT = "Guard Uyarı: Düşme Algılandı!"
EMAIL_FROM = "mehmetkarataslar@gmail.com"
SMS_MESSAGE = "Guard Uyarı: Düşme Algılandı! Lütfen kontrol ediniz acil."
TELEGRAM_MESSAGE = "⚠️ *GUARD UYARI* ⚠️\nDüşme algılandı! Lütfen kontrol edin."

# Uygulama temaları
THEME_LIGHT = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f5f5f5",
    "bg_tertiary": "#e0e0e0",
    "text_primary": "#2c3e50",
    "text_secondary": "#7f8c8d",
    "accent_primary": "#3498db",  # Mavi
    "accent_secondary": "#2ecc71",  # Yeşil
    "accent_warning": "#f39c12",  # Turuncu
    "accent_danger": "#e74c3c",  # Kırmızı
    "border": "#dddddd"
}

THEME_DARK = {
    "bg_primary": "#1a1a1a",
    "bg_secondary": "#2d2d2d",
    "bg_tertiary": "#3d3d3d",
    "text_primary": "#ecf0f1",
    "text_secondary": "#bdc3c7",
    "accent_primary": "#3498db",  # Mavi
    "accent_secondary": "#2ecc71",  # Yeşil
    "accent_warning": "#f39c12",  # Turuncu
    "accent_danger": "#e74c3c",  # Kırmızı
    "border": "#555555"
}

# Varsayılan tema
DEFAULT_THEME = "light"  # "light" veya "dark"
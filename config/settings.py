# =======================================================================================
# 📄 Dosya Adı: settings.py
# 📁 Konum: guard_pc_app/config/settings.py
# 📌 Açıklama:
# Uygulama genel ayarlarını tanımlar.
# Çoklu kamera desteği için CAMERA_CONFIGS eklendi, CAMERA_INDEX kaldırıldı.
# Mevcut yapı, değişken isimleri ve diğer ayarlar korundu.
# 🔗 Bağlantılı Dosyalar:
# - core/camera.py: Kamera ayarları
# - ui/app.py: Tema ayarları
# - core/stream_server.py: API ayarları
# - core/notification.py: Bildirim ayarları
# =======================================================================================

import os
import cv2

# Uygulama ayarları
APP_NAME = "Guard - Düşme Algılama Sistemi"
APP_VERSION = "1.0.0"

# Kamera ayarları
CAMERA_CONFIGS = [
    {"index": 0, "backend": cv2.CAP_MSMF, "name": "Ana Kamera"},  # MSMF backend’li ana kamera
    {"index": 1, "backend": cv2.CAP_DSHOW, "name": "Harici Kamera"},  # DSHOW backend’li harici kamera
]  # Çoklu kamera yapılandırması
FRAME_WIDTH = 640  # 640x640 frame boyutu
FRAME_HEIGHT = 640  # 640x640 frame boyutu
FRAME_RATE = 30

# YOLOv11 Ayarları
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "resources", 
    "models", 
    "fall_model.pt"  # YOLOv11 model dosyası
)
CONFIDENCE_THRESHOLD = 0.50  # YOLOv11 için güven eşiği

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
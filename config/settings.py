# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: settings.py (GELİŞMİŞ UYGULAMA YAPILANDIRMALARI)
# Konum: guard_pc_app/config/settings.py
# Açıklama:
# Guard AI uygulamasında kullanılan tüm yapılandırma ayarlarını içeren dosyadır.
# AI modeli seçimleri, kamera kalitesi, güvenlik politikaları, ekran çözünürlüğü,
# gizlilik modu, veri saklama süreleri gibi temel yapılandırmalar burada tanımlanmıştır.

# === ÖZELLİKLER ===
# - AI modeli kalite/performans profilleri
# - Kamera kalitesi ve FPS ayarları
# - Güvenlik ve şifreleme yapılandırması
# - Eklenti ve API genişletme ayarları
# - Pose noktaları ve bağlantıları (YOLOv11-pose için)
# - DeepSORT takip algoritması parametreleri
# - Düşme algılama hassasiyeti ayarları

# === BAŞLICA BÖLÜMLER ===
# 1. AI MODELİ SEÇİM PROFİLLERİ
#    - Farklı hız/doğruluk dengesi sunar
#    - yolo11n-pose: En hızlı, düşük doğruluk (~6MB)
#    - yolo11s-pose: Hızlı, orta doğruluk (~22MB)
#    - yolo11m-pose: Dengeli hız ve iyi doğruluk (~52MB)
#    - yolo11l-pose: Yavaş, yüksek doğruluk (~110MB)
#    - yolo11x-pose: En yavaş, en yüksek doğruluk (~220MB)

# 2. KAMERA KALİTESİ AYARLARI
#    - Çözünürlük ve FPS ayarları
#    - low: 640x480 @ 15 FPS
#    - medium: 1280x720 @ 20 FPS
#    - high: 1920x1080 @ 25 FPS
#    - ultra: 3840x2160 @ 15 FPS

# 3. GÜVENLİK VE GİZLİLİK
#    - Saklanan verilerin şifrelenmesi
#    - Güvenli veri iletimi
#    - Veri saklama süresi (gün cinsinden)
#    - Otomatik eski olay silme
#    - Gizlilik modu (yüz blurlama)

# 4. EKLENTİ VE GENİŞLETME DESTEĞİ
#    - Eklenti desteği
#    - Özel model yükleme
#    - API genişletmeleri

# 5. POSE TANIMLARI (YOLOv11-pose)
#    - İnsan vücudundaki 17 farklı anatomik nokta
#    - Her noktanın isim, renk ve gösterilen adı var
#    - Bağlantılar (örn. omuz-diz, el-bilek) COCO formatında

# 6. DEEPSORT TRACKING PARAMETRELERİ
#    - max_age: Track'in kaybolma süresi (frame sayısı)
#    - n_init: Track onaylamak için gereken frame sayısı
#    - max_iou_distance: IOU mesafesi eşik değeri
#    - max_cosine_distance: Cosine mesafesi eşik değeri
#    - nn_budget: Max özellik vektörü sayısı
#    - max_feature_history: Özellik geçmişi uzunluğu

# 7. DÜŞME ALGILAMA PARAMETRELERİ
#    - confidence_threshold: Minimum güven skoru
#    - angle_threshold: Düşme açısı eşik değeri
#    - speed_threshold: Hareket hızı eşiği
#    - fall_duration: Sürekli düşme süresi (saniye)
#    - min_detection_interval: Aynı kişi için minimum tekrar algılama süresi

# === KULLANIM AMACI ===
# - Uygulamanın performansını optimize etmek
# - Kullanıcıya özelleştirme imkanı sunmak
# - Sistem kaynaklarının verimli kullanılmasını sağlamak
# - Gerçek zamanlı analizde doğru dengeyi kurmak

# === NOTLAR ===
# - Bu dosya, app.py, camera.py, dashboard.py ve detection.py ile entegre çalışır
# - Yapılandırma değerleri, ayarlar menüsünden kullanıcı tarafından değiştirilebilir
# - Varsayılan değerler test edilmiş senaryolara göre belirlenmiştir
# =======================================================================================

import os
import cv2
import numpy as np

# Uygulama ayarları
APP_NAME = "Guard AI - YOLOv11 Pose Düşme Algılama Sistemi"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "YOLOv11 Pose Estimation + DeepSORT tabanlı gelişmiş düşme algılama sistemi"

# Kamera ayarları
CAMERA_CONFIGS = [
    {"index": 0, "backend": cv2.CAP_DSHOW, "name": "Ana Kamera (DirectShow)"},
    {"index": 1, "backend": cv2.CAP_DSHOW, "name": "Harici Kamera 1 (DirectShow)"},
    {"index": 2, "backend": cv2.CAP_DSHOW, "name": "Harici Kamera 2 (DirectShow)"},
]

FRAME_WIDTH = 1080
FRAME_HEIGHT = 720
FRAME_RATE = 30     

# YOLOv11 Pose Estimation Ayarları
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "resources", 
    "models", 
    "yolo11l-pose.pt"  # YOLOv11 Large Pose model
)
CONFIDENCE_THRESHOLD = 0.50  # Genel tespit güven eşiği
POSE_CONFIDENCE_THRESHOLD = 0.30  # Pose keypoint güven eşiği
NMS_THRESHOLD = 0.45  # Non-Maximum Suppression eşiği

# YOLOv11 Model Seçenekleri
AVAILABLE_MODELS = {
    "yolo11n-pose": {
        "name": "YOLOv11 Nano Pose",
        "description": "En hızlı, düşük doğruluk",
        "size": "~10MB",
        "speed": "Çok Hızlı",
        "accuracy": "Düşük"
    },
    "yolo11s-pose": {
        "name": "YOLOv11 Small Pose", 
        "description": "Hızlı, orta doğruluk",
        "size": "~20MB",
        "speed": "Hızlı",
        "accuracy": "Orta"
    },
    "yolo11m-pose": {
        "name": "YOLOv11 Medium Pose",
        "description": "Dengeli hız ve doğruluk",
        "size": "~50MB", 
        "speed": "Orta",
        "accuracy": "İyi"
    },
    "yolo11l-pose": {
        "name": "YOLOv11 Large Pose",
        "description": "Yavaş, yüksek doğruluk (Önerilen)",
        "size": "~100MB",
        "speed": "Yavaş",
        "accuracy": "Yüksek"
    },
    "yolo11x-pose": {
        "name": "YOLOv11 Extra Large Pose",
        "description": "En yavaş, en yüksek doğruluk",
        "size": "~200MB",
        "speed": "Çok Yavaş", 
        "accuracy": "Çok Yüksek"
    }
}

# COCO Pose Keypoints (17 nokta)
POSE_KEYPOINTS = {
    0: {"name": "nose", "display": "Burun", "color": (255, 0, 0)},
    1: {"name": "left_eye", "display": "Sol Göz", "color": (255, 85, 0)},
    2: {"name": "right_eye", "display": "Sağ Göz", "color": (255, 170, 0)},
    3: {"name": "left_ear", "display": "Sol Kulak", "color": (255, 255, 0)},
    4: {"name": "right_ear", "display": "Sağ Kulak", "color": (170, 255, 0)},
    5: {"name": "left_shoulder", "display": "Sol Omuz", "color": (85, 255, 0)},
    6: {"name": "right_shoulder", "display": "Sağ Omuz", "color": (0, 255, 0)},
    7: {"name": "left_elbow", "display": "Sol Dirsek", "color": (0, 255, 85)},
    8: {"name": "right_elbow", "display": "Sağ Dirsek", "color": (0, 255, 170)},
    9: {"name": "left_wrist", "display": "Sol Bilek", "color": (0, 255, 255)},
    10: {"name": "right_wrist", "display": "Sağ Bilek", "color": (0, 170, 255)},
    11: {"name": "left_hip", "display": "Sol Kalça", "color": (0, 85, 255)},
    12: {"name": "right_hip", "display": "Sağ Kalça", "color": (0, 0, 255)},
    13: {"name": "left_knee", "display": "Sol Diz", "color": (85, 0, 255)},
    14: {"name": "right_knee", "display": "Sağ Diz", "color": (170, 0, 255)},
    15: {"name": "left_ankle", "display": "Sol Ayak Bileği", "color": (255, 0, 255)},
    16: {"name": "right_ankle", "display": "Sağ Ayak Bileği", "color": (255, 0, 170)}
}

# Pose Skeleton Bağlantıları (COCO format)
POSE_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],  # Bacaklar
    [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],         # Gövde ve kollar
    [8, 10], [9, 11], [6, 5], [5, 7], [1, 2],         # Kollar ve omuzlar
    [0, 1], [0, 2], [1, 3], [2, 4]                    # Baş
]

# DeepSORT Tracking Ayarları
DEEPSORT_CONFIG = {
    "max_age": 30,              # Track'in kaybolma süresi (frame)
    "n_init": 3,                # Track onaylanma için gerekli frame sayısı
    "max_iou_distance": 0.7,    # IOU mesafesi eşiği
    "max_cosine_distance": 0.4, # Cosine mesafesi eşiği
    "nn_budget": 100,           # Neural network budget
    "max_feature_history": 50   # Özellik geçmişi
}

# Düşme Algılama Parametreleri
FALL_DETECTION_CONFIG = {
    # DÜZELTME: Daha hassas eşikler
    "head_pelvis_ratio_threshold": 0.6,    # 0.8 -> 0.6 (daha hassas)
    "tilt_angle_threshold": 50,            # 45 -> 50 (sizin istediğiniz değer)
    "shoulder_hip_alignment_threshold": 40, # 30 -> 40 (daha toleranslı)
    
    # DÜZELTME: Daha hızlı response
    "continuity_frames": 3,                # 5 -> 3 (daha hızlı algılama)
    "min_detection_interval": 1.5,        # 5.0 -> 1.5 (daha sık kontrol)
    "max_detection_per_minute": 5,        # 3 -> 5 (daha fazla algılama)
    
    # DÜZELTME: Daha düşük kalite gereksinimleri
    "min_keypoints": 8,                    # 10 -> 8 (daha esnek)
    "min_keypoint_confidence": 0.25,      # 0.3 -> 0.25 (daha hassas)
    "min_pose_stability": 0.15,           # 0.2 -> 0.15 (daha toleranslı)
    
    # Diğer ayarlar aynı kalabilir
    "body_ratio_analysis": True,
    "temporal_analysis": True,
    "multi_frame_validation": True,
    "pose_sequence_analysis": True,
    
    "fall_type_weights": {
        "forward_fall": 0.4,
        "backward_fall": 0.3,
        "side_fall": 0.25,
        "sitting_fall": 0.05
    }
}

# Görselleştirme Ayarları
VISUALIZATION_CONFIG = {
    "show_pose_points": True,
    "show_pose_skeleton": True,
    "show_pose_labels": False,
    "pose_point_radius": 3,              # 4 -> 3 (performance)
    "pose_line_thickness": 2,
    
    "show_track_id": True,
    "show_confidence": True,
    "show_bounding_box": True,
    "bounding_box_thickness": 2,
    
    "fall_alert_color": (0, 0, 255),
    "normal_color": (0, 255, 0),
    "tracking_color": (255, 0, 0),
    "show_fall_overlay": True,
    "fall_text_size": 1.0,              # 1.2 -> 1.0 (performance)
    
    "camera_display_size": (1200, 800),  # Optimize boyut
    "ui_update_interval": 25,            # 33 -> 25 ms (~40 FPS)
    "stats_update_interval": 500,        # 1000 -> 500 ms (daha hızlı)
}

# API sunucusu ayarları
API_HOST = "127.0.0.1"
API_PORT = 8002
STREAM_PORT = 5000

# Performans Ayarları
# Performans Ayarları - DÜZELTME
PERFORMANCE_CONFIG = {
    "max_concurrent_detections": 3,
    "frame_skip_ratio": 1,               # 0 -> 1 (her frame'i işle)
    "gpu_acceleration": True,
    "multi_threading": True,
    "memory_optimization": True,
    "detection_queue_size": 3,           # 15 -> 3 (düşük latency)
    "camera_buffer_size": 1,             # Minimum buffer
    "display_fps_limit": 40,             # UI FPS limit
    "ai_detection_fps": 15,              # AI detection FPS (daha düşük)
}

# Bildirim ayarları
EMAIL_SUBJECT = "🚨 Guard AI: YOLOv11 Düşme Algıladı!"
EMAIL_FROM = "mehmetkarataslar@gmail.com"
SMS_MESSAGE = "🚨 Guard AI Uyarı: YOLOv11 ile düşme algılandı! Lütfen kontrol ediniz."
TELEGRAM_MESSAGE = "🚨 *GUARD AI UYARI* 🚨\nYOLOv11 Pose Estimation ile düşme algılandı!\n🤖 AI Güven Skoru ile doğrulandı."

# Gelişmiş bildirim şablonları
NOTIFICATION_TEMPLATES = {
    "email_html": """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">🤖 Guard AI - YOLOv11 Düşme Algılama</h2>
        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px;">
            <h3>📊 Algılama Detayları:</h3>
            <p><strong>🕐 Zaman:</strong> {timestamp}</p>
            <p><strong>📊 AI Güven Skoru:</strong> {confidence}%</p>
            <p><strong>🤸 Pose Analizi:</strong> {pose_analysis}</p>
            <p><strong>🎯 Takip ID:</strong> {track_id}</p>
            <p><strong>🧠 Model:</strong> YOLOv11 Pose Estimation</p>
        </div>
        <p style="color: #d32f2f; font-weight: bold;">⚠️ Lütfen durumu acilen kontrol edin!</p>
    </div>
    """,
    
    "telegram_detailed": """
🚨 *GUARD AI DÜŞME ALGILAMA* 🚨

🤖 *Model:* YOLOv11 Pose Estimation
🎯 *Takip ID:* {track_id}
📊 *AI Güven Skoru:* {confidence}%
🤸 *Pose Analizi:* {pose_analysis}
🕐 *Zaman:* {timestamp}
📍 *Kamera:* {camera_id}

⚠️ *Acil kontrol gerekli!*
""",
    
    "sms_short": "🚨 Guard AI: Düşme algılandı! AI Güven: {confidence}% | Zaman: {timestamp} | Kontrol edin!"
}

# Loglama Ayarları
LOGGING_CONFIG = {
    "level": "INFO",                      # Log seviyesi
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_logging": True,                 # Dosyaya loglama
    "console_logging": True,              # Konsola loglama
    "max_log_size": 10485760,            # 10MB maksimum log boyutu
    "backup_count": 5,                    # Yedek log dosyası sayısı
    "log_rotation": True,                 # Log rotasyonu
}

# Uygulama temaları
THEME_LIGHT = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f5f5f5", 
    "bg_tertiary": "#e0e0e0",
    "text_primary": "#2c3e50",
    "text_secondary": "#7f8c8d",
    "accent_primary": "#3498db",
    "accent_secondary": "#2ecc71",
    "accent_warning": "#f39c12",
    "accent_danger": "#e74c3c",
    "accent_ai": "#9b59b6",              # AI/ML vurgu rengi
    "border": "#dddddd",
    "pose_point": "#ff4081",             # Pose noktası rengi
    "skeleton_line": "#4caf50",          # Skeleton çizgi rengi
    "tracking_box": "#2196f3"            # Tracking kutu rengi
}

THEME_DARK = {
    "bg_primary": "#1a1a1a",
    "bg_secondary": "#2d2d2d",
    "bg_tertiary": "#3d3d3d", 
    "text_primary": "#ecf0f1",
    "text_secondary": "#bdc3c7",
    "accent_primary": "#3498db",
    "accent_secondary": "#2ecc71",
    "accent_warning": "#f39c12",
    "accent_danger": "#e74c3c",
    "accent_ai": "#bb86fc",              # AI/ML vurgu rengi (koyu tema)
    "border": "#555555",
    "pose_point": "#ff6ec7",             # Pose noktası rengi (koyu tema)
    "skeleton_line": "#81c784",          # Skeleton çizgi rengi (koyu tema)
    "tracking_box": "#64b5f6"            # Tracking kutu rengi (koyu tema)
}

# Varsayılan tema
DEFAULT_THEME = "light"

# Sistem gereksinimleri ve öneriler
SYSTEM_REQUIREMENTS = {
    "minimum": {
        "ram": "8GB",
        "cpu": "Intel i5 / AMD Ryzen 5",
        "gpu": "Entegre grafik (CPU işlem)",
        "storage": "2GB boş alan",
        "camera": "USB 2.0 kamera",
        "os": "Windows 10/11, macOS 10.15+, Ubuntu 18.04+"
    },
    "recommended": {
        "ram": "16GB+",
        "cpu": "Intel i7 / AMD Ryzen 7",
        "gpu": "NVIDIA RTX 3060+ (CUDA desteği)",
        "storage": "5GB+ SSD",
        "camera": "USB 3.0 HD kamera",
        "os": "Windows 11, macOS 12+, Ubuntu 20.04+"
    },
    "optimal": {
        "ram": "32GB+",
        "cpu": "Intel i9 / AMD Ryzen 9",
        "gpu": "NVIDIA RTX 4070+ (CUDA 11.8+)",
        "storage": "10GB+ NVMe SSD",
        "camera": "USB 3.0 4K kamera",
        "os": "Windows 11 Pro, macOS 13+, Ubuntu 22.04+"
    }
}

# Model performans profilleri
MODEL_PROFILES = {
    "ultra_fast": {
        "model": "yolo11n-pose.pt",
        "confidence": 0.6,
        "frame_skip": 2,
        "pose_points": False,
        "description": "En hızlı, düşük doğruluk"
    },
    "fast": {
        "model": "yolo11s-pose.pt", 
        "confidence": 0.55,
        "frame_skip": 1,
        "pose_points": True,
        "description": "Hızlı, orta doğruluk"
    },
    "balanced": {
        "model": "yolo11m-pose.pt",
        "confidence": 0.50,
        "frame_skip": 0,
        "pose_points": True, 
        "description": "Dengeli hız ve doğruluk"
    },
    "accurate": {
        "model": "yolo11l-pose.pt",
        "confidence": 0.45,
        "frame_skip": 0,
        "pose_points": True,
        "description": "Yüksek doğruluk (Önerilen)"
    },
    "ultra_accurate": {
        "model": "yolo11x-pose.pt",
        "confidence": 0.40,
        "frame_skip": 0,
        "pose_points": True,
        "description": "En yüksek doğruluk, yavaş"
    }
}

# Kamera kalitesi ayarları
CAMERA_QUALITY_PRESETS = {
    "low": {
        "width": 640,
        "height": 480,
        "fps": 15,
        "description": "Düşük kalite, hızlı işlem"
    },
    "medium": {
        "width": 1280,
        "height": 720,
        "fps": 25,
        "description": "Orta kalite, dengeli işlem (Önerilen)"
    },
    "high": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "description": "Yüksek kalite, yavaş işlem"
    },
    "ultra": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "description": "Ultra kalite"
    }
}

# Düşme algılama hassaslık seviyeleri
SENSITIVITY_LEVELS = {
    "low": {
        "head_pelvis_ratio": 0.9,
        "tilt_angle": 50,
        "continuity_frames": 8,
        "min_keypoints": 12,
        "description": "Düşük hassaslık, az false positive"
    },
    "medium": {
        "head_pelvis_ratio": 0.8,
        "tilt_angle": 45,
        "continuity_frames": 5,
        "min_keypoints": 10,
        "description": "Orta hassaslık, dengeli (Önerilen)"
    },
    "high": {
        "head_pelvis_ratio": 0.7,
        "tilt_angle": 40,
        "continuity_frames": 3,
        "min_keypoints": 8,
        "description": "Yüksek hassaslık, daha çok algılama"
    },
    "ultra": {
        "head_pelvis_ratio": 0.6,
        "tilt_angle": 35,
        "continuity_frames": 2,
        "min_keypoints": 6,
        "description": "Ultra hassaslık, çok false positive"
    }
}

# Hata kodları ve mesajları
ERROR_CODES = {
    "MODEL_LOAD_FAILED": {
        "code": 1001,
        "message": "YOLOv11 modeli yüklenemedi",
        "solution": "Model dosyasını kontrol edin ve yeniden indirin"
    },
    "CAMERA_NOT_FOUND": {
        "code": 1002, 
        "message": "Kamera bulunamadı",
        "solution": "Kamera bağlantısını kontrol edin"
    },
    "TRACKING_FAILED": {
        "code": 1003,
        "message": "DeepSORT tracking başlatılamadı", 
        "solution": "Tracking kütüphanesini yeniden yükleyin"
    },
    "POSE_DETECTION_FAILED": {
        "code": 1004,
        "message": "Pose detection başarısız",
        "solution": "Model dosyasını ve kamera kalitesini kontrol edin"
    },
    "INSUFFICIENT_RESOURCES": {
        "code": 1005,
        "message": "Yetersiz sistem kaynağı",
        "solution": "Daha düşük kalite ayarları kullanın"
    }
}

# Başarı mesajları
SUCCESS_MESSAGES = {
    "SYSTEM_STARTED": "🚀 Guard AI sistemi başarıyla başlatıldı",
    "MODEL_LOADED": "🧠 YOLOv11 modeli başarıyla yüklendi", 
    "TRACKING_ACTIVE": "🎯 DeepSORT tracking aktif",
    "FALL_DETECTED": "🚨 Düşme algılandı ve kaydedildi",
    "NOTIFICATION_SENT": "📧 Bildirimler başarıyla gönderildi"
}

# Geliştirici ve debug ayarları
DEBUG_CONFIG = {
    "show_fps": True,                     # FPS göstergesi
    "show_detection_time": True,          # Algılama süresi
    "show_model_info": True,              # Model bilgileri
    "show_memory_usage": False,           # Bellek kullanımı
    "save_debug_frames": False,           # Debug frame'leri kaydet
    "verbose_logging": False,             # Detaylı loglama
    "performance_profiling": False,       # Performans profilleme
}

# Güvenlik ve gizlilik ayarları
SECURITY_CONFIG = {
    "encrypt_stored_data": True,          # Saklanan verileri şifrele
    "secure_transmission": True,          # Güvenli veri iletimi
    "anonymize_tracking_data": False,     # Tracking verilerini anonimleştir
    "data_retention_days": 30,            # Veri saklama süresi (gün)
    "auto_delete_old_events": True,       # Eski olayları otomatik sil
    "privacy_mode": False,                # Gizlilik modu (yüzleri blur)
}

# Eklenti ve genişletme ayarları
EXTENSIONS_CONFIG = {
    "enable_plugins": False,              # Eklenti desteği
    "custom_models": False,               # Özel model desteği
    "api_extensions": False,              # API genişletmeleri
    "third_party_integrations": False,    # Üçüncü parti entegrasyonlar
}

# Backup ve kurtarma ayarları
BACKUP_CONFIG = {
    "auto_backup": True,                  # Otomatik yedekleme
    "backup_interval_hours": 24,          # Yedekleme aralığı (saat)
    "max_backup_files": 7,                # Maksimum yedek dosya sayısı
    "backup_location": "backups",         # Yedekleme konumu
    "include_model_files": False,         # Model dosyalarını dahil et
    "compress_backups": True,             # Yedekleri sıkıştır
}

# Ağ ve bağlantı ayarları
NETWORK_CONFIG = {
    "enable_remote_access": False,        # Uzaktan erişim
    "api_rate_limiting": True,            # API hız sınırı
    "cors_enabled": True,                 # CORS desteği
    "ssl_enabled": False,                 # SSL/TLS şifreleme
    "max_connections": 10,                # Maksimum bağlantı sayısı
    "timeout_seconds": 30,                # Bağlantı zaman aşımı
}

# Lisans ve telemetri ayarları
LICENSE_CONFIG = {
    "license_key": None,                  # Lisans anahtarı
    "telemetry_enabled": False,           # Telemetri verisi gönderimi
    "analytics_enabled": False,           # Analitik veri toplama
    "crash_reporting": True,              # Hata raporu gönderimi
    "usage_statistics": False,            # Kullanım istatistikleri
}

# Ses ve titreşim ayarları
AUDIO_CONFIG = {
    "enable_sound_alerts": True,          # Sesli uyarılar
    "alert_volume": 0.8,                  # Uyarı ses seviyesi (0.0-1.0)
    "sound_file_path": None,              # Özel ses dosyası yolu
    "text_to_speech": False,              # Metin okuma
    "voice_language": "tr-TR",            # Ses dili
}

# Gelişmiş AI ayarları
AI_ADVANCED_CONFIG = {
    "ensemble_models": False,             # Çoklu model kullanımı
    "model_uncertainty": True,            # Model belirsizlik analizi
    "active_learning": False,             # Aktif öğrenme
    "continual_learning": False,          # Sürekli öğrenme
    "federated_learning": False,          # Federasyon öğrenme
    "explainable_ai": True,               # Açıklanabilir AI
}

# Son güncelleme tarihi ve sürüm bilgileri
LAST_UPDATED = "2024-12-19"
VERSION_HISTORY = {
    "2.0.0": "YOLOv11 Pose Estimation + DeepSORT entegrasyonu",
    "1.0.0": "Temel YOLOv8 düşme algılama sistemi"
}



# =======================================================================================

# Akıcı kamera için optimize ayarlar
CAMERA_BUFFER_CONFIG = {
    "buffer_size": 1,                    # Tek frame buffer
    "capture_fps": 30,                   # Yakalama FPS
    "display_fps": 30,                   # Gösterim FPS
    "processing_fps": 10,                # AI işleme FPS (daha düşük)
    "frame_skip_display": 1,             # Display için frame atlama yok
    "frame_skip_ai": 3,                  # AI için her 3. frame
    "double_buffering": True,            # Çift buffer sistemi
    "direct_display": True,              # Doğrudan display güncelleme
}

# Mobil API ayarları  
MOBILE_API_CONFIG = {
    "enabled": True,
    "port": 5000,
    "host": "0.0.0.0",
    "cors_enabled": True,
    "max_clients": 5,
    "stream_timeout": 300,               # 5 dakika
    "quality_profiles": {
        "mobile_low": {"width": 320, "height": 240, "fps": 15, "quality": 60},
        "mobile_medium": {"width": 640, "height": 480, "fps": 20, "quality": 70},
        "mobile_high": {"width": 854, "height": 480, "fps": 25, "quality": 80}
    }
}

# Performance ayarları güncelle
PERFORMANCE_CONFIG = {
    "max_concurrent_detections": 3,
    "frame_skip_ratio": 0,               # Hiç frame atlama
    "gpu_acceleration": True,
    "multi_threading": True,
    "memory_optimization": True,
    "detection_queue_size": 1,           # Minimal queue
    "camera_buffer_size": 1,             # Tek frame buffer
    "display_fps_limit": 30,             # 30 FPS display
    "ai_detection_fps": 10,              # 10 FPS AI processing
    "mobile_stream_enabled": True,       # Mobil stream aktif
}


# Ek yardımcı fonksiyonlar için sabitler
CONSTANTS = {
    "PI": 3.14159265359,
    "GRAVITY": 9.81,                      # Yerçekimi ivmesi
    "HUMAN_HEIGHT_AVG": 170,              # Ortalama insan boyu (cm)
    "FALL_ACCELERATION_THRESHOLD": 15,    # Düşme ivme eşiği (m/s²)
    "MAX_HUMAN_SPEED": 12,                # Maksimum insan hızı (m/s)
}

# Konfigürasyon doğrulama
def validate_config():
    """Konfigürasyon ayarlarını doğrular."""
    errors = []
    
    # Model dosyası kontrolü
    if not os.path.exists(MODEL_PATH):
        errors.append(f"Model dosyası bulunamadı: {MODEL_PATH}")
    
    # Eşik değerleri kontrolü
    if not 0.1 <= CONFIDENCE_THRESHOLD <= 1.0:
        errors.append("CONFIDENCE_THRESHOLD 0.1-1.0 arasında olmalı")
    
    if not 0.1 <= POSE_CONFIDENCE_THRESHOLD <= 1.0:
        errors.append("POSE_CONFIDENCE_THRESHOLD 0.1-1.0 arasında olmalı")
    
    # Frame boyutu kontrolü
    if FRAME_WIDTH <= 0 or FRAME_HEIGHT <= 0:
        errors.append("Frame boyutları pozitif olmalı")
    
    # Port kontrolü
    if not 1024 <= API_PORT <= 65535:
        errors.append("API_PORT 1024-65535 arasında olmalı")
    
    return errors

# Konfigürasyon export fonksiyonu
def export_config():
    """Mevcut konfigürasyonu dictionary olarak döndürür."""
    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION
        },
        "model": {
            "path": MODEL_PATH,
            "confidence": CONFIDENCE_THRESHOLD,
            "pose_confidence": POSE_CONFIDENCE_THRESHOLD
        },
        "camera": {
            "configs": CAMERA_CONFIGS,
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "fps": FRAME_RATE
        },
        "tracking": DEEPSORT_CONFIG,
        "fall_detection": FALL_DETECTION_CONFIG,
        "visualization": VISUALIZATION_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "themes": {
            "light": THEME_LIGHT,
            "dark": THEME_DARK,
            "default": DEFAULT_THEME
        }
    }
# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: settings.py (ULTRA STABIL UYGULAMA YAPILANDIRMALARI - FIXED)
# Konum: guard_pc_app/config/settings.py
# Açıklama:
# Guard AI uygulamasında kullanılan tüm yapılandırma ayarlarını içeren dosyadır.
# Tüm stabilite sorunları çözülmüş, ultra stabil performans için optimize edilmiştir.

# === ÇÖZÜLEN SORUNLAR ===
# 1. Kamera görüntüsü gidip geliyor → Ultra stabil kamera ayarları
# 2. FPS dengesizliği → Sabit FPS kontrolü ve buffer optimizasyonu
# 3. İnsan tespiti başarısız → Düşük confidence threshold'ları
# 4. Düşme olayı algılanmıyor → Hassas fall detection parametreleri
# 5. Eklem noktaları görünmüyor → Yüksek keypoint visibility ayarları

# === YENİ ÖZELLİKLER ===
# - Ultra stabil kamera konfigürasyonu
# - Sabit FPS kontrolü (30 FPS)
# - Düşük confidence threshold'ları
# - Hassas fall detection
# - Yüksek keypoint visibility
# =======================================================================================

import os
import cv2
import numpy as np

# Uygulama ayarları
APP_NAME = "Guard AI - Ultra Stabil YOLOv11 Pose Düşme Algılama Sistemi"
APP_VERSION = "3.0.0"
APP_DESCRIPTION = "Ultra stabil YOLOv11 Pose Estimation + DeepSORT tabanlı gelişmiş düşme algılama sistemi"

# FIXED: Ultra stabil kamera ayarları
CAMERA_CONFIGS = [
    {"index": 0, "backend": cv2.CAP_DSHOW, "name": "Ana Kamera (Ultra Stabil)"},
    {"index": 1, "backend": cv2.CAP_DSHOW, "name": "Harici Kamera 1 (Ultra Stabil)"},
    {"index": 2, "backend": cv2.CAP_DSHOW, "name": "Harici Kamera 2 (Ultra Stabil)"},
]

# ULTRA OPTIMIZE: YOLOv11 optimize frame ayarları - 640x640 kare format
FRAME_WIDTH = 640
FRAME_HEIGHT = 640  # YOLOv11 için kare format
FRAME_RATE = 45  # ULTRA OPTIMIZE: Gerçekçi ve stabil FPS hedefi

# FIXED: Ultra stabil YOLOv11 Pose Estimation Ayarları
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "resources", 
    "models", 
    "yolo11l-pose.pt"  # YOLOv11 Large Pose model
)

# ULTRA OPTIMIZE: YOLOv11 640x640 için optimize threshold'lar
CONFIDENCE_THRESHOLD = 0.12  # ULTRA OPTIMIZE: Maksimum tespit için
POSE_CONFIDENCE_THRESHOLD = 0.10  # ULTRA OPTIMIZE: Minimum geçerli değer (0.1-1.0)
NMS_THRESHOLD = 0.5  # ULTRA OPTIMIZE: Optimal filtreleme
YOLO_INPUT_SIZE = (640, 640)  # ULTRA OPTIMIZE: YOLOv11 kare format
MIN_KEYPOINTS = 6  # ULTRA OPTIMIZE: Minimum keypoint sayısı

# FIXED: YOLOv11 Model Seçenekleri
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

# FIXED: Ultra görünür COCO Pose Keypoints (17 nokta)
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

# FIXED: Ultra stabil Pose Skeleton Bağlantıları (COCO format)
POSE_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],  # Bacaklar
    [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],         # Gövde ve kollar
    [8, 10], [9, 11], [6, 5], [5, 7], [1, 2],         # Kollar ve omuzlar
    [0, 1], [0, 2], [1, 3], [2, 4]                    # Baş
]

# FIXED: Ultra stabil DeepSORT Tracking Ayarları
DEEPSORT_CONFIG = {
    "max_age": 50,              # 30 -> 50 (daha uzun track)
    "n_init": 2,                # 3 -> 2 (daha hızlı onay)
    "max_iou_distance": 0.8,    # 0.7 -> 0.8 (daha toleranslı)
    "max_cosine_distance": 0.5, # 0.4 -> 0.5 (daha toleranslı)
    "nn_budget": 150,           # 100 -> 150 (daha fazla özellik)
    "max_feature_history": 75   # 50 -> 75 (daha uzun geçmiş)
}

# FIXED: DENGELI İNSAN ALGILLAMA - hem güvenilir hem algılayabilen
FALL_DETECTION_CONFIG = {
    # FIXED: DENGELI GÜVENİLİRLİK - insan algılaması + yanlış pozitif önleme
    "person_confidence_threshold": 0.4,       # 0.6 -> 0.4 (daha fazla insan algılar)
    "pose_confidence_threshold": 0.35,        # 0.5 -> 0.35 (daha fazla keypoint algılar)
    "min_keypoints_for_analysis": 7,          # 10 -> 7 (daha az keypoint yeterli)
    "min_critical_keypoints": 2,              # 3 -> 2 (daha esnek kritik keypoint)
    
    # FIXED: ANATOMIK DOĞRULAMA - insan vücut oranları (korundu)
    "min_bbox_width": 30,                    # Minimum bbox genişliği
    "min_bbox_height": 80,                   # Minimum bbox yüksekliği
    "max_bbox_width": 300,                   # Maksimum bbox genişliği
    "max_bbox_height": 500,                  # Maksimum bbox yüksekliği
    "min_aspect_ratio": 1.2,                 # 1.5 -> 1.2 (daha esnek oran)
    "max_aspect_ratio": 4.5,                 # 4.0 -> 4.5 (daha geniş oran)
    
    # FIXED: KATIL düşme algılama eşikleri - yanlış pozitif önleme
    "critical_tilt_angle": 60,               # Kritik eğim açısı (derece)
    "moderate_tilt_angle": 45,               # Orta risk eğim açısı
    "critical_height_ratio": 0.25,           # Kritik yükseklik kaybı oranı
    "moderate_height_ratio": 0.4,            # Orta risk yükseklik oranı
    "critical_width_height_ratio": 0.8,      # Kritik yatay pozisyon oranı
    "moderate_width_height_ratio": 0.6,      # Orta risk yatay pozisyon
    
    # FIXED: EKLEM AÇISI KONTROLLERI - insan fizyolojisi
    "min_elbow_angle": 10,                   # Minimum dirsek açısı
    "max_elbow_angle": 170,                  # Maksimum dirsek açısı
    "min_knee_angle": 20,                    # Minimum diz açısı
    "max_knee_angle": 185,                   # Maksimum diz açısı
    "critical_knee_angle": 45,               # Kritik diz açısı (düşme)
    "moderate_knee_angle": 60,               # Orta risk diz açısı
    
    # FIXED: SIMETRI KONTROLLERI - vücut hizalama
    "max_shoulder_asymmetry": 50,            # Maksimum omuz eğikliği (piksel)
    "max_hip_asymmetry": 40,                 # Maksimum kalça eğikliği
    "max_eye_asymmetry": 30,                 # Maksimum göz eğikliği
    "max_body_lateral_shift": 80,            # Maksimum yanal kayma
    
    # FIXED: DESTEK POZİSYONU - el yerde kontrolleri
    "critical_elbow_ground_distance": 60,    # Kritik dirsek-yer mesafesi
    "moderate_elbow_ground_distance": 100,   # Orta risk dirsek-yer mesafesi
    "critical_head_hip_diff": 40,            # Kritik baş-kalça farkı
    "moderate_head_hip_diff": 20,            # Orta risk baş-kalça farkı
    
    # FIXED: DÜŞME KARARI - çok yüksek eşikler
    "fall_score_threshold": 2.0,             # Minimum düşme skoru
    "min_diverse_indicators": 2,             # Minimum farklı indikatör sayısı
    "critical_indicator_weight": 1.0,        # Kritik indikatör ağırlığı
    "moderate_indicator_weight": 0.5,        # Orta risk indikatör ağırlığı
    
    # FIXED: SÜREKLİLİK VE İNTERVAL - spam önleme
    "continuity_frames": 5,                  # Süreklilik için frame sayısı
    "min_detection_interval": 3.0,          # Minimum algılama aralığı (saniye)
    "max_detection_per_minute": 3,          # Dakikada maksimum algılama
    "track_stability_frames": 10,           # Track stabilite frame sayısı
    
    # FIXED: KALITE KONTROLLERI - güvenilirlik
    "min_track_length": 8,                  # Minimum track uzunluğu
    "max_track_age": 120,                   # Maksimum track yaşı
    "pose_stability_threshold": 0.6,        # Pose stabilite eşiği
    "detection_confidence_boost": 0.1       # Sürekli detection confidence artışı
}

# Görselleştirme Ayarları - DÜZELTME: AKICI VIDEO + Keypoint'leri görünür yap
VISUALIZATION_CONFIG = {
    "show_pose_points": True,             # Mutlaka True
    "show_pose_skeleton": True,           # Mutlaka True
    "show_pose_labels": True,             # False -> True (label'ları göster)
    "pose_point_radius": 4,               # 5 -> 4 (biraz daha küçük - performans)
    "pose_line_thickness": 2,             # 3 -> 2 (daha ince - performans)
    
    "show_track_id": True,
    "show_confidence": True,
    "show_bounding_box": True,
    "bounding_box_thickness": 2,
    
    "fall_alert_color": (0, 0, 255),      # Kırmızı
    "normal_color": (0, 255, 0),          # Yeşil
    "tracking_color": (255, 255, 0),      # Sarı - daha görünür
    "pose_point_color": (255, 0, 255),    # Magenta - çok görünür
    "skeleton_color": (0, 255, 255),      # Cyan - çok görünür
    
    "show_fall_overlay": True,
    "fall_text_size": 1.2,               # 1.5 -> 1.2 (daha küçük - performans)
    
    "camera_display_size": (640, 640),    # YOLOv11 kare format
    "ui_update_interval": 8,              # ULTRA OPTIMIZE: 16 -> 8 ms (120 FPS UI)
    "stats_update_interval": 500,         # ULTRA OPTIMIZE: 1000 -> 500 ms (çok hızlı stats)
}

# API sunucusu ayarları
API_HOST = "127.0.0.1"
API_PORT = 8002
STREAM_PORT = 5000

# Performans Ayarları - DÜZELTME: YÜKSEK FPS için optimizasyon
PERFORMANCE_CONFIG = {
    "max_concurrent_detections": 2,       # 3 -> 2 (daha az CPU kullanımı)
    "frame_skip_ratio": 0,                # Her frame'i işle
    "gpu_acceleration": True,
    "multi_threading": True,
    "memory_optimization": True,
    "detection_queue_size": 1,            # Minimal latency
    "camera_buffer_size": 1,              # Minimum buffer
    "display_fps_limit": 60,              # 30 -> 60 (çok daha akıcı)
    "ai_detection_fps": 30,               # 20 -> 30 (daha hızlı AI)
    "mobile_stream_enabled": True,
    
    # YENİ: YÜKSEK FPS ayarları
    "video_buffer_size": 1,               # Minimum buffer
    "video_processing_threads": 3,        # 2 -> 3 (daha fazla paralel işlem)
    "frame_processing_timeout": 0.01,     # 0.02 -> 0.01 (daha hızlı timeout)
    "detection_interval": 0.02,           # 0.033 -> 0.02 (50 FPS detection)
    "ui_update_interval": 0.016,          # 0.025 -> 0.016 (60 FPS UI)
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

# Model Performans Profilleri - DÜZELTME: Hassas profil
MODEL_PROFILES = {
    "ultra_sensitive": {                  # YENİ: Test profili
        "model": "yolo11l-pose.pt",
        "confidence": 0.15,               # Çok düşük
        "frame_skip": 0,                  # Her frame
        "pose_points": True,
        "fall_threshold": 0.2,            # Çok hassas
        "description": "Ultra hassas test modu"
    },
    "balanced": {
        "model": "yolo11m-pose.pt",
        "confidence": 0.25,               # 0.50 -> 0.25
        "frame_skip": 0,
        "pose_points": True, 
        "fall_threshold": 0.3,            # Düşürüldü
        "description": "Dengeli hız ve hassaslık"
    },
    "accurate": {
        "model": "yolo11l-pose.pt",
        "confidence": 0.2,                # 0.45 -> 0.2
        "frame_skip": 0,
        "pose_points": True,
        "fall_threshold": 0.25,           # Düşürüldü
        "description": "Yüksek hassaslık (Önerilen)"
    }
}



# Kamera kalitesi ayarları
CAMERA_QUALITY_PRESETS = {
    "low": {
        "width": 416,
        "height": 416,
        "fps": 15,
        "description": "Düşük kalite, çok hızlı işlem - YOLOv11 uyumlu"
    },
    "medium": {
        "width": 640,
        "height": 640,
        "fps": 25,
        "description": "Orta kalite, dengeli işlem - YOLOv11 optimize (Önerilen)"
    },
    "high": {
        "width": 832,
        "height": 832,
        "fps": 30,
        "description": "Yüksek kalite, yavaş işlem - YOLOv11 uyumlu"
    },
    "ultra": {
        "width": 1280,
        "height": 1280,
        "fps": 30,
        "description": "Ultra kalite - YOLOv11 maksimum doğruluk"
    }
}

# Düşme algılama hassaslık seviyeleri - DÜZELTME: Ultra hassas seviye eklendi
SENSITIVITY_LEVELS = {
    "low": {                             # YENİ: Düşük hassasiyet - günlük kullanım
        "head_pelvis_ratio": 0.7,
        "tilt_angle": 60,
        "continuity_frames": 5,
        "min_keypoints": 10,
        "description": "Düşük hassaslık, günlük kullanım (önerilen)"
    },
    "medium": {
        "head_pelvis_ratio": 0.5,         # 0.6 -> 0.5
        "tilt_angle": 45,                 # 30 -> 45
        "continuity_frames": 3,           # 2 -> 3
        "min_keypoints": 8,               # 6 -> 8
        "description": "Orta hassaslık, dengeli"
    },
    "high": {
        "head_pelvis_ratio": 0.3,         # 0.4 -> 0.3
        "tilt_angle": 30,                 # 20 -> 30
        "continuity_frames": 2,           # 1 -> 2
        "min_keypoints": 6,               # 4 -> 6
        "description": "Yüksek hassaslık, çok algılama"
    },
    "ultra": {                            # Test seviyesi - çok hassas
        "head_pelvis_ratio": 0.2,
        "tilt_angle": 20,
        "continuity_frames": 1,
        "min_keypoints": 4,
        "description": "Ultra hassaslık, test modu - sadece test için"
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

# Camera Buffer Config - DÜZELTME: Daha stabil
CAMERA_BUFFER_CONFIG = {
    "buffer_size": 2,                     # 1 -> 2
    "capture_fps": 30,
    "display_fps": 25,                    # 30 -> 25 (stabil)
    "processing_fps": 15,                 # 10 -> 15 (daha hızlı AI)
    "frame_skip_display": 1,
    "frame_skip_ai": 2,                   # 3 -> 2 (daha sık AI)
    "double_buffering": True,
    "direct_display": True,
}

# TEST MODU - Geliştiriciler için
DEBUG_FALL_DETECTION = {
    "ultra_sensitive_mode": True,         # Test için ultra hassas mod
    "log_all_detections": True,          # Her algılamayı logla
    "show_debug_overlay": True,          # Debug bilgileri göster
    "force_fall_threshold": 0.2,        # Test için çok düşük threshold
    "disable_continuity_check": True,   # Süreklilik kontrolünü kapat
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

# Firebase ayarları
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBJJXJ-EFQhJmY-bKwJFnXlmnmkwxSyWJk",
    "authDomain": "guard-12345.firebaseapp.com",
    "projectId": "guard-12345",
    "storageBucket": "guard-12345.firebasestorage.app",
    "messagingSenderId": "584140094374",
    "appId": "1:584140094374:web:e8e8e8e8e8e8e8e8e8e8e8",
    "databaseURL": "https://guard-12345-default-rtdb.firebaseio.com",
    "measurementId": "G-Q69PDLQLSQ",
    "serviceAccountKey": "resources/firebase/serviceAccountKey.json",
    "use_local_storage": True  # Firebase Storage yerine yerel depolama kullan
}
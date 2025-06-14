# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: app.py (ENHANCED VERSION V3 - FIXED)
# Konum: guard_pc_app/ui/app.py
# Açıklama:
# Guard AI , gelişmiş yapay zeka destekli düşme tespiti yapan bir güvenlik/gözlem uygulamasıdır.
# Gerçek zamanlı kamera görüntülerinden insan figürlerinin takibi ve düşme riskinin analizi yapılır.
# Uygulama, kullanıcı dostu bir arayüz ile ayarların yapılandırılmasına,
# bildirimlerin gönderilmesine ve geçmiş olayların incelenmesine izin verir.

# === ÖZELLİKLER ===
# - Gelişmiş YOLOv11 tabanlı düşme tespiti (pose estimation)
# - Çoklu kamera desteği (USB/IP kameralar)
# - Gerçek zamanlı görselleştirme
# - Bildirim sistemi (E-posta, SMS, Mobil Push)
# - Ayarlar paneli (AI model seçimi, tema, kamera ayarları)
# - Geçmiş olay kayıtları ve ekran görüntüleri
# - Firebase entegrasyonu (kullanıcı kimlik doğrulama, veritabanı, depolama)
# - API sunucusu desteği (harici erişim için)

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - tkinter: Arayüz oluşturma (Login, Register, Dashboard, Settings, History)
# - OpenCV (cv2): Kamera görüntüsünü işleme
# - NumPy: Görsel ve matematiksel işlemler
# - Firebase: Kimlik doğrulama, veritabanı ve dosya saklama
# - threading: Arka plan işlemleri (algılama döngüsü, indirmeler)
# - logging: Sistemde oluşan tüm hatalar ve işlem kayıtları
# - datetime / time: Zaman damgası ve performans ölçümü
# - uuid: Olay ID'leri üretmek için
# - psutil: Bellek kullanımı izleme

# === SINIFLAR ===
# - GuardApp: Ana uygulama sınıfı (tk.Tk türemiştir)
#   - LoginFrame: Giriş ekranı
#   - RegisterFrame: Kayıt ekranı
#   - DashboardFrame: Ana kontrol paneli (kamera akışı, durum bilgileri)
#   - SettingsFrame: Gelişmiş ayarlar (bu dosyada ayrı bir sınıf olarak tanımlanmıştır)
#   - HistoryFrame: Geçmiş düşme olaylarını gösteren arayüz

# === TEMEL FONKSİYONLAR ===
# - __init__: Uygulamayı başlatır, UI bileşenlerini oluşturur, Firebase servislerini kurar
# - _setup_enhanced_styles: UI stilleri ve renk temasını yönetir
# - _setup_firebase: Firebase kimlik doğrulama, veritabanı ve depolama bağlantılarını sağlar
# - _setup_advanced_fall_detection: Düşme algılama motorunu başlatır (YOLO + pose analiz)
# - start_enhanced_detection: Kamerayı başlatır ve düşme algılamaya başlar
# - stop_enhanced_detection: Kamerayı ve algılamayı durdurur
# - _enhanced_detection_loop: Her kamera için çalışan gerçek zamanlı algılama döngüsü
# - _handle_enhanced_fall_detection: Düşme algılandığında bildirim gönderir, veritabanına kaydeder
# - show_login / show_register / show_dashboard / show_settings / show_history: UI geçiş fonksiyonları
# - switch_ai_model: AI modelini değiştirme
# - logout: Kullanıcının çıkış yapması
# - _on_enhanced_close: Uygulama kapatıldığında temizlik işlemleri

# === MODEL YÖNETİMİ ===
# - AI model dizini: resources/models/
# - Desteklenen modeller:
#   - yolo11n-pose: En hızlı, düşük doğruluk (~6MB)
#   - yolo11s-pose: Hızlı, orta doğruluk (~22MB)
#   - yolo11m-pose: Orta hız ve iyi doğruluk (~52MB)
#   - yolo11l-pose: Yavaş, yüksek doğruluk (~110MB)
#   - yolo11x-pose: En yavaş, en yüksek doğruluk (~220MB)

# === BİLDİRİM MEKANİZMASI ===
# - E-posta bildirimi
# - SMS bildirimi (telefon numarası girilirse)
# - Mobil push bildirimi (Firebase Cloud Messaging ile)

# === VERİTABANI İŞLEMLERİ ===
# - Kullanıcı girişi ve kayıt işlemleri Firebase Auth üzerinden yapılır
# - Ayarlar, kullanıcı bilgileri ve düşme olayları Firestore üzerinde saklanır
# - Ekran görüntüleri Firebase Storage'a yüklenir

# === PERFORMANS İZLEME ===
# - Ortalama FPS
# - Toplam frame sayısı
# - Bellek kullanımı (psutil kullanılarak)
# - Çalışma süresi (uptime)

# === GÜVENLİ KAPATMA ===
# - Kamera akışlarını durdurma
# - AI modeli temizliği
# - Sonuçları loglama

# === TEST ÇALIŞTIRMA ===
# - `if __name__ == "__main__":` bloğu ile uygulama bağımsız çalıştırılabilir
# - Test için mock database bağlantısı ya da gerçek Firebase yapılandırması yapılabilir

# === GERİ DÖNÜŞ MEKANİZMASI ===
# - Ayarlardan çıkarken değişiklik varsa uyarı verilir
# - Bildirim gönderildikten sonra dashboard güncellenir

# === HATA YÖNETİMİ ===
# - Tüm işlemlerde try-except bloklarıyla hatalar loglanır
# - Kullanıcıya anlamlı mesajlar gösterilir
# - Hatalı işlemlerden sonra sistem güvenli şekilde devam eder veya durur

# === DOSYA LOGGING ===
# - Günlük aktiviteler bir log dosyasına yazılır (guard_ai_v3.log)
# - Log formatı: Tarih/Zaman [Seviye] Mesaj
# =======================================================================================

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import time
import os
import sys
import traceback
from typing import Optional, Dict, Any
import uuid
import cv2
import numpy as np
from datetime import datetime, timedelta

# UI Components
from ui.login import LoginFrame
from ui.register import RegisterFrame
from ui.dashboard import DashboardFrame
from ui.settings import SettingsFrame
from ui.history import HistoryFrame

# Configuration
from config.firebase_config import FIREBASE_CONFIG

from config.settings import THEME_LIGHT, THEME_DARK, DEFAULT_THEME, CAMERA_CONFIGS
# Services
from utils.auth import FirebaseAuth
from data.database import FirestoreManager
from data.storage import StorageManager
from core.camera import Camera
from core.fall_detection import FallDetector
from core.notification import NotificationManager
from core.stream_server import run_api_server_in_thread

class GuardApp:
    """gelişmiş ana uygulama sınıfı - AdvancedFallDetector entegrasyonu."""

    def __init__(self, root: tk.Tk):
        """
        Args:
            root (tk.Tk): Tkinter kök penceresi
        """
        self.root = root
        self.root.title("Guard AI -  Enhanced Fall Detection System v3.0")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.configure(bg="#f5f5f5")

        # App metadata
        self.app_version = "3.0.0"
        self.app_name = "Guard AI "
        self.build_date = "2025-06-06"
        
        # Tema durumu
        self.current_theme = DEFAULT_THEME

        # Enhanced sistem durumu
        self.system_state = {
            'running': False,
            'cameras_active': 0,
            'detection_active': False,
            'ai_model_loaded': False,
            'current_model': None,
            'session_start': None,
            'total_detections': 0,
            'fall_events': 0,
            'last_activity': None
        }
        
        # Fall event processing lock - aynı anda birden fazla event işlenmesini önler
        self.fall_event_lock = threading.Lock()
        self.last_fall_event_time = 0
        self.min_fall_event_interval = 5.0  # 5 saniye

        # Stiller
        self._setup_enhanced_styles()

        # Firebase servisleri
        self._setup_firebase()

        # gelişmiş düşme algılama sistemi
        self._setup_advanced_fall_detection()

        # Enhanced API sunucusu
        self.api_thread = run_api_server_in_thread()

        # Performance monitoring
        self.performance_monitor = {
            'start_time': time.time(),
            'frame_count': 0,
            'detection_time_total': 0.0,
            'avg_fps': 0.0,
            'memory_usage': 0.0
        }

        # Çıkış planı
        self.root.protocol("WM_DELETE_WINDOW", self._on_enhanced_close)

        # Enhanced UI bileşenleri
        self._create_enhanced_ui()

        # Background monitoring
        self._start_background_monitoring()

    def _setup_enhanced_styles(self):
        """Gelişmiş Tkinter stillerini ayarlar."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        theme = THEME_LIGHT if self.current_theme == "light" else THEME_DARK

        # Enhanced color palette
        self.colors = {
            'primary': theme["accent_primary"],
            'secondary': theme["accent_secondary"],
            'success': "#28a745",
            'danger': "#dc3545",
            'warning': "#ffc107",
            'info': "#17a2b8",
            'light': theme["bg_secondary"],
            'dark': theme["bg_primary"],
            'text_primary': theme["text_primary"],
            'text_secondary': "#6c757d",
            'border': "#dee2e6",
            'gradient_start': "#667eea",
            'gradient_end': "#764ba2"
        }

        # Enhanced style configurations
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), 
                           foreground=self.colors['primary'], padding=15)
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 12), 
                           foreground=self.colors['text_secondary'], padding=5)
        self.style.configure("Enhanced.TButton", font=("Segoe UI", 11, "bold"), 
                           padding=12, relief="flat")
        self.style.configure("Critical.TButton", font=("Segoe UI", 12, "bold"), 
                           padding=15, relief="flat")
        
        # Status indicators
        self.style.configure("Status.Running.TLabel", font=("Segoe UI", 11, "bold"), 
                           foreground=self.colors['success'])
        self.style.configure("Status.Stopped.TLabel", font=("Segoe UI", 11, "bold"), 
                           foreground=self.colors['danger'])
        self.style.configure("Status.Warning.TLabel", font=("Segoe UI", 11, "bold"), 
                           foreground=self.colors['warning'])

    def _setup_firebase(self):
        """Enhanced Firebase servisleri ayarlanır."""
        try:
            logging.info("🔥 Enhanced Firebase servisleri başlatılıyor...")
            
            self.auth = FirebaseAuth(FIREBASE_CONFIG)
            self.db_manager = FirestoreManager()
            self.storage_manager = StorageManager()
            self.notification_manager = None
            self.current_user = None
            self.detection_threads = {}
            
            logging.info("✅ Enhanced Firebase servisleri başarıyla başlatıldı")
            
        except Exception as e:
            logging.error(f"❌ Enhanced Firebase servisleri başlatılırken hata: {str(e)}")
            messagebox.showerror(
                "Bağlantı Hatası",
                f"Firebase servislerine bağlanılamadı.\n"
                f"Hata: {str(e)}\n"
                "Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin."
            )
            self.root.after(2000, self._show_enhanced_error_screen)

    def _setup_advanced_fall_detection(self):
        """gelişmiş düşme algılama sistemi ayarlanır."""
        try:
            logging.info("🤖 gelişmiş düşme algılama sistemi başlatılıyor...")
            
            # Enhanced kamera yönetimi
            self.cameras = []
            for config in CAMERA_CONFIGS:
                try:
                    camera = Camera(camera_index=config['index'], name=config['name'])
                    
                    # Enhanced camera validation
                    if hasattr(camera, '_validate_camera_with_fallback') and camera._validate_camera_with_fallback():
                        self.cameras.append(camera)
                        logging.info(f"✅ Kamera eklendi: {config['name']} "
                                   f"(indeks: {config['index']})")
                    else:
                        logging.warning(f"⚠️ Kamera {config['index']} başlatılamadı, listeye eklenmedi")
                        
                except Exception as e:
                    logging.error(f"❌ Kamera {config['index']} hatası: {str(e)}")
            
            # AdvancedFallDetector başlat
            try:
                # Default model ile başlat
                default_model = 'yolo11l-pose.pt'
                self.fall_detector = FallDetector.get_instance(default_model)
                
                model_info = self.fall_detector.get_enhanced_model_info()
                self.system_state['ai_model_loaded'] = model_info['model_loaded']
                self.system_state['current_model'] = model_info['model_name']
                
                logging.info("🎯 Enhanced Fall Detection Sistemi:")
                logging.info(f"   📦 Model: {model_info['model_name']}")
                logging.info(f"   ✅ Yüklü: {model_info['model_loaded']}")
                logging.info(f"   🖥️ Cihaz: {model_info['device']}")
                logging.info(f"   📊 Güven Eşiği: {model_info.get('fall_detection_params', {}).get('confidence_threshold', 'N/A')}")
                logging.info(f"   🎨 Keypoints: {model_info['keypoints_count']}")
                logging.info(f"   📈 Mevcut Modeller: {len(model_info['available_models'])}")
                
                if not model_info['model_loaded']:
                    logging.warning("⚠️ AI modeli yüklenemedi! Düşme algılama devre dışı olacak.")
                    messagebox.showwarning(
                        "AI Model Uyarısı",
                        f"AI düşme algılama modeli yüklenemedi.\n"
                        f"Model: {model_info['model_name']}\n"
                        "Sistem çalışacak ancak düşme algılama devre dışı olacak."
                    )
                else:
                    logging.info("✅ AI Model başarıyla yüklendi ve hazır!")
                
            except Exception as e:
                logging.error(f"❌ FallDetector başlatma hatası: {str(e)}")
                self.fall_detector = None
                self.system_state['ai_model_loaded'] = False
                
                messagebox.showerror(
                    "AI Model Hatası",
                    f"Gelişmiş düşme algılama sistemi başlatılamadı:\n{str(e)}\n"
                    "Uygulama çalışacak ancak AI özellikleri devre dışı olacak."
                )
            
            logging.info(f"📹 Toplam kamera sayısı: {len(self.cameras)}")
            logging.info(f"🤖 AI Model durumu: {'Aktif' if self.system_state['ai_model_loaded'] else 'Deaktif'}")
            
        except Exception as e:
            logging.error(f"❌ fall detection setup hatası: {str(e)}")
            self.fall_detector = None
            self.cameras = []
            self.system_state['ai_model_loaded'] = False

    def _start_background_monitoring(self):
        """Arka plan izleme thread'lerini başlat."""
        def monitoring_worker():
            while True:
                try:
                    # Performance monitoring
                    current_time = time.time()
                    uptime = current_time - self.performance_monitor['start_time']
                    
                    # Memory usage (basit hesaplama)
                    import psutil
                    process = psutil.Process()
                    self.performance_monitor['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
                    
                    # System state güncelle
                    if hasattr(self, 'fall_detector') and self.fall_detector:
                        try:
                            analytics = self.fall_detector.analytics.get_summary() if hasattr(self.fall_detector, 'analytics') else {}
                            self.system_state['total_detections'] = analytics.get('total_detections', 0)
                            self.system_state['fall_events'] = analytics.get('fall_events', 0)
                        except:
                            pass
                    
                    time.sleep(10)  # 10 saniyede bir güncelle
                    
                except Exception as e:
                    logging.error(f"Background monitoring hatası: {e}")
                    time.sleep(30)
        
        monitor_thread = threading.Thread(target=monitoring_worker, daemon=True)
        monitor_thread.start()
        logging.info("📊 Background monitoring başlatıldı")

    def _show_enhanced_error_screen(self):
        """Gelişmiş hata ekranını gösterir."""
        self._clear_content()
        error_frame = tk.Frame(self.content_frame, bg="#f8f9fa")
        error_frame.pack(fill=tk.BOTH, expand=True)

        # Error icon area
        icon_frame = tk.Frame(error_frame, bg="#f8f9fa")
        icon_frame.pack(pady=30)
        
        tk.Label(
            icon_frame,
            text="⚠️",
            font=("Segoe UI", 48),
            bg="#f8f9fa",
            fg="#dc3545"
        ).pack()

        tk.Label(
            error_frame,
            text="Bağlantı Hatası",
            font=("Segoe UI", 24, "bold"),
            fg="#dc3545",
            bg="#f8f9fa"
        ).pack(pady=10)

        tk.Label(
            error_frame,
            text="Firebase servislerine bağlanılamadı.\n"
                 "Lütfen internet bağlantınızı kontrol edin ve\n"
                 "uygulamayı yeniden başlatın.",
            font=("Segoe UI", 14),
            fg="#6c757d",
            bg="#f8f9fa",
            justify=tk.CENTER
        ).pack(pady=15)

        # Action buttons
        button_frame = tk.Frame(error_frame, bg="#f8f9fa")
        button_frame.pack(pady=20)

        tk.Button(
            button_frame,
            text="🔄 Yeniden Dene",
            command=self._retry_firebase_connection,
            font=("Segoe UI", 12, "bold"),
            bg="#28a745",
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            button_frame,
            text="❌ Uygulamayı Kapat",
            command=self.root.destroy,
            font=("Segoe UI", 12, "bold"),
            bg="#dc3545",
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)

    def _retry_firebase_connection(self):
        """Firebase bağlantısını yeniden dene."""
        try:
            self._setup_firebase()
            if hasattr(self, 'auth'):
                self.show_login()
                messagebox.showinfo("Başarı", "Firebase bağlantısı yeniden kuruldu!")
        except Exception as e:
            messagebox.showerror("Hata", f"Bağlantı yeniden kurulamadı:\n{str(e)}")

    def _create_enhanced_ui(self):
        """Enhanced UI bileşenleri oluşturulur."""
        self.main_frame = tk.Frame(self.root, bg="#f8f9fa", padx=15, pady=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.content_frame = tk.Frame(self.main_frame, bg="#f8f9fa")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.show_login()
        
        # Header frame oluştur ve API bilgisi butonunu ekle
        header_frame = tk.Frame(self.main_frame, bg="#f8f9fa")
        header_frame.pack(fill=tk.X, side=tk.TOP)
        api_btn = tk.Button(header_frame, text="📱 Mobil API", 
                        font=("Segoe UI", 12, "bold"),
                        bg="#17a2b8", fg="white", 
                        command=self.show_api_info)
        api_btn.pack(side=tk.RIGHT, padx=5)

    def show_login(self):
        """Enhanced giriş ekranını gösterir."""
        self._clear_content()
        self.login_frame = LoginFrame(
            self.content_frame,
            self.auth,
            self._on_enhanced_login_success,
            on_register_click=self.show_register
        )
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("🔐 Enhanced giriş ekranı gösterildi")

    def show_register(self):
        """Enhanced kayıt ekranını gösterir."""
        self._clear_content()
        self.register_frame = RegisterFrame(
            self.content_frame,
            self.auth,
            on_register_success=self.show_login,
            on_back_to_login=self.show_login
        )
        self.register_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("📝 Enhanced kayıt ekranı gösterildi")

    def show_dashboard(self):
        """ enhanced gösterge panelini gösterir."""
        self._clear_content()
        
        self.dashboard_frame = DashboardFrame(
            self.content_frame,
            self.current_user,
            self.cameras,
            self.start_enhanced_detection,
            self.stop_enhanced_detection,
            self.show_settings,
            self.show_history,
            self.logout
        )
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # Enhanced sistem durumu aktarma
        if self.system_state['running']:
            self.dashboard_frame.update_system_status(True)
            logging.info("📊 Enhanced Dashboard yeniden oluşturuldu - sistem durumu aktarıldı")
        
        logging.info("🖥️ Enhanced Dashboard ekranı gösterildi")

    def show_settings(self):
        """Enhanced ayarlar ekranını gösterir."""
        if hasattr(self, 'dashboard_frame'):
            try:
                self.dashboard_frame.on_destroy()
            except:
                pass
            self.dashboard_frame = None
            
        self._clear_content()
        
        # Enhanced settings frame with AI model management
        self.settings_frame = SettingsFrame(
            self.content_frame,
            self.current_user,
            self.db_manager,
            self.show_dashboard,
            fall_detector=self.fall_detector  # AI model yönetimi için
        )
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("⚙️ Enhanced Ayarlar ekranı gösterildi")

    def show_history(self):
        """Enhanced geçmiş olaylar ekranını gösterir."""
        if hasattr(self, 'dashboard_frame'):
            try:
                self.dashboard_frame.on_destroy()
            except:
                pass
            self.dashboard_frame = None
            
        self._clear_content()
        self.history_frame = HistoryFrame(
            self.content_frame,
            self.current_user,
            self.db_manager,
            self.show_dashboard
        )
        self.history_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("📜 Enhanced Geçmiş ekranı gösterildi")

    def _clear_content(self):
        """Enhanced içerik temizleme."""
        try:
            for widget in self.content_frame.winfo_children():
                try:
                    if hasattr(widget, 'on_destroy'):
                        widget.on_destroy()
                    widget.destroy()
                except Exception as e:
                    logging.warning(f"Widget temizleme hatası: {e}")
        except Exception as e:
            logging.error(f"Enhanced content temizleme hatası: {e}")

    def _on_enhanced_login_success(self, user):
        """Enhanced giriş başarılı callback."""
        try:
            self.current_user = user
            self.system_state['session_start'] = time.time()
            
            # User data management
            self.db_manager.update_last_login(user["localId"])
            user_data = self.db_manager.get_user_data(user["localId"])

            if not user_data:
                user_data = {
                    "email": user.get("email", ""),
                    "displayName": user.get("displayName", ""),
                    "lastLogin": time.time(),
                    "appVersion": self.app_version,
                    "preferences": {
                        "theme": self.current_theme,
                        "notifications": True,
                        "ai_model": self.system_state['current_model']
                    }
                }
                self.db_manager.create_new_user(user["localId"], user_data)
                user_data = self.db_manager.get_user_data(user["localId"])

            # Theme update
            if user_data and "settings" in user_data and "theme" in user_data["settings"]:
                if user_data["settings"]["theme"] != self.current_theme:
                    self.current_theme = user_data["settings"]["theme"]
                    self._setup_enhanced_styles()

            # DÜZELTME: Enhanced notification manager - boş user_data ile başlat
            try:
                self.notification_manager = NotificationManager.get_instance(user_data or {})
                logging.info("✅ NotificationManager başlatıldı")
            except Exception as notif_error:
                logging.error(f"❌ NotificationManager başlatma hatası: {notif_error}")
                # Basit fallback
                self.notification_manager = NotificationManager({})
            
            logging.info(f"✅ Enhanced login başarılı: {user.get('email', 'Unknown')}")
            logging.info(f"👤 User ID: {user['localId']}")
            logging.info(f"🎨 Tema: {self.current_theme}")
            logging.info(f"🔔 NotificationManager: {'Aktif' if self.notification_manager else 'Deaktif'}")
            
            self.show_dashboard()
            
        except Exception as e:
            logging.error(f"❌ Enhanced login success hatası: {str(e)}")
            messagebox.showerror("Login Hatası", f"Giriş işlemi tamamlanamadı:\n{str(e)}")



    def start_enhanced_detection(self):
            """
            DÜZELTME: Stabil detection başlatma - titreme yok
            """
            if self.system_state['running']:
                logging.warning("⚠️ Sistem zaten çalışıyor")
                if hasattr(self, 'dashboard_frame') and self.dashboard_frame:
                    self.dashboard_frame.update_system_status(True)
                return

            try:
                logging.info("🚀 Stabil Detection sistemi başlatılıyor...")
                
                # DÜZELTME: Kameraları doğal ayarlarla başlat
                camera_start_count = 0
                failed_cameras = []
                
                for i, camera in enumerate(self.cameras):
                    try:
                        logging.info(f"Kamera {camera.camera_index} başlatılıyor - doğal ayarlar...")
                        
                        # DÜZELTME: Hızlı validation
                        if hasattr(camera, '_validate_camera_with_fallback'):
                            if not camera._validate_camera_with_fallback():
                                logging.error(f"❌ Kamera {camera.camera_index} doğrulanamadı")
                                failed_cameras.append(camera.camera_index)
                                continue
                        
                        # DÜZELTME: Doğal ayarlarla başlat
                        if camera.start():
                            camera_start_count += 1
                            logging.info(f"✅ Kamera {camera.camera_index} başlatıldı - doğal kalite")
                            
                            # DÜZELTME: Kısa test
                            time.sleep(0.2)
                            test_frame = camera.get_frame()
                            if test_frame is not None and test_frame.size > 0:
                                logging.info(f"✅ Kamera {camera.camera_index} frame testi başarılı: {test_frame.shape}")
                            else:
                                logging.warning(f"⚠️ Kamera {camera.camera_index} frame testi başarısız")
                        else:
                            logging.error(f"❌ Kamera {camera.camera_index} başlatılamadı")
                            failed_cameras.append(camera.camera_index)
                            
                    except Exception as camera_error:
                        logging.error(f"❌ Kamera {camera.camera_index} başlatma hatası: {str(camera_error)}")
                        failed_cameras.append(camera.camera_index)

                # DÜZELTME: Sonuç değerlendirmesi
                if camera_start_count == 0:
                    error_msg = "Hiçbir kamera başlatılamadı!\n\n"
                    error_msg += "Başarısız kameralar:\n"
                    for cam_id in failed_cameras:
                        error_msg += f"• Kamera {cam_id}\n"
                    error_msg += "\nÖneriler:\n"
                    error_msg += "• Kamera bağlantılarını kontrol edin\n"
                    error_msg += "• Başka uygulamalar kamerayı kullanıyor olabilir\n"
                    error_msg += "• USB portlarını değiştirin\n"
                    error_msg += "• Bilgisayarı yeniden başlatın"
                    
                    messagebox.showerror("Kamera Hatası", error_msg)
                    return

                # DÜZELTME: Sistem durumunu güncelle
                self.system_state['running'] = True
                self.system_state['cameras_active'] = camera_start_count
                self.system_state['detection_active'] = self.system_state['ai_model_loaded']
                self.system_state['last_activity'] = time.time()
                
                # DÜZELTME: Stabil detection threads - daha az müdahale
                for camera in self.cameras:
                    if hasattr(camera, 'is_running') and camera.is_running:
                        camera_id = f"camera_{camera.camera_index}"
                        
                        if camera_id in self.detection_threads and self.detection_threads[camera_id].is_alive():
                            logging.warning(f"⚠️ Kamera {camera_id} detection thread zaten çalışıyor")
                        else:
                            self.detection_threads[camera_id] = threading.Thread(
                                target=self._stable_detection_loop,  # DÜZELTME: Stabil loop
                                args=(camera,),
                                daemon=True,
                                name=f"StableDetection-{camera_id}"
                            )
                            self.detection_threads[camera_id].start()
                            logging.info(f"🧵 Stabil detection thread başlatıldı: {camera_id}")

                # DÜZELTME: Dashboard güncelle
                if hasattr(self, "dashboard_frame") and self.dashboard_frame:
                    self.dashboard_frame.update_system_status(True)

                logging.info("✅ Stabil Detection sistemi başarıyla başlatıldı!")
                logging.info(f"📹 Aktif kameralar: {camera_start_count}/{len(self.cameras)}")
                logging.info(f"🤖 AI Algılama: {'Aktif' if self.system_state['detection_active'] else 'Deaktif'}")
                logging.info("🎨 Doğal kalite ayarları aktif")

            except Exception as e:
                logging.error(f"❌ Stabil detection başlatma hatası: {str(e)}")
                messagebox.showerror("Sistem Hatası", f"Stabil algılama sistemi başlatılamadı:\n{str(e)}")


    def _stable_detection_loop(self, camera):
            """
            stabil AI detection loop - tüm sorunlar çözülmüş
            
            Args:
                camera: İşlenecek kamera nesnesi
            """
            try:
                camera_id = f"camera_{camera.camera_index}"
                logging.info(f"🎥 stabil Detection Loop başlatıldı: {camera_id}")
                
                # stabil loop configuration
                config = {
                    'ai_process_interval': 10,  # Her 10. frame'de AI (daha az yük)
                    'max_errors': 25,
                    'min_detection_interval': 2.5,  # 2.5 saniye ara
                    'ai_enabled': self.system_state['ai_model_loaded']
                }
                
                # FIXED: Statistics
                stats = {
                    'frame_count': 0,
                    'detection_count': 0,
                    'fall_detection_count': 0,
                    'error_count': 0,
                    'session_start': time.time(),
                    'last_detection_time': 0
                }
                
                frame_counter = 0
                
                # FIXED: Model durumu kontrolü
                if not self.fall_detector or not config['ai_enabled']:
                    logging.warning(f"⚠️ {camera_id}: AI model yüklü değil, temel tracking modunda çalışıyor")
                
                while self.system_state['running']:
                    try:
                        # FIXED: Camera status check
                        if not camera or not hasattr(camera, 'is_running') or not camera.is_running:
                            time.sleep(0.5)
                            continue
                        
                        # stabil frame acquisition
                        frame = camera.get_frame()
                        if frame is None or frame.size == 0:
                            stats['error_count'] += 1
                            if stats['error_count'] % 25 == 0:
                                logging.warning(f"⚠️ {camera_id}: {stats['error_count']} frame hatası")
                            time.sleep(0.1)
                            continue
                        
                        stats['frame_count'] += 1
                        frame_counter += 1
                        
                        # FIXED: Stabil AI processing
                        if config['ai_enabled'] and self.fall_detector and (frame_counter % config['ai_process_interval'] == 0):
                            try:
                                #  stabil AI detection
                                if hasattr(self.fall_detector, 'get_detection_visualization'):
                                    annotated_frame, tracks = self.fall_detector.get_detection_visualization(frame)
                                else:
                                    annotated_frame, tracks = frame, []
                            except Exception as detection_error:
                                logging.error(f"❌ {camera_id} AI detection hatası: {detection_error}")
                                annotated_frame, tracks = frame, []
                            
                            # FIXED: Update detection count
                            if tracks:
                                stats['detection_count'] += len(tracks)
                                self.system_state['total_detections'] += len(tracks)
                                self.system_state['last_activity'] = time.time()
                            
                            #  stabil Fall Detection
                            try:
                                if hasattr(self.fall_detector, 'detect_fall'):
                                    is_fall, confidence, track_id = self.fall_detector.detect_fall(frame, tracks)
                                else:
                                    is_fall, confidence, track_id = False, 0.0, None
                            except Exception as fall_error:
                                logging.error(f"❌ {camera_id} fall detection hatası: {fall_error}")
                                is_fall, confidence, track_id = False, 0.0, None
                            
                            # FIXED: Dashboard'a annotated frame'i gönder - HER FRAME'DE
                            if hasattr(self, 'dashboard_frame') and self.dashboard_frame:
                                try:
                                    # Seçili kamera ise frame'i güncelle
                                    if camera.camera_index == self.dashboard_frame.selected_camera_index:
                                        self.dashboard_frame.update_ai_frame(annotated_frame)
                                except Exception as e:
                                    logging.debug(f"Dashboard frame update hatası: {e}")
                            
                            #  stabil fall event processing
                            current_time = time.time()
                            if (is_fall and confidence > 0.5 and  # Stabil threshold
                                (current_time - stats['last_detection_time']) > config['min_detection_interval']):
                                
                                stats['last_detection_time'] = current_time
                                stats['fall_detection_count'] += 1
                                self.system_state['fall_events'] += 1
                                
                                # stabil fall event processing
                                logging.warning(f"🚨 {camera_id} STABIL FALL DETECTED!")
                                logging.info(f"   📍 Track ID: {track_id}")
                                logging.info(f"   📊 Confidence: {confidence:.4f}")
                                
                                # FIXED: Thread-safe UI çağrısı
                                def handle_fall():
                                    try:
                                        result = self._handle_enhanced_fall_detection(
                                            annotated_frame, confidence, camera_id, track_id, None
                                        )
                                        logging.info(f"🎯 stabil fall handling result: {result}")
                                    except Exception as handle_error:
                                        logging.error(f"❌ Fall handling hatası: {handle_error}")
                                
                                # FIXED: UI thread'de çalıştır
                                self.root.after(0, handle_fall)
                        
                        # FIXED: Performance stats - daha az sıklıkla
                        if stats['frame_count'] % 300 == 0:  # 300 frame'de bir
                            self._log_ultra_stable_performance_stats(camera_id, stats)
                        
                        # ULTRA OPTIMIZE: Stabil timing - çok daha hızlı
                        time.sleep(0.005)  # 5ms = ~200 FPS theoretical max  # 0.025 -> 0.016 (60 FPS UI loop)
                        
                        # FIXED: Reset error count on success
                        stats['error_count'] = 0
                        
                    except Exception as inner_e:
                        stats['error_count'] += 1
                        logging.error(f"❌ {camera_id} ultra stabil detection inner hatası ({stats['error_count']}/{config['max_errors']}): {str(inner_e)}")
                        
                        if stats['error_count'] >= config['max_errors']:
                            logging.error(f"💥 {camera_id} maksimum hata sayısına ulaştı. Loop sonlandırılıyor.")
                            self.root.after(0, self.stop_enhanced_detection)
                            break
                        
                        time.sleep(1.0)
                
                # FIXED: Final statistics
                self._log_ultra_stable_session_summary(camera_id, stats)
                
            except Exception as e:
                logging.error(f"💥 {camera_id} Ultra stabil detection loop kritik hatası: {str(e)}")
                self.root.after(0, self.stop_enhanced_detection)
            finally:
                logging.info(f"🧹 {camera_id} ultra stabil detection thread temizlendi")

    def _log_ultra_stable_performance_stats(self, camera_id: str, stats: Dict):
            """Ultra stabil performans istatistiklerini logla."""
            try:
                current_time = time.time()
                elapsed_time = current_time - stats['session_start']
                
                avg_fps = stats['frame_count'] / elapsed_time if elapsed_time > 0 else 0
                detection_rate = (stats['detection_count'] / stats['frame_count'] 
                                if stats['frame_count'] > 0 else 0)
                
                logging.info(f"📊 {camera_id} Ultra Stabil Performance Stats:")
                logging.info(f"   🎬 Frames: {stats['frame_count']}")
                logging.info(f"   👥 Detections: {stats['detection_count']}")
                logging.info(f"   🚨 Fall Events: {stats['fall_detection_count']}")
                logging.info(f"   📈 Avg FPS: {avg_fps:.1f}")
                logging.info(f"   🎯 Detection Rate: {detection_rate:.3f}")
                logging.info(f"   ❌ Error Count: {stats['error_count']}")
                logging.info(f"   🎨 Ultra Stabil Quality: Aktif")
                
            except Exception as e:
                logging.error(f"Ultra stabil stats log hatası: {e}")
                
                
    def _log_ultra_stable_session_summary(self, camera_id: str, stats: Dict):
        """Ultra stabil session özeti logla."""
        total_time = time.time() - stats['session_start']
        avg_fps = stats['frame_count'] / total_time if total_time > 0 else 0
        
        logging.info(f"🏁 {camera_id} Ultra Stabil Session Summary:")
        logging.info(f"   ⏱️ Total Time: {total_time:.1f}s")
        logging.info(f"   🎬 Total Frames: {stats['frame_count']}")
        logging.info(f"   👥 Total Detections: {stats['detection_count']}")
        logging.info(f"   🚨 Fall Events: {stats['fall_detection_count']}")
        logging.info(f"   📊 Average FPS: {avg_fps:.1f}")
        logging.info(f"   ❌ Final Error Count: {stats['error_count']}")
        logging.info(f"   🎨 Ultra Stabil Quality: Korundu")

    def stop_enhanced_detection(self):
        """Ultra gelişmiş düşme algılama sistemini durdurur."""
        if not self.system_state['running']:
            logging.warning("⚠️ Sistem zaten durmuş durumda")
            if hasattr(self, 'dashboard_frame') and self.dashboard_frame:
                self.dashboard_frame.update_system_status(False)
            return

        try:
            logging.info("🛑 Ultra Enhanced Detection sistemi durduruluyor...")
            
            # Sistem durumunu güncelle
            self.system_state['running'] = False
            self.system_state['detection_active'] = False
            
            # Detection thread'lerini durdur
            for camera_id, thread in list(self.detection_threads.items()):
                if thread and thread.is_alive():
                    logging.info(f"🧵 Thread durduruluyor: {camera_id}")
                    thread.join(timeout=3.0)
                    if thread.is_alive():
                        logging.warning(f"⚠️ Thread zorla sonlandırıldı: {camera_id}")
                
                self.detection_threads[camera_id] = None
            
            self.detection_threads.clear()

            # Kameraları durdur
            stopped_cameras = 0
            for camera in self.cameras:
                try:
                    if hasattr(camera, 'is_running') and camera.is_running:
                        camera.stop()
                        stopped_cameras += 1
                        logging.info(f"✅ Kamera {camera.camera_index} durduruldu")
                except Exception as e:
                    logging.error(f"❌ Kamera {camera.camera_index} durdurma hatası: {str(e)}")

            self.system_state['cameras_active'] = 0

            # Dashboard güncelle
            if hasattr(self, "dashboard_frame") and self.dashboard_frame:
                self.dashboard_frame.update_system_status(False)

            logging.info("✅ Ultra Enhanced Detection sistemi başarıyla durduruldu!")
            logging.info(f"📹 Durdurulan kameralar: {stopped_cameras}")

        except Exception as e:
            logging.error(f"❌ Enhanced detection durdurma hatası: {str(e)}")

    def _enhanced_detection_loop(self, camera):
        """
        DÜZELTME: Ultra Enhanced AI düşme algılama döngüsü - Fixed version
        
        Args:
            camera: İşlenecek kamera nesnesi
        """
        try:
            camera_id = f"camera_{camera.camera_index}"
            logging.info(f"🎥 Enhanced Detection Loop başlatıldı: {camera_id}")
            
            # DÜZELTME: Loop configuration - daha düşük eşikler
            config = {
                'target_fps': 30,
                'max_errors': 15,
                'min_detection_interval': 2.0,  # DÜZELTME: 3 -> 2 saniye
                'performance_log_interval': 150,
                'ai_enabled': self.system_state['ai_model_loaded']
            }
            
            # Statistics
            stats = {
                'frame_count': 0,
                'detection_count': 0,
                'fall_detection_count': 0,
                'error_count': 0,
                'session_start': time.time(),
                'last_detection_time': 0,
                'total_processing_time': 0.0
            }
            
            frame_duration = 1.0 / config['target_fps']
            
            # Model durumu kontrolü
            if not self.fall_detector or not config['ai_enabled']:
                logging.warning(f"⚠️ {camera_id}: AI model yüklü değil, basit tracking modunda çalışıyor")
            
            while self.system_state['running']:
                loop_start = time.time()
                
                try:
                    # Camera status check
                    if not camera or not hasattr(camera, 'is_running') or not camera.is_running:
                        time.sleep(0.5)
                        continue
                    
                    # Frame acquisition
                    frame = camera.get_frame()
                    if frame is None or frame.size == 0:
                        stats['error_count'] += 1
                        if stats['error_count'] % 10 == 0:
                            logging.warning(f"⚠️ {camera_id}: {stats['error_count']} frame hatası")
                        time.sleep(0.1)
                        continue
                    
                    stats['frame_count'] += 1
                    processing_start = time.time()
                    
                    if config['ai_enabled'] and self.fall_detector:
                        # Enhanced AI Detection
                        try:
                            if hasattr(self.fall_detector, 'get_enhanced_detection_visualization'):
                                annotated_frame, tracks = self.fall_detector.get_enhanced_detection_visualization(frame)
                            else:
                                annotated_frame, tracks = self.fall_detector.get_detection_visualization(frame)
                        except Exception as detection_error:
                            logging.error(f"❌ {camera_id} AI detection hatası: {detection_error}")
                            annotated_frame, tracks = frame, []
                        
                        # Update detection count
                        if tracks:
                            stats['detection_count'] += len(tracks)
                            self.system_state['total_detections'] += len(tracks)
                            self.system_state['last_activity'] = time.time()
                        
                        # DÜZELTME: Enhanced Fall Detection - daha düşük threshold
                        try:
                            if hasattr(self.fall_detector, 'detect_enhanced_fall'):
                                fall_result = self.fall_detector.detect_enhanced_fall(frame, tracks)
                                is_fall, confidence, track_id = fall_result[0], fall_result[1], fall_result[2]
                                analysis_result = fall_result[3] if len(fall_result) > 3 else None
                            else:
                                is_fall, confidence, track_id = self.fall_detector.detect_fall(frame, tracks)
                                analysis_result = None
                        except Exception as fall_error:
                            logging.error(f"❌ {camera_id} fall detection hatası: {fall_error}")
                            is_fall, confidence, track_id, analysis_result = False, 0.0, None, None
                        
                        # DÜZELTME: DENGELI Fall event processing - güvenilir ama algılayabilen
                        current_time = time.time()
                        if (is_fall and confidence > 0.8 and  # DÜZELTME: 1.5 -> 0.8 (dengeli eşik)
                            (current_time - stats['last_detection_time']) > config['min_detection_interval']):
                            
                            # DÜZELTME: Ek doğrulama - track validation
                            if track_id is not None and self._validate_fall_track(track_id, confidence):
                                stats['last_detection_time'] = current_time
                                stats['fall_detection_count'] += 1
                                self.system_state['fall_events'] += 1
                                
                                # DÜZELTME: Enhanced fall event processing - UI thread güvenli çağrı
                                logging.warning(f"🚨 {camera_id} GELİŞMİŞ DOĞRULANMIŞ DÜŞME ALGILANDI!")
                                logging.info(f"   📍 Track ID: {track_id}")
                                logging.info(f"   📊 Confidence: {confidence:.4f}")
                                logging.info(f"   🔍 Track Validation: ✅")
                                if analysis_result:
                                    logging.info(f"   🎯 Fall Score: {analysis_result.fall_score:.3f}")
                                    logging.info(f"   🤸 Keypoint Quality: {analysis_result.keypoint_quality:.3f}")
                                    logging.info(f"   ⚠️ Risk Factors: {len(analysis_result.risk_factors)}")
                                
                                # DÜZELTME: Thread-safe UI çağrısı
                                def handle_fall():
                                    try:
                                        result = self._handle_enhanced_fall_detection(
                                            annotated_frame, confidence, camera_id, track_id, analysis_result
                                        )
                                        logging.info(f"🎯 stabil fall handling result: {result}")
                                    except Exception as handle_error:
                                        logging.error(f"❌ Fall handling hatası: {handle_error}")
                                        logging.error(f"📍 Traceback: {traceback.format_exc()}")
                                
                                # UI thread'de çalıştır
                                self.root.after(0, handle_fall)
                            else:
                                logging.debug(f"❌ Track validation failed for ID: {track_id}, confidence: {confidence:.3f}")
                        elif is_fall and confidence <= 1.5:
                            logging.debug(f"❌ Düşük confidence reddedildi: {confidence:.3f} <= 1.5")
                    
                    else:
                        # Basic detection mode (AI olmadan)
                        annotated_frame = frame
                        logging.debug(f"{camera_id}: Basic mode - AI disabled")
                    
                    # Processing time
                    processing_time = time.time() - processing_start
                    stats['total_processing_time'] += processing_time
                    
                    # Performance logging
                    if stats['frame_count'] % config['performance_log_interval'] == 0:
                        self._log_enhanced_performance_stats(camera_id, stats, config)
                    
                    # FPS control
                    elapsed_time = time.time() - loop_start
                    sleep_time = max(0, frame_duration - elapsed_time)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                    # Reset error count on success
                    stats['error_count'] = 0
                    
                except Exception as inner_e:
                    stats['error_count'] += 1
                    logging.error(f"❌ {camera_id} detection loop inner hatası ({stats['error_count']}/{config['max_errors']}): {str(inner_e)}")
                    
                    if stats['error_count'] >= config['max_errors']:
                        logging.error(f"💥 {camera_id} maksimum hata sayısına ulaştı. Loop sonlandırılıyor.")
                        self.root.after(0, self.stop_enhanced_detection)
                        break
                    
                    time.sleep(1.0)
            
            # Final statistics
            self._log_enhanced_session_summary(camera_id, stats)
            
        except Exception as e:
            logging.error(f"💥 {camera_id} Enhanced detection loop kritik hatası: {str(e)}")
            logging.error(f"📍 Traceback: {traceback.format_exc()}")
            self.root.after(0, self.stop_enhanced_detection)
        finally:
            # Thread cleanup işlemleri
            logging.info(f"🧹 {camera_id} detection thread temizlendi")

    def _log_enhanced_performance_stats(self, camera_id: str, stats: Dict, config: Dict):
        """Enhanced performans istatistiklerini logla."""
        try:
            current_time = time.time()
            elapsed_time = current_time - stats['session_start']
            
            avg_fps = stats['frame_count'] / elapsed_time if elapsed_time > 0 else 0
            avg_processing_time = (stats['total_processing_time'] / stats['frame_count'] 
                                 if stats['frame_count'] > 0 else 0)
            detection_rate = (stats['detection_count'] / stats['frame_count'] 
                            if stats['frame_count'] > 0 else 0)
            
            logging.info(f"📊 {camera_id} Enhanced Performance Stats:")
            logging.info(f"   🎬 Frames: {stats['frame_count']}")
            logging.info(f"   👥 Detections: {stats['detection_count']}")
            logging.info(f"   🚨 Fall Events: {stats['fall_detection_count']}")
            logging.info(f"   📈 Avg FPS: {avg_fps:.1f}")
            logging.info(f"   ⚡ Avg Processing: {avg_processing_time*1000:.1f}ms")
            logging.info(f"   🎯 Detection Rate: {detection_rate:.3f}")
            logging.info(f"   ❌ Error Count: {stats['error_count']}")
            
            # Performance monitoring güncelle
            self.performance_monitor['avg_fps'] = avg_fps
            self.performance_monitor['detection_time_total'] = stats['total_processing_time']
            self.performance_monitor['frame_count'] = stats['frame_count']
            
        except Exception as e:
            logging.error(f"Performance stats log hatası: {e}")

    def _log_enhanced_session_summary(self, camera_id: str, stats: Dict):
        """Enhanced session özeti logla."""
        total_time = time.time() - stats['session_start']
        avg_fps = stats['frame_count'] / total_time if total_time > 0 else 0
        
        logging.info(f"🏁 {camera_id} Enhanced Session Summary:")
        logging.info(f"   ⏱️ Total Time: {total_time:.1f}s")
        logging.info(f"   🎬 Total Frames: {stats['frame_count']}")
        logging.info(f"   👥 Total Detections: {stats['detection_count']}")
        logging.info(f"   🚨 Fall Events: {stats['fall_detection_count']}")
        logging.info(f"   📊 Average FPS: {avg_fps:.1f}")
        logging.info(f"   ❌ Final Error Count: {stats['error_count']}")

    def _handle_enhanced_fall_detection(self, screenshot: np.ndarray, confidence: float, 
                                      camera_id: str, track_id: int, analysis_result=None):
        """
        DÜZELTME: Enhanced düşme algılama event handler - Performance Optimized Version
        Sistem donmasını önleyen asenkron işlem mantığı.
        """
        # DÜZELTME: Performance optimized fall event handling
        current_time = time.time()
        
        # DÜZELTME: Çok sık düşme olaylarını önle (2 saniye minimum)
        if (current_time - self.last_fall_event_time) < 2.0:  # 3 -> 2 saniye (daha hızlı tepki)
            logging.info(f"⏳ Fall event rate limited: {current_time - self.last_fall_event_time:.1f}s < 2.0s")
            return {'event_saved': False, 'notification_sent': False, 'image_uploaded': False}
        
        # DÜZELTME: Instant non-blocking processing - asla beklemez
        if not self.fall_event_lock.acquire(blocking=False):
            logging.warning("🔒 Fall event processing busy, immediate background processing...")
            # DÜZELTME: Hızlı background processing
            threading.Thread(target=self._lightweight_fall_processing, 
                           args=(screenshot.copy() if screenshot is not None else None, 
                                confidence, camera_id, track_id, analysis_result),
                           daemon=True).start()
            return {'event_saved': False, 'notification_sent': False, 'image_uploaded': False}
        
        try:
            self.last_fall_event_time = current_time
            
            # DÜZELTME: Minimal logging - performans için
            logging.warning(f"🚨 FALL DETECTION: {camera_id}, conf={confidence:.3f}, id={track_id}")
            
            event_id = str(uuid.uuid4())
            
            # DÜZELTME: Asenkron processing - hızlı return
            # Screenshot'u kopyalayıp background'da işle
            screenshot_copy = screenshot.copy() if screenshot is not None else None
            
            # DÜZELTME: Hızlı response - tüm heavy operations background'da
            threading.Thread(target=self._async_fall_event_processing, 
                           args=(screenshot_copy, confidence, camera_id, track_id, 
                                analysis_result, event_id),
                           daemon=True).start()
            
            # DÜZELTME: Instant UI update - donmayı önler
            self._instant_ui_update(event_id, confidence, camera_id, track_id)
            
            logging.info(f"🎯 FALL EVENT QUEUED: {event_id} (async processing)")
            
            return {'event_saved': True, 'notification_sent': True, 'image_uploaded': True}

        except Exception as e:
            logging.error(f"💥 Fall detection handler error: {str(e)}")
            return {'event_saved': False, 'notification_sent': False, 'image_uploaded': False}
        finally:
            # Lock'u hemen release et
            self.fall_event_lock.release()

    def _async_fall_event_processing(self, screenshot, confidence, camera_id, track_id, analysis_result, event_id):
        """DÜZELTME: Asenkron fall event processing - UI thread'i bloklamaz."""
        try:
            logging.info(f"🔄 Async processing started: {event_id}")
            
            # Enhanced screenshot processing
            enhanced_screenshot = self._enhance_screenshot(screenshot, analysis_result, camera_id) if screenshot is not None else None
            
            # Storage upload - background'da
            image_url = None
            if enhanced_screenshot is not None:
                try:
                    if len(enhanced_screenshot.shape) == 3:
                        screenshot_rgb = cv2.cvtColor(enhanced_screenshot, cv2.COLOR_BGR2RGB)
                    else:
                        screenshot_rgb = enhanced_screenshot
                    
                    image_url = self.storage_manager.upload_screenshot(
                        screenshot_rgb, self.current_user["localId"], event_id
                    )
                    logging.info(f"✅ Async storage upload: {event_id}")
                except Exception as storage_error:
                    logging.error(f"❌ Async storage error: {storage_error}")
            
            # Model info al
            model_info = self.fall_detector.get_enhanced_model_info() if self.fall_detector else {}
            
            # Event data oluştur
            event_data = {
                "id": event_id,
                "user_id": self.current_user["localId"],
                "timestamp": time.time(),
                "confidence": float(confidence),
                "image_url": image_url,
                "detection_method": "AsyncFallDetector_v3",
                "camera_id": camera_id,
                "track_id": track_id,
                "model_info": {
                    "model_name": model_info.get("model_name", "Unknown"),
                    "model_version": "3.0",
                    "device": model_info.get("device", "unknown"),
                    "keypoints_count": model_info.get("keypoints_count", 17)
                },
                "enhanced_analysis": self._serialize_analysis_result(analysis_result) if analysis_result else {},
            }
            
            # Database save - background'da
            try:
                save_result = self.db_manager.save_fall_event(event_data)
                logging.info(f"✅ Async database save: {event_id} -> {save_result}")
            except Exception as db_error:
                logging.error(f"❌ Async database error: {db_error}")

            # Notification gönder - background'da
            if self.notification_manager:
                try:
                    user_data = self.db_manager.get_user_data(self.current_user["localId"])
                    if user_data:
                        self.notification_manager.update_user_data(user_data)
                    
                    notification_data = event_data.copy()
                    notification_data['test'] = False
                    
                    notification_result = self.notification_manager.send_notifications(
                        notification_data, enhanced_screenshot
                    )
                    logging.info(f"✅ Async notification: {event_id} -> {notification_result}")
                except Exception as notif_error:
                    logging.error(f"❌ Async notification error: {notif_error}")
            
            logging.info(f"✅ Async fall processing completed: {event_id}")
            
        except Exception as e:
            logging.error(f"💥 Async fall processing error: {e}")

    def _instant_ui_update(self, event_id, confidence, camera_id, track_id):
        """DÜZELTME: Anında UI güncellemesi - hiç beklemez."""
        try:
            if hasattr(self, "dashboard_frame") and self.dashboard_frame:
                def quick_update():
                    try:
                        if (hasattr(self.dashboard_frame, 'winfo_exists') and 
                            self.dashboard_frame.winfo_exists()):
                            # Hızlı event data
                            quick_event_data = {
                                'camera_id': camera_id,
                                'track_id': track_id,
                                'timestamp': time.time(),
                                'event_id': event_id
                            }
                            self.dashboard_frame.update_fall_detection(None, confidence, quick_event_data)
                            logging.info(f"✅ Instant UI update: {event_id}")
                    except Exception as ui_error:
                        logging.error(f"❌ Instant UI error: {ui_error}")
                
                # UI thread'inde hemen çalıştır
                self.root.after(0, quick_update)
        except Exception as e:
            logging.error(f"❌ Instant UI update error: {e}")

    def _delayed_fall_processing(self, screenshot, confidence, camera_id, track_id, analysis_result):
        """DÜZELTME: Gecikmeli düşme olayı işleme - sistem donmasını önler."""
        try:
            # 1 saniye bekle - sistem stabilize olsun
            time.sleep(1.0)
            
            # Lock mevcut mu kontrol et
            if self.fall_event_lock.acquire(blocking=True, timeout=5.0):
                try:
                    logging.info(f"🔄 Delayed fall processing started: {camera_id}")
                    result = self._handle_enhanced_fall_detection(
                        screenshot, confidence, camera_id, track_id, analysis_result
                    )
                    logging.info(f"🔄 Delayed fall processing completed: {result}")
                finally:
                    self.fall_event_lock.release()
            else:
                logging.warning("⚠️ Delayed fall processing timeout - skipping")
                
        except Exception as e:
            logging.error(f"💥 Delayed fall processing error: {e}")
    
    def _lightweight_fall_processing(self, screenshot, confidence, camera_id, track_id, analysis_result):
        """DÜZELTME: Hafif düşme olayı işleme - sistem donmasını önler."""
        try:
            # Öncelik sırasına göre hızlı işlem
            logging.info(f"⚡ Lightweight fall processing started: {camera_id}")
            
            # 1. Hızlı bildirim gönder (UI donmaması için)
            event_id = str(uuid.uuid4())
            
            # 2. Minimal event data
            minimal_event_data = {
                "id": event_id,
                "user_id": self.current_user["localId"] if self.current_user else "unknown",
                "timestamp": time.time(),
                "confidence": float(confidence),
                "camera_id": camera_id,
                "track_id": track_id,
                "processing_mode": "lightweight"
            }
            
            # 3. Dashboard hızlı güncelle
            if hasattr(self, "dashboard_frame") and self.dashboard_frame:
                def quick_dashboard_update():
                    try:
                        if (hasattr(self.dashboard_frame, 'winfo_exists') and 
                            self.dashboard_frame.winfo_exists()):
                            self.dashboard_frame.update_fall_detection(
                                screenshot, confidence, minimal_event_data
                            )
                            logging.info(f"⚡ Quick dashboard update: {event_id}")
                    except Exception as e:
                        logging.error(f"❌ Quick dashboard update error: {e}")
                
                self.root.after(0, quick_dashboard_update)
            
            # 4. Arka planda tam işleme
            time.sleep(0.5)  # Kısa gecikme ile tam işleme
            
            if self.fall_event_lock.acquire(blocking=True, timeout=2.0):
                try:
                    logging.info(f"🔄 Full processing started for: {event_id}")
                    # Tam işleme yap
                    result = self._handle_enhanced_fall_detection(
                        screenshot, confidence, camera_id, track_id, analysis_result
                    )
                    logging.info(f"✅ Lightweight processing completed: {result}")
                finally:
                    self.fall_event_lock.release()
            else:
                logging.warning(f"⏰ Full processing timeout for: {event_id}")
                
        except Exception as e:
            logging.error(f"💥 Lightweight fall processing error: {e}")
    
    def _add_minimal_fall_info(self, screenshot, fall_info):
        """DÜZELTME: Screenshot'a minimal düşme bilgisi ekler - performans optimized."""
        try:
            h, w = screenshot.shape[:2]
            
            # Minimal overlay - sadece gerekli bilgiler
            cv2.rectangle(screenshot, (0, 0), (300, 60), (0, 0, 255), -1)  # Kırmızı background
            
            cv2.putText(screenshot, "FALL DETECTED", (10, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            timestamp = datetime.datetime.fromtimestamp(fall_info['timestamp']).strftime('%H:%M:%S')
            cv2.putText(screenshot, f"Time: {timestamp}", (10, 45), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            confidence = fall_info.get('confidence', 0)
            cv2.putText(screenshot, f"Conf: {confidence:.2f}", (10, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                       
        except Exception as e:
            logging.error(f"Minimal fall info overlay error: {e}")
    
    def get_storage_manager(self):
        """DÜZELTME: Thread-safe storage manager getter."""
        if not hasattr(self, 'storage_manager') or self.storage_manager is None:
            try:
                from data.storage import StorageManager
                self.storage_manager = StorageManager()
                logging.info("✅ Storage manager initialized")
            except Exception as e:
                logging.error(f"❌ Storage manager initialization error: {e}")
                return None
        return self.storage_manager
    
    def get_db_manager(self):
        """DÜZELTME: Thread-safe database manager getter."""
        if not hasattr(self, 'db_manager') or self.db_manager is None:
            try:
                from data.database import FirestoreManager
                self.db_manager = FirestoreManager()
                logging.info("✅ Database manager initialized")
            except Exception as e:
                logging.error(f"❌ Database manager initialization error: {e}")
                return None
        return self.db_manager
    
    def get_notification_manager(self):
        """DÜZELTME: Thread-safe notification manager getter."""
        if not hasattr(self, 'notification_manager') or self.notification_manager is None:
            try:
                from core.notification import NotificationManager
                user_data = self.get_db_manager().get_user_data(self.current_user["localId"]) if self.current_user else None
                self.notification_manager = NotificationManager.get_instance(user_data)
                logging.info("✅ Notification manager initialized")
            except Exception as e:
                logging.error(f"❌ Notification manager initialization error: {e}")
                return None
        return self.notification_manager

    def _enhance_screenshot(self, screenshot: np.ndarray, analysis_result, camera_id: str) -> np.ndarray:
        """Screenshot'ı gelişmiş bilgilerle zenginleştir."""
        try:
            enhanced = screenshot.copy()
            h, w = enhanced.shape[:2]
            
            # Enhanced overlay background
            overlay = enhanced.copy()
            cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, enhanced, 0.3, 0, enhanced)
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # Enhanced header
            cv2.putText(enhanced, "GUARD AI v3.0 - ENHANCED FALL DETECTION", 
                       (10, 25), font, 0.7, (0, 255, 255), 2)
            
            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(enhanced, f"Time: {timestamp}", (10, 50), font, 0.6, (255, 255, 255), 1)
            
            # Camera info
            cv2.putText(enhanced, f"Camera: {camera_id}", (10, 75), font, 0.6, (255, 255, 255), 1)
            
            # Enhanced analysis info
            if analysis_result:
                cv2.putText(enhanced, f"Fall Score: {analysis_result.fall_score:.3f}", 
                           (300, 50), font, 0.6, (0, 0, 255), 2)
                cv2.putText(enhanced, f"Quality: {analysis_result.keypoint_quality:.3f}", 
                           (300, 75), font, 0.6, (255, 255, 0), 1)
                cv2.putText(enhanced, f"Risks: {len(analysis_result.risk_factors)}", 
                           (300, 100), font, 0.6, (255, 0, 255), 1)
            
            # App signature
            cv2.putText(enhanced, f"Guard AI v{self.app_version}", 
                       (w-150, h-10), font, 0.5, (128, 128, 128), 1)
            
            return enhanced
            
        except Exception as e:
            logging.error(f"Screenshot enhancement hatası: {e}")
            return screenshot

    def _serialize_analysis_result(self, analysis_result) -> Dict[str, Any]:
        """PoseAnalysisResult'ı serialize et."""
        try:
            if not analysis_result:
                return {}
            
            return {
                "is_fall": analysis_result.is_fall,
                "confidence": float(analysis_result.confidence),
                "fall_score": float(analysis_result.fall_score),
                "keypoint_quality": float(analysis_result.keypoint_quality),
                "pose_stability": float(analysis_result.pose_stability),
                "risk_factors": analysis_result.risk_factors,
                "timestamp": analysis_result.timestamp,
                "analysis_details": {
                    k: self._serialize_analysis_component(v) 
                    for k, v in analysis_result.analysis_details.items()
                }
            }
        except Exception as e:
            logging.error(f"Analysis result serialization hatası: {e}")
            return {"error": str(e)}

    def _serialize_analysis_component(self, component) -> Any:
        """Analysis component'ini serialize et."""
        try:
            if isinstance(component, dict):
                return {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                       for k, v in component.items()}
            elif isinstance(component, (int, float, np.number)):
                return float(component)
            elif isinstance(component, (list, tuple)):
                return [float(x) if isinstance(x, (int, float, np.number)) else x for x in component]
            else:
                return str(component)
        except:
            return str(component)

    def _create_enhanced_summary(self, analysis_result) -> str:
        """Enhanced özet oluştur."""
        if not analysis_result:
            return "Enhanced analiz mevcut değil"
        
        try:
            # Risk level
            risk_level = "YÜKSEK" if len(analysis_result.risk_factors) > 4 else \
                        "ORTA" if len(analysis_result.risk_factors) > 2 else "DÜŞÜK"
            
            # Quality assessment
            quality = "Mükemmel" if analysis_result.keypoint_quality > 0.8 else \
                     "İyi" if analysis_result.keypoint_quality > 0.6 else \
                     "Orta" if analysis_result.keypoint_quality > 0.4 else "Düşük"
            
            # Stability assessment
            stability = "Çok Kararlı" if analysis_result.pose_stability > 0.8 else \
                       "Kararlı" if analysis_result.pose_stability > 0.6 else \
                       "Orta" if analysis_result.pose_stability > 0.4 else "Kararsız"
            
            return (f"Enhanced AI Analizi: Risk {risk_level}, "
                   f"Kalite {quality}, Kararlılık {stability}, "
                   f"Skor {analysis_result.fall_score:.3f}")
            
        except Exception as e:
            return f"Enhanced özet hatası: {str(e)}"

    def _calculate_severity_level(self, analysis_result) -> str:
        """Severity level hesapla."""
        try:
            if not analysis_result:
                return "medium"
            
            score = analysis_result.fall_score
            risk_count = len(analysis_result.risk_factors)
            quality = analysis_result.keypoint_quality
            
            # Enhanced severity calculation
            if score > 0.9 and quality > 0.7:
                return "critical"
            elif score > 0.8 or risk_count > 5:
                return "high"
            elif score > 0.7 or risk_count > 3:
                return "medium"
            else:
                return "low"
                
        except Exception:
            return "medium"

    def _create_enhanced_display_summary(self, event_data: Dict, analysis_result) -> Dict[str, Any]:
        """Enhanced dashboard display summary."""
        try:
            base_summary = {
                'detection_method': 'Advanced AI v3.0',
                'tracking_method': 'Enhanced DeepSORT',
                'model_name': event_data.get('model_info', {}).get('model_name', 'Unknown'),
                'app_version': self.app_version,
                'timestamp_formatted': datetime.fromtimestamp(
                    event_data.get('timestamp', time.time())
                ).strftime('%H:%M:%S'),
                'uptime': f"{(time.time() - self.performance_monitor['start_time'])/60:.1f}m"
            }
            
            if analysis_result:
                base_summary.update({
                    'confidence_level': 'Kritik' if analysis_result.confidence > 0.9 else
                                      'Yüksek' if analysis_result.confidence > 0.7 else 'Orta',
                    'pose_quality': self._get_quality_description(analysis_result.keypoint_quality),
                    'fall_score': f"{analysis_result.fall_score:.3f}",
                    'risk_factors_count': len(analysis_result.risk_factors),
                    'severity': self._calculate_severity_level(analysis_result)
                })
            
            return base_summary
            
        except Exception as e:
            logging.error(f"Enhanced display summary hatası: {e}")
            return {'error': str(e)}

    def _get_quality_description(self, quality: float) -> str:
        """Kalite açıklaması."""
        if quality > 0.8:
            return "Mükemmel"
        elif quality > 0.6:
            return "İyi"
        elif quality > 0.4:
            return "Orta"
        else:
            return "Düşük"

    def logout(self):
        """Enhanced kullanıcı çıkışı."""
        try:
            logging.info("🚪 Enhanced logout başlatılıyor...")
            
            # Sistemi durdur
            if self.system_state['running']:
                self.stop_enhanced_detection()
            
            # Enhanced cleanup
            if hasattr(self, 'fall_detector') and self.fall_detector:
                try:
                    self.fall_detector.cleanup()
                except:
                    pass
            
            # Session bilgilerini temizle
            self.current_user = None
            self.notification_manager = None
            self.system_state['session_start'] = None
            
            # UI'ya dön
            self.show_login()
            
            logging.info("✅ Enhanced logout tamamlandı")
            
        except Exception as e:
            logging.error(f"❌ Enhanced logout hatası: {str(e)}")

    def switch_ai_model(self, model_name: str) -> bool:
        """AI modelini değiştir (SettingsFrame'den çağrılır)."""
        try:
            if not self.fall_detector:
                messagebox.showerror("Hata", "Fall detector başlatılmamış!")
                return False
            
            # Basit model switch - mevcut model path'i güncelle
            from config.settings import AVAILABLE_MODELS
            import os
            
            if model_name not in AVAILABLE_MODELS:
                messagebox.showerror("Hata", f"Geçersiz model: {model_name}")
                return False
            
            # Model dosyası var mı kontrol et
            model_dir = os.path.dirname(self.fall_detector.model_path)
            new_model_path = os.path.join(model_dir, f"{model_name}.pt")
            
            if not os.path.exists(new_model_path):
                messagebox.showerror("Hata", f"Model dosyası bulunamadı: {new_model_path}")
                return False
            
            # Sistemi durdur
            was_running = self.system_state['running']
            if was_running:
                self.stop_enhanced_detection()
            
            try:
                # Yeni model yükle
                from ultralytics import YOLO
                new_model = YOLO(new_model_path)
                
                # Eski modeli güncelle
                self.fall_detector.model = new_model
                self.fall_detector.model_path = new_model_path
                self.fall_detector.is_model_loaded = True
                
                # Sistem durumunu güncelle
                self.system_state['current_model'] = model_name
                self.system_state['ai_model_loaded'] = True
                
                # Sistemi tekrar başlat
                if was_running:
                    self.start_enhanced_detection()
                
                messagebox.showinfo("Başarı", f"Model başarıyla değiştirildi: {model_name}")
                logging.info(f"🔄 AI Model değiştirildi: {model_name}")
                return True
                
            except Exception as e:
                logging.error(f"Model yükleme hatası: {str(e)}")
                messagebox.showerror("Hata", f"Model yüklenemedi: {str(e)}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Model switch hatası: {str(e)}")
            messagebox.showerror("Hata", f"Model değiştirme hatası: {str(e)}")
            return False


    def get_system_status(self) -> Dict[str, Any]:
        """Enhanced sistem durumunu döndür."""
        try:
            uptime = time.time() - self.performance_monitor['start_time']
            
            return {
                'app_info': {
                    'name': self.app_name,
                    'version': self.app_version,
                    'build_date': self.build_date,
                    'uptime_seconds': uptime,
                    'uptime_formatted': f"{int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}"
                },
                'system_state': self.system_state.copy(),
                'performance': self.performance_monitor.copy(),
                'cameras': {
                    'total': len(self.cameras),
                    'active': self.system_state['cameras_active'],
                    'available_configs': len(CAMERA_CONFIGS)
                },
                'ai_model': {
                    'loaded': self.system_state['ai_model_loaded'],
                    'current': self.system_state['current_model'],
                    'available': list(self.fall_detector.available_models.keys()) if self.fall_detector else []
                }
            }
        except Exception as e:
            logging.error(f"System status hatası: {e}")
            return {'error': str(e)}



    def _on_enhanced_close(self):
        """Enhanced uygulama kapatma."""
        try:
            logging.info("🔚 Enhanced uygulama kapatılıyor...")
            
            # Sistem durdur
            if self.system_state['running']:
                self.stop_enhanced_detection()
            
            # Kameraları durdur
            for camera in self.cameras:
                try:
                    camera.stop()
                except:
                    pass
            
            # Enhanced cleanup
            if hasattr(self, 'fall_detector') and self.fall_detector:
                try:
                    self.fall_detector.cleanup()
                except:
                    pass
            
            # Final istatistikler
            total_uptime = time.time() - self.performance_monitor['start_time']
            logging.info(f"📊 Final Statistics:")
            logging.info(f"   ⏱️ Total Uptime: {total_uptime:.1f}s")
            logging.info(f"   👥 Total Detections: {self.system_state['total_detections']}")
            logging.info(f"   🚨 Fall Events: {self.system_state['fall_events']}")
            logging.info(f"   🎬 Processed Frames: {self.performance_monitor['frame_count']}")
            
            logging.info("✅ Enhanced Guard AI uygulaması güvenli şekilde kapatıldı")
            self.root.destroy()
            
        except Exception as e:
            logging.error(f"❌ Enhanced close hatası: {str(e)}")
            sys.exit(1)





    # =======================================================================================

    def get_api_server_info(self):
        """API server bilgilerini döndür - mobil için."""
        import socket
        
        # Local IP adresini bul
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        
        api_port = 5000  # stream_server.py'deki port
        
        return {
            "server_ip": local_ip,
            "api_port": api_port,
            "base_url": f"http://{local_ip}:{api_port}",
            "endpoints": {
                "mobile_cameras": f"http://{local_ip}:{api_port}/api/mobile/cameras",
                "mobile_health": f"http://{local_ip}:{api_port}/api/mobile/health",
                "mobile_server_info": f"http://{local_ip}:{api_port}/api/mobile/server/info",
                "stream_base": f"http://{local_ip}:{api_port}/mobile/stream"
            },
            "usage": {
                "camera_list": f"GET http://{local_ip}:{api_port}/api/mobile/cameras",
                "basic_stream": f"GET http://{local_ip}:{api_port}/mobile/stream/camera_0",
                "pose_stream": f"GET http://{local_ip}:{api_port}/mobile/stream/camera_0/pose",
                "detection_stream": f"GET http://{local_ip}:{api_port}/mobile/stream/camera_0/detection"
            }
        }

    # Dashboard'a API bilgisi gösterme butonu ekle
    def show_api_info(self):
        """API bilgilerini göster."""
        api_info = self.get_api_server_info()
        
        info_window = tk.Toplevel(self.root)
        info_window.title("📱 Mobil API Bilgileri")
        info_window.geometry("600x500")
        info_window.configure(bg="#f8f9fa")
        
        # Başlık
        title_label = tk.Label(info_window, text="📱 Mobil Canlı Yayın API'si", 
                            font=("Segoe UI", 16, "bold"),
                            bg="#f8f9fa", fg="#2c3e50")
        title_label.pack(pady=10)
        
        # Bilgi metni
        info_text = f"""
    🌐 Server IP: {api_info['server_ip']}
    🔌 Port: {api_info['api_port']}
    📡 Base URL: {api_info['base_url']}

    📱 MOBİL KULLANIM:

    1️⃣ Kamera Listesi:
    GET {api_info['endpoints']['mobile_cameras']}

    2️⃣ Canlı Yayın (Temel):
    {api_info['usage']['basic_stream']}

    3️⃣ Pose Detection Yayını:
    {api_info['usage']['pose_stream']}

    4️⃣ Düşme Algılama Yayını:
    {api_info['usage']['detection_stream']}

    5️⃣ Server Durumu:
    GET {api_info['endpoints']['mobile_health']}

    🔗 Mobil uygulamanızda bu URL'leri kullanın!
        """
        
        # Text widget
        text_widget = tk.Text(info_window, wrap=tk.WORD, font=("Consolas", 10),
                            bg="white", fg="#2c3e50", padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", info_text)
        text_widget.config(state=tk.DISABLED)
        
        # Kapat butonu
        close_btn = tk.Button(info_window, text="Kapat", font=("Segoe UI", 12),
                            bg="#dc3545", fg="white", command=info_window.destroy)
        close_btn.pack(pady=10)

    def _validate_fall_track(self, track_id: int, confidence: float) -> bool:
        """
        DÜZELTME: Track doğrulama - yanlış pozitif önleme
        """
        try:
            # Track stability kontrolü
            if not hasattr(self, 'track_validation_history'):
                self.track_validation_history = {}
            
            current_time = time.time()
            
            # Track history güncelle
            if track_id not in self.track_validation_history:
                self.track_validation_history[track_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'fall_detections': 1,
                    'max_confidence': confidence,
                    'validated': False
                }
                logging.debug(f"🆕 Yeni track kaydedildi: {track_id}")
                return False  # İlk görüşte hemen düşme algılama
            
            track_info = self.track_validation_history[track_id]
            track_info['last_seen'] = current_time
            track_info['fall_detections'] += 1
            track_info['max_confidence'] = max(track_info['max_confidence'], confidence)
            
            # Track yaşı kontrolü - en az 2 saniye takip edilmeli
            track_age = current_time - track_info['first_seen']
            if track_age < 2.0:
                logging.debug(f"❌ Track {track_id} çok genç: {track_age:.1f}s < 2.0s")
                return False
            
            # Confidence kontrolü - çok yüksek olmalı
            if confidence < 1.8:  # Çok yüksek eşik
                logging.debug(f"❌ Track {track_id} düşük confidence: {confidence:.3f} < 1.8")
                return False
            
            # Sürekli düşme algılaması kontrolü - spam önleme
            if track_info['fall_detections'] > 3:  # Maksimum 3 düşme algılaması
                logging.debug(f"❌ Track {track_id} çok fazla düşme: {track_info['fall_detections']} > 3")
                return False
            
            # DÜZELTME: Fall detector'dan ek doğrulama al
            if self.fall_detector and hasattr(self.fall_detector, 'person_tracks'):
                if track_id in self.fall_detector.person_tracks:
                    person_track = self.fall_detector.person_tracks[track_id]
                    
                    # Keypoint kalitesi kontrolü
                    if person_track.has_valid_pose():
                        stability = person_track.get_pose_stability()
                        if stability < 0.6:  # Yüksek stabilite gerekli
                            logging.debug(f"❌ Track {track_id} düşük pose stability: {stability:.3f}")
                            return False
                    else:
                        logging.debug(f"❌ Track {track_id} geçersiz pose")
                        return False
            
            # Tüm kontrollerden geçtiyse doğrula
            track_info['validated'] = True
            logging.info(f"✅ Track {track_id} doğrulandı - confidence: {confidence:.3f}, age: {track_age:.1f}s")
            return True
            
        except Exception as e:
            logging.error(f"Track validation hatası: {str(e)}")
            return False




if __name__ == "__main__":
    # Enhanced logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('guard_ai_v3.log', encoding='utf-8')
        ]
    )
    
    logging.info("🚀 Guard AI v3.0 başlatılıyor...")
    
    try:
        root = tk.Tk()
        app = GuardApp(root)
        logging.info("✅ Guard AI başarıyla başlatıldı!")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"❌ Guard AI başlatma hatası: {str(e)}")
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı:\n{str(e)}")
        sys.exit(1)
    
    
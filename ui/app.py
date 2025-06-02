# File: ui/app.py
# Açıklama: Ana uygulama arayüzü - YOLOv11 entegrasyonu ile güncellenmiş

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import time
import os
import sys
from typing import Optional
import uuid

from ui.login import LoginFrame
from ui.register import RegisterFrame
from ui.dashboard import DashboardFrame
from ui.settings import SettingsFrame
from ui.history import HistoryFrame

from config.firebase_config import FIREBASE_CONFIG
from config.settings import THEME_LIGHT, THEME_DARK, DEFAULT_THEME
from utils.auth import FirebaseAuth
from data.database import FirestoreManager
from data.storage import StorageManager
from core.camera import Camera
from core.fall_detection import FallDetector
from core.notification import NotificationManager
from api.server import run_api_server_in_thread

class GuardApp:
    """Ana uygulama sınıfı - YOLOv11 düşme algılama entegrasyonu."""

    def __init__(self, root: tk.Tk):
        """
        Args:
            root (tk.Tk): Tkinter kök penceresi
        """
        self.root = root
        self.root.title("Guard - YOLOv11 Düşme Algılama Sistemi")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f5f5f5")

        # Tema durumu
        self.current_theme = DEFAULT_THEME

        # Stiller
        self._setup_styles()

        # Firebase servisleri
        self._setup_firebase()

        # YOLOv11 düşme algılama sistemi
        self._setup_fall_detection()

        # API sunucusu
        self.api_thread = run_api_server_in_thread()

        # Çıkış planı
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # UI bileşenleri
        self._create_ui()

    def _setup_styles(self):
        """Tkinter stillerini ayarlar."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        theme = THEME_LIGHT if self.current_theme == "light" else THEME_DARK

        primary_color = theme["accent_primary"]
        secondary_color = theme["accent_secondary"]
        danger_color = theme["accent_danger"]
        warning_color = theme["accent_warning"]
        light_bg = theme["bg_secondary"]
        dark_bg = theme["bg_primary"]
        text_light = theme["text_primary"] if self.current_theme == "dark" else "#ffffff"
        text_dark = theme["text_primary"]

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=primary_color, padding=10)
        self.style.configure("Logo.TLabel", font=("Segoe UI", 10))
        self.style.configure("Login.TFrame", relief="ridge", borderwidth=1)
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8, relief="flat")
        self.style.map("TButton", background=[('active', '#2980b9'), ('disabled', '#bdc3c7')])
        self.style.configure("Wide.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        self.style.configure("Start.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        self.style.configure("Stop.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        self.style.configure("Card.TFrame", relief="flat")
        self.style.configure("Section.TLabel", font=("Segoe UI", 14, "bold"), foreground=text_dark, padding=(0, 5))
        self.style.configure("TEntry", padding=8, relief="flat")
        self.style.configure("TCheckbutton", font=("Segoe UI", 10))
        self.style.configure("TProgressbar", troughcolor=light_bg, thickness=8)
        self.style.configure("TCombobox", padding=8)
        self.style.configure("TNotebook", tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", foreground=text_dark, padding=[10, 5], font=("Segoe UI", 10))
        self.style.map("TNotebook.Tab", foreground=[('selected', primary_color)])
        self.style.configure("Info.TFrame", relief="flat", borderwidth=1)
        self.style.configure("Warning.TFrame", relief="flat", borderwidth=1)
        self.style.configure("Danger.TFrame", relief="flat", borderwidth=1)
        self.style.configure("Success.TFrame", relief="flat", borderwidth=1)

    def _setup_firebase(self):
        """Firebase servislerini ayarlar."""
        try:
            self.auth = FirebaseAuth(FIREBASE_CONFIG)
            self.db_manager = FirestoreManager()
            self.storage_manager = StorageManager()
            self.notification_manager = None
            self.current_user = None
            self.system_running = False
            self.detection_thread = None
            logging.info("Firebase servisleri başlatıldı.")
        except Exception as e:
            logging.error(f"Firebase servisleri başlatılırken hata oluştu: {str(e)}")
            messagebox.showerror(
                "Bağlantı Hatası",
                "Firebase servislerine bağlanılamadı.\nLütfen internet bağlantınızı kontrol edin ve tekrar deneyin."
            )
            self.root.after(2000, self._show_error_screen)

    def _setup_fall_detection(self):
        """YOLOv11 düşme algılama sistemini ayarlar."""
        try:
            # Kamera sistemini başlat
            self.camera = Camera.get_instance()
            
            # YOLOv11 düşme algılama modelini başlat
            self.fall_detector = FallDetector.get_instance()
            
            # Model bilgilerini logla
            model_info = self.fall_detector.get_model_info()
            logging.info(f"YOLOv11 Düşme Algılama Sistemi:")
            logging.info(f"  - Model Yüklü: {model_info['model_loaded']}")
            logging.info(f"  - Cihaz: {model_info['device']}")
            logging.info(f"  - Güven Eşiği: {model_info['confidence_threshold']}")
            logging.info(f"  - Frame Boyutu: {model_info['frame_size']}")
            
            if not model_info['model_loaded']:
                logging.warning("YOLOv11 modeli yüklenemedi! Düşme algılama devre dışı olacak.")
                messagebox.showwarning(
                    "Model Uyarısı",
                    "YOLOv11 düşme algılama modeli yüklenemedi.\n"
                    f"Model dosyası: {model_info['model_path']}\n"
                    "Sistem çalışacak ancak düşme algılama devre dışı olacak."
                )
            
        except Exception as e:
            logging.error(f"Düşme algılama sistemi başlatılırken hata: {str(e)}")
            messagebox.showerror(
                "Model Hatası",
                f"Düşme algılama sistemi başlatılamadı:\n{str(e)}\n"
                "Uygulama çalışacak ancak düşme algılama devre dışı olacak."
            )
            # Hata durumunda None olarak ayarla
            self.fall_detector = None

    def _show_error_screen(self):
        """Hata ekranını gösterir."""
        self._clear_content()
        error_frame = tk.Frame(self.content_frame, bg="#f5f5f5")
        error_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            error_frame,
            text="Bağlantı Hatası",
            font=("Segoe UI", 24, "bold"),
            fg="#d32f2f",
            bg="#f5f5f5"
        ).pack(pady=20)

        tk.Label(
            error_frame,
            text="Firebase servislerine bağlanılamadı.\nLütfen internet bağlantınızı kontrol edin ve uygulamayı yeniden başlatın.",
            font=("Segoe UI", 14),
            fg="#555",
            bg="#f5f5f5",
            justify=tk.CENTER
        ).pack(pady=10)

        tk.Button(
            error_frame,
            text="Uygulamayı Kapat",
            command=self.root.destroy,
            font=("Segoe UI", 12, "bold"),
            bg="#d32f2f",
            fg="white",
            relief="flat",
            padx=20,
            pady=10
        ).pack(pady=20)

    def _create_ui(self):
        """UI bileşenlerini oluşturur."""
        self.main_frame = tk.Frame(self.root, bg="#f5f5f5", padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.content_frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.show_login()

    def show_login(self):
        """Giriş ekranını gösterir."""
        self._clear_content()
        self.login_frame = LoginFrame(
            self.content_frame,
            self.auth,
            self._on_login_success,
            on_register_click=self.show_register
        )
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("Giriş ekranı gösterildi")

    def show_register(self):
        """Kayıt ekranını gösterir."""
        self._clear_content()
        self.register_frame = RegisterFrame(
            self.content_frame,
            self.auth,
            on_register_success=self.show_login,
            on_back_to_login=self.show_login
        )
        self.register_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("Kayıt ekranı gösterildi")

    def show_dashboard(self):
        """Ana gösterge panelini gösterir - sistem durumunu korur"""
        self._clear_content()
        
        # Dashboard frame'i oluştur
        self.dashboard_frame = DashboardFrame(
            self.content_frame,
            self.current_user,
            self.camera,
            self.start_detection,
            self.stop_detection,
            self.show_settings,
            self.show_history,
            self.logout
        )
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sistem durumunu dashboard'a aktar
        if hasattr(self, 'system_running') and self.system_running:
            self.dashboard_frame.update_system_status(True)
            logging.info("Dashboard yeniden oluşturuldu - sistem durumu aktarıldı")
        
        logging.info("Dashboard ekranı gösterildi")

    def show_settings(self):
        """Ayarlar ekranını gösterir - dashboard referansını temizler"""
        # Dashboard referansını güvenli şekilde temizle
        if hasattr(self, 'dashboard_frame'):
            try:
                self.dashboard_frame.on_destroy()
            except:
                pass
            self.dashboard_frame = None
            
        self._clear_content()
        self.settings_frame = SettingsFrame(
            self.content_frame,
            self.current_user,
            self.db_manager,
            self.show_dashboard
        )
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        logging.info("Ayarlar ekranı gösterildi")

    def show_history(self):
        """Geçmiş olaylar ekranını gösterir - dashboard referansını temizler"""
        # Dashboard referansını güvenli şekilde temizle
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
        logging.info("Geçmiş ekranı gösterildi")

    def _clear_content(self):
        """İçerik çerçevesindeki tüm bileşenleri güvenli şekilde temizler"""
        try:
            for widget in self.content_frame.winfo_children():
                try:
                    # Dashboard widget'ını güvenli şekilde yok et
                    if hasattr(widget, 'on_destroy'):
                        widget.on_destroy()
                    widget.destroy()
                except Exception as e:
                    logging.warning(f"Widget temizleme hatası: {e}")
        except Exception as e:
            logging.error(f"Content temizleme hatası: {e}")

    def _on_login_success(self, user):
        """Giriş başarılı olduğunda çağrılır."""
        self.current_user = user
        self.db_manager.update_last_login(user["localId"])
        user_data = self.db_manager.get_user_data(user["localId"])

        if not user_data:
            user_data = {
                "email": user.get("email", ""),
                "displayName": user.get("displayName", "")
            }
            self.db_manager.create_new_user(user["localId"], user_data)
            user_data = self.db_manager.get_user_data(user["localId"])

        if user_data and "settings" in user_data and "theme" in user_data["settings"]:
            if user_data["settings"]["theme"] != self.current_theme:
                self.current_theme = user_data["settings"]["theme"]
                self._setup_styles()

        self.notification_manager = NotificationManager(user_data)
        self.show_dashboard()

    def start_detection(self):
        """YOLOv11 düşme algılama sistemini başlatır - gelişmiş durum kontrolü"""
        if hasattr(self, 'system_running') and self.system_running:
            logging.warning("Sistem zaten çalışıyor.")
            # Dashboard varsa durumu güncelle
            if hasattr(self, 'dashboard_frame') and self.dashboard_frame:
                self.dashboard_frame.update_system_status(True)
            return

        # Kamerayı başlat
        if not self.camera.start():
            messagebox.showerror("Kamera Hatası", "Kamera başlatılamadı. Lütfen kamera bağlantınızı kontrol edin.")
            return

        # Düşme algılama modelini kontrol et
        if not self.fall_detector or not self.fall_detector.is_model_loaded:
            messagebox.showwarning(
                "Model Uyarısı", 
                "YOLOv11 düşme algılama modeli yüklü değil.\n"
                "Sistem kamera görüntüsünü gösterecek ancak düşme algılama çalışmayacak."
            )

        # Sistem durumunu güncelle
        self.system_running = True
        
        # Detection thread'ini başlat
        if hasattr(self, 'detection_thread') and self.detection_thread and self.detection_thread.is_alive():
            logging.warning("Detection thread zaten çalışıyor")
        else:
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()

        # Dashboard varsa durumu güncelle
        if hasattr(self, "dashboard_frame") and self.dashboard_frame:
            self.dashboard_frame.update_system_status(True)

        logging.info("YOLOv11 düşme algılama sistemi başlatıldı.")

    def stop_detection(self):
        """Düşme algılama sistemini durdurur - gelişmiş durum kontrolü"""
        if not hasattr(self, 'system_running') or not self.system_running:
            logging.warning("Sistem zaten durmuş durumda.")
            # Dashboard varsa durumu güncelle
            if hasattr(self, 'dashboard_frame') and self.dashboard_frame:
                self.dashboard_frame.update_system_status(False)
            return

        # Sistem durumunu güncelle
        self.system_running = False

        # Detection thread'ini durdur
        if hasattr(self, 'detection_thread') and self.detection_thread:
            if self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2.0)
            self.detection_thread = None

        # Kamerayı durdur
        self.camera.stop()

        # Dashboard varsa durumu güncelle
        if hasattr(self, "dashboard_frame") and self.dashboard_frame:
            self.dashboard_frame.update_system_status(False)

        logging.info("YOLOv11 düşme algılama sistemi durduruldu.")

    def _detection_loop(self):
        """YOLOv11 tabanlı gelişmiş düşme algılama döngüsü."""
        try:
            # Hata sayacı ve performans ölçümleri
            error_count = 0
            max_errors = 10
            
            # Performans ölçekleri
            last_detection_time = 0
            min_detection_interval = 15  # 15 saniye minimum bildirim arası
            target_fps = 30
            frame_duration = 1.0 / target_fps
            
            # YOLOv11 model performans takibi
            model_performance_log_interval = 60  # 1 dakikada bir performans logla
            last_model_log_time = 0
            
            logging.info("YOLOv11 düşme algılama döngüsü başlatıldı")
            
            while self.system_running:
                start_time = time.time()
                try:
                    # Kameranın durumunu kontrol et
                    if not self.camera or not self.camera.is_running:
                        time.sleep(0.5)
                        continue
                    
                    # Kareyi al
                    frame = self.camera.get_frame()
                    
                    # Kare geçersizse atla
                    if frame is None or frame.size == 0:
                        time.sleep(0.1)
                        continue
                    
                    # YOLOv11 model performansını logla
                    current_time = time.time()
                    if current_time - last_model_log_time > model_performance_log_interval:
                        if self.fall_detector and self.fall_detector.is_model_loaded:
                            model_info = self.fall_detector.get_model_info()
                            logging.info(f"YOLOv11 Model Performans: {model_info.get('avg_inference_time', 'N/A')}")
                        last_model_log_time = current_time
                    
                    # Düşme algılama - sadece model yüklüyse
                    is_fall = False
                    confidence = 0.0
                    
                    if self.fall_detector and self.fall_detector.is_model_loaded:
                        is_fall, confidence = self.fall_detector.detect_fall(frame)
                    
                    # Düşme algılandıysa ve yeterli süre geçtiyse bildirim gönder
                    if is_fall and (time.time() - last_detection_time) > min_detection_interval:
                        last_detection_time = time.time()
                        
                        # Tespit edilen frame için visualization oluştur
                        if self.fall_detector:
                            screenshot = self.fall_detector.get_detection_visualization(frame)
                        else:
                            screenshot = self.camera.capture_screenshot()
                        
                        # Ana thread'de düşme işlemi gerçekleştir
                        self.root.after(0, self._handle_fall_detection, screenshot, confidence)
                    
                    # FPS kontrolü için uyku süresi
                    elapsed_time = time.time() - start_time
                    sleep_time = max(0, frame_duration - elapsed_time)
                    time.sleep(sleep_time)
                    
                    # Hata sayacını sıfırla
                    error_count = 0
                    
                except Exception as e:
                    error_count += 1
                    logging.error(f"Düşme algılama döngüsünde hata ({error_count}/{max_errors}): {str(e)}")
                    
                    # Çok fazla hata varsa döngüyü sonlandır
                    if error_count >= max_errors:
                        logging.error(f"Maksimum hata sayısına ulaşıldı. Düşme algılama durduruluyor.")
                        self.root.after(0, self.stop_detection)
                        break
                    
                    time.sleep(1.0)  # Hata durumunda biraz bekle
            
        except Exception as e:
            logging.error(f"Algılama döngüsü tamamen başarısız: {str(e)}")
            self.root.after(0, self.stop_detection)

    def _handle_fall_detection(self, screenshot, confidence):
        """YOLOv11 ile düşme algılandığında çağrılır - güvenli dashboard güncellemesi"""
        try:
            logging.info(f"YOLOv11 Düşme Algılandı! Olasılık: {confidence:.4f}")

            # Benzersiz olay ID'si oluştur
            event_id = str(uuid.uuid4())
            
            # Ekran görüntüsünü yükle ve URL'sini al
            image_url = self.storage_manager.upload_screenshot(
                self.current_user["localId"],
                screenshot,
                event_id
            )
            
            # Olay verilerini oluştur
            event_data = {
                "id": event_id,
                "user_id": self.current_user["localId"],
                "timestamp": time.time(),
                "confidence": float(confidence),
                "image_url": image_url,
                "detection_method": "YOLOv11",
                "model_info": self.fall_detector.get_model_info() if self.fall_detector else {}
            }
            
            # Olay verilerini Firestore'a kaydet
            save_result = self.db_manager.save_fall_event(self.current_user["localId"], event_data)
            if not save_result:
                logging.error("Düşme olayı veritabanına kaydedilemedi!")
            else:
                logging.info(f"YOLOv11 düşme olayı veritabanına kaydedildi: {event_id}")

            # Bildirim gönder
            if self.notification_manager:
                user_data = self.db_manager.get_user_data(self.current_user["localId"])
                if user_data:
                    self.notification_manager.update_user_data(user_data)
                
                notification_result = self.notification_manager.send_notifications(event_data, screenshot)
                if not notification_result:
                    logging.error("Bildirimler gönderilemedi!")
                else:
                    logging.info("YOLOv11 düşme bildirimleri başarıyla gönderildi")
            else:
                logging.error("Bildirim yöneticisi bulunamadı!")

            # Dashboard'ı güvenli şekilde güncelle
            if hasattr(self, "dashboard_frame") and self.dashboard_frame:
                try:
                    # Widget'ın hala mevcut olup olmadığını kontrol et
                    if not self.dashboard_frame.is_destroyed and self.dashboard_frame.winfo_exists():
                        self.dashboard_frame.update_fall_detection(screenshot, confidence, event_data)
                        logging.info("Dashboard başarıyla güncellendi, YOLOv11 düşme uyarısı gösteriliyor")
                    else:
                        logging.warning("Dashboard widget mevcut değil, güncelleme atlandı")
                except Exception as e:
                    logging.error(f"Dashboard güncellenirken hata: {str(e)}")
            else:
                logging.warning("Dashboard referansı bulunamadı!")

        except Exception as e:
            logging.error(f"YOLOv11 düşme olayı işlenirken hata oluştu: {str(e)}", exc_info=True)

    def logout(self):
        """Kullanıcı çıkışı yapar."""
        if self.system_running:
            self.stop_detection()

        self.current_user = None
        self.notification_manager = None
        self.show_login()
        logging.info("Kullanıcı çıkış yaptı.")

    def toggle_theme(self):
        """Açık/koyu tema arasında geçiş yapar."""
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"

        # Tema geçiş animasyonu için kısa bir gecikme
        self.root.configure(bg="#000000" if self.current_theme == "dark" else "#f5f5f5")
        self._setup_styles()
        self._update_ui_theme()

        if self.current_user:
            settings = self.db_manager.get_user_data(self.current_user["localId"]).get("settings", {})
            settings["theme"] = self.current_theme
            self.db_manager.save_user_settings(self.current_user["localId"], settings)

    def _update_ui_theme(self):
        """Tüm UI bileşenlerini mevcut temaya göre günceller."""
        self.main_frame.configure(bg="#f5f5f5" if self.current_theme == "light" else "#212121")
        self.content_frame.configure(bg="#f5f5f5" if self.current_theme == "light" else "#212121")

        if hasattr(self, "login_frame") and self.login_frame.winfo_exists():
            self.login_frame.update_theme(self.current_theme)
        elif hasattr(self, "register_frame") and self.register_frame.winfo_exists():
            self.register_frame.update_theme(self.current_theme)
        elif hasattr(self, "dashboard_frame") and self.dashboard_frame.winfo_exists():
            self.dashboard_frame.update_theme(self.current_theme)
        elif hasattr(self, "settings_frame") and self.settings_frame.winfo_exists():
            self.settings_frame.update_theme(self.current_theme)
        elif hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            self.history_frame.update_theme(self.current_theme)

    def _on_close(self):
        """Uygulama kapatıldığında çağrılır."""
        try:
            if self.system_running:
                self.stop_detection()

            # Kamera ve model kaynaklarını temizle
            if hasattr(self, 'camera') and self.camera:
                self.camera.stop()
            
            if hasattr(self, 'fall_detector') and self.fall_detector:
                # Model kaynakları temizleme (gerekirse)
                pass

            logging.info("Uygulama kapatılıyor...")
            self.root.destroy()

        except Exception as e:
            logging.error(f"Uygulama kapatılırken hata oluştu: {str(e)}")
            sys.exit(1)
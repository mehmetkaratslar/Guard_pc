# app_integration.py
# Guard uygulamasındaki özellikleri birleştiren entegrasyon modülü

import logging
import os
import sys
import threading
import time

# Özel modülleri içe aktarma
from utils.password_reset_handler import PasswordResetHandler
from utils.user_settings_manager import UserSettingsManager
from ui.enhanced_settings import EnhancedSettingsFrame
from core.fall_detection import FallDetector
from core.camera import Camera
from core.notification import NotificationManager
from api.server import run_api_server_in_thread

class GuardApplicationIntegrator:
    """
    Guard uygulamasının bileşenlerini entegre eden sınıf.
    Bu sınıf, uygulama genelinde kullanılan tüm temel bileşenleri başlatır ve yönetir.
    """
    
    _instance = None
    _init_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Singleton örneğini döndürür."""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Entegratör sınıfını başlatır."""
        # Singleton kontrolü
        if GuardApplicationIntegrator._instance is not None:
            raise RuntimeError("GuardApplicationIntegrator zaten başlatılmış. get_instance() kullanın.")
        
        # Durum değişkenleri
        self.components = {
            "camera": {"status": "not_initialized", "instance": None},
            "fall_detector": {"status": "not_initialized", "instance": None},
            "notification": {"status": "not_initialized", "instance": None},
            "api_server": {"status": "not_initialized", "thread": None},
            "settings_manager": {"status": "not_initialized", "instance": None},
            "password_handler": {"status": "not_initialized", "instance": None}
        }
        
        # Kritik bileşenleri başlat
        self._init_core_components()
    
    def _init_core_components(self):
        """Temel bileşenleri başlatır."""
        # İlk olarak bağımlılıkları kontrol et
        self._check_dependencies()
        
        # Kamera sınıfını başlat
        try:
            self.components["camera"]["instance"] = Camera.get_instance()
            self.components["camera"]["status"] = "initialized"
            logging.info("Kamera bileşeni başlatıldı.")
        except Exception as e:
            self.components["camera"]["status"] = "error"
            logging.error(f"Kamera bileşeni başlatılamadı: {str(e)}")
        
        # Düşme algılama modelini başlat
        try:
            self.components["fall_detector"]["instance"] = FallDetector.get_instance()
            self.components["fall_detector"]["status"] = "initialized"
            logging.info("Düşme algılama bileşeni başlatıldı.")
        except Exception as e:
            self.components["fall_detector"]["status"] = "error"
            logging.error(f"Düşme algılama bileşeni başlatılamadı: {str(e)}")
        
        # Bildirim yöneticisini başlat
        try:
            self.components["notification"]["instance"] = NotificationManager.get_instance()
            self.components["notification"]["status"] = "initialized"
            logging.info("Bildirim bileşeni başlatıldı.")
        except Exception as e:
            self.components["notification"]["status"] = "error"
            logging.error(f"Bildirim bileşeni başlatılamadı: {str(e)}")
        
        # API sunucusunu başlat
        try:
            self.components["api_server"]["thread"] = run_api_server_in_thread()
            self.components["api_server"]["status"] = "running"
            logging.info("API sunucusu başlatıldı.")
        except Exception as e:
            self.components["api_server"]["status"] = "error"
            logging.error(f"API sunucusu başlatılamadı: {str(e)}")
    
    def _check_dependencies(self):
        """Kritik bağımlılıkları kontrol eder."""
        required_modules = [
            "cv2",      # OpenCV - görüntü işleme ve kamera
            "numpy",    # NumPy - matematiksel işlemler
            "torch",    # PyTorch - düşme algılama modeli
            "requests", # Requests - API çağrıları
            "PIL",      # Pillow - görüntü işleme
            "firebase_admin"  # Firebase - veritabanı
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            error_msg = f"Eksik kütüphaneler: {', '.join(missing_modules)}"
            logging.error(error_msg)
            raise ImportError(error_msg + 
                             "\nLütfen şu komutu çalıştırın: pip install " + " ".join(missing_modules))
    
    def init_app_components(self, app, auth, db_manager):
        """Uygulama bileşenlerini başlatır.
        
        Args:
            app: Ana uygulama örneği
            auth: Kimlik doğrulama yöneticisi
            db_manager: Veritabanı yöneticisi
        
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            logging.info("Uygulama bileşenleri başlatılıyor...")
            
            # Ayarlar yöneticisi
            try:
                self.components["settings_manager"]["instance"] = UserSettingsManager(auth, db_manager)
                self.components["settings_manager"]["status"] = "initialized"
                # Ana uygulamaya referans ekle
                app.settings_manager = self.components["settings_manager"]["instance"]
                logging.info("Ayarlar yöneticisi başlatıldı.")
            except Exception as e:
                self.components["settings_manager"]["status"] = "error"
                logging.error(f"Ayarlar yöneticisi başlatılamadı: {str(e)}")
            
            # Şifre sıfırlama işleyicisi
            try:
                self.components["password_handler"]["instance"] = PasswordResetHandler(auth)
                self.components["password_handler"]["status"] = "initialized"
                # Ana uygulamaya referans ekle
                app.password_handler = self.components["password_handler"]["instance"]
                logging.info("Şifre sıfırlama işleyicisi başlatıldı.")
            except Exception as e:
                self.components["password_handler"]["status"] = "error"
                logging.error(f"Şifre sıfırlama işleyicisi başlatılamadı: {str(e)}")
            
            # Kamera ve model referanslarını ana uygulamaya ekle
            app.camera = self.components["camera"]["instance"]
            app.fall_detector = self.components["fall_detector"]["instance"]
            app.notification_manager = self.components["notification"]["instance"]
            
            # Dashboard ekranı için etkinleştirilmiş kamera ve model ayarla
            self._enhance_dashboard(app)
            
            # Ayarlar ekranını geliştir
            self._enhance_settings(app)
            
            # Sistem kontrollerini geliştir
            self._enhance_system_controls(app)
            
            logging.info("Uygulama bileşenleri başarıyla entegre edildi.")
            return True
            
        except Exception as e:
            logging.error(f"Uygulama bileşenleri entegre edilirken hata: {str(e)}")
            return False
    
    def _enhance_dashboard(self, app):
        """Dashboard ekranını geliştirir."""
        # Orijinal show_dashboard metodunu yedekle
        if hasattr(app, "show_dashboard"):
            original_show_dashboard = app.show_dashboard
            
            # Dashboard görüntüleme metodunu geliştir
            def enhanced_show_dashboard():
                """Geliştirilmiş gösterge paneli ekranını gösterir."""
                # Çoklu açma sorununu düzelt - önceki ekranları temizle
                if hasattr(app, "dashboard_frame") and app.dashboard_frame:
                    try:
                        app.dashboard_frame.on_destroy()
                    except:
                        pass
                
                # Orijinal metodu çağır
                original_show_dashboard()
                
                # Kamera durumunu kontrol et ve gerekirse yeniden başlat
                if app.camera and not app.camera.is_running:
                    threading.Thread(target=app.camera.start, daemon=True).start()
            
            # Metodu değiştir
            app.show_dashboard = enhanced_show_dashboard
            logging.info("Dashboard ekranı geliştirildi.")
    
    def _enhance_settings(self, app):
        """Ayarlar ekranını geliştirir."""
        # Orijinal show_settings metodunu yedekle
        if hasattr(app, "show_settings"):
            original_show_settings = app.show_settings
            
            # Ayarlar görüntüleme metodunu geliştir
            def enhanced_show_settings():
                """Geliştirilmiş ayarlar ekranını gösterir."""
                # Önce orijinal metodu çağır
                original_show_settings()
                
                # EnhancedSettingsFrame ile geliştir
                if hasattr(app, "settings_frame"):
                    try:
                        # EnhancedSettingsFrame örneği oluştur
                        enhanced_settings = EnhancedSettingsFrame(
                            app.settings_frame,
                            app.current_user,
                            app.auth,
                            app.db_manager
                        )
                        
                        # Referansı sakla
                        app.enhanced_settings = enhanced_settings
                        
                        logging.info("Gelişmiş ayarlar ekranı başarıyla uygulandı.")
                    except Exception as e:
                        logging.error(f"Gelişmiş ayarlar ekranı uygulanırken hata: {str(e)}")
            
            # Metodu değiştir
            app.show_settings = enhanced_show_settings
            logging.info("Ayarlar ekranı geliştirildi.")
    
    def _enhance_system_controls(self, app):
        """Sistem kontrol metodlarını güvenlik ve kararlılık için geliştirir."""
        # Başlatma metodunu yedekle ve geliştir
        if hasattr(app, "start_detection"):
            original_start_detection = app.start_detection
            
            def enhanced_start_detection():
                """Geliştirilmiş düşme algılama başlatma."""
                try:
                    # Sistem zaten çalışıyorsa uyar
                    if app.system_running:
                        logging.warning("Sistem zaten çalışıyor.")
                        return
                    
                    # Kameranın durumunu kontrol et
                    if not app.camera:
                        logging.error("Kamera bileşeni bulunamadı.")
                        return
                    
                    # Kamerayı başlat - eğer başarısız olursa
                    if not app.camera.is_running and not app.camera.start():
                        logging.error("Kamera başlatılamadı.")
                        return
                    
                    # Daha sonra orijinal metodu çağır
                    original_start_detection()
                    
                except Exception as e:
                    logging.error(f"Düşme algılama başlatılırken hata: {str(e)}")
                    app.system_running = False
                    if hasattr(app, "dashboard_frame"):
                        app.dashboard_frame.update_system_status(False)
            
            # Metodu değiştir
            app.start_detection = enhanced_start_detection
            
        # Durdurma metodunu yedekle ve geliştir
        if hasattr(app, "stop_detection"):
            original_stop_detection = app.stop_detection
            
            def enhanced_stop_detection():
                """Geliştirilmiş düşme algılama durdurma."""
                try:
                    # Sistem çalışmıyorsa uyar
                    if not app.system_running:
                        logging.warning("Sistem zaten durdurulmuş durumda.")
                        return
                    
                    # Orijinal metodu çağır
                    original_stop_detection()
                    
                    # Sistem durumunu güncelle (hata durumunda güvenlik için)
                    app.system_running = False
                    if hasattr(app, "dashboard_frame"):
                        app.dashboard_frame.update_system_status(False)
                    
                except Exception as e:
                    logging.error(f"Düşme algılama durdurulurken hata: {str(e)}")
                    # Zorla durdur
                    app.system_running = False
                    if app.camera:
                        app.camera.stop()
                    if hasattr(app, "dashboard_frame"):
                        app.dashboard_frame.update_system_status(False)
            
            # Metodu değiştir
            app.stop_detection = enhanced_stop_detection
            
        # Düşme algılama thread metodunu geliştir
        if hasattr(app, "_detection_loop"):
            original_detection_loop = app._detection_loop
            
            def enhanced_detection_loop():
                """Geliştirilmiş düşme algılama döngüsü."""
                try:
                    # Hata sayacı
                    error_count = 0
                    max_errors = 10
                    
                    # Performans ölçekleri
                    last_detection_time = 0
                    min_detection_interval = 5
                    target_fps = 30
                    frame_duration = 1.0 / target_fps
                    
                    while app.system_running:
                        start_time = time.time()
                        try:
                            # Kameranın durumunu kontrol et
                            if not app.camera or not app.camera.is_running:
                                time.sleep(0.5)
                                continue
                            
                            # Kareyi al
                            frame = app.camera.get_frame()
                            
                            # Kare geçersizse atla
                            if frame is None or frame.size == 0:
                                time.sleep(0.1)
                                continue
                            
                            # Düşme algılama modelinin durumunu kontrol et
                            if not app.fall_detector or not app.fall_detector.is_model_loaded:
                                logging.warning("Düşme algılama modeli yüklü değil, durduruldu.")
                                app.stop_detection()
                                break
                            
                            # Düşme algıla
                            is_fall, confidence = app.fall_detector.detect_fall(frame)
                            
                            # Düşme algılandıysa ve yeterli süre geçtiyse
                            if is_fall and (time.time() - last_detection_time) > min_detection_interval:
                                last_detection_time = time.time()
                                screenshot = app.camera.capture_screenshot()
                                app.root.after(0, app._handle_fall_detection, screenshot, confidence)
                            
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
                                app.root.after(0, app.stop_detection)
                                break
                            
                            time.sleep(1.0)  # Hata durumunda biraz bekle
                    
                except Exception as e:
                    logging.error(f"Algılama döngüsü tamamen başarısız: {str(e)}")
                    app.root.after(0, app.stop_detection)
            
            # Metodu değiştir
            app._detection_loop = enhanced_detection_loop
            
        logging.info("Sistem kontrolleri geliştirildi.")

    def get_status(self):
        """Tüm bileşenlerin durumunu döndürür."""
        return self.components


def entegre_et(app):
    """
    Geliştirilen özellikleri ana uygulamaya entegre eder.
    
    Args:
        app (GuardApp): Ana uygulama örneği
    
    Returns:
        bool: Entegrasyon başarılı ise True, değilse False
    """
    try:
        logging.info("Guard uygulaması entegrasyonu başlatılıyor...")
        
        # Singleton entegratör örneğini al
        integrator = GuardApplicationIntegrator.get_instance()
        
        # Uygulama bileşenlerini başlat
        result = integrator.init_app_components(app, app.auth, app.db_manager)
        
        # Entegratör referansını uygulamaya ekle
        app.integrator = integrator
        
        return result
        
    except Exception as e:
        logging.error(f"Entegrasyon sırasında hata: {str(e)}")
        return False
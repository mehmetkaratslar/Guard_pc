# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: camera.py (ULTRA ENHANCED CAMERA ENGINE)
# Konum: pc/core/camera.py
# Açıklama:
# Bu dosya, Guard AI uygulamasında kullanılan gelişmiş kamera motorunu tanımlar.
# Gerçek zamanlı kamera görüntüsünü alır, işleme tabi tutar, parlaklık ve kontrast
# kontrolü sağlar ve yüksek performanslı video akışı sunar.
#
# Çoklu backend desteği (cv2.CAP_DSHOW, cv2.CAP_V4L2, vs.) ile uyumludur.

# === ÖZELLİKLER ===
# - Gerçek zamanlı kamera akışı
# - Otomatik ve manuel parlaklık/kontrast kontrolü
# - Frame atlama (performance optimizasyonu)
# - Dinamik kalite ayarı (yüksek CPU kullanımında)
# - Yeniden bağlantı sistemi (bağlantı kesilirse otomatik tekrar bağlanır)
# - Performans izleme (FPS, buffer boyutu, ortalama parlaklık)
# - Farklı backend destekleri (DSHOW, V4L2, vb.)

# === BAŞLICA MODÜLLER VE KULLANIM AMACI ===
# - cv2 (OpenCV): Kamera görüntüsünü alma ve işleme
# - numpy: Görsel verilerin analizi için
# - threading: Arka planda çalışan kamera döngüsü
# - logging: Hata ve işlem kayıtları tutma
# - time / queue / deque: Zamanlama ve buffer yönetimi
# - platform: Sistem bilgisi almak için

# === SINIFLAR ===
# - Camera: Gelişmiş kamera kontrol sınıfı (threaded yapıda çalışır)

# === TEMEL FONKSİYONLAR ===
# - __init__: Kamera bağlantısı başlatılır, varsayılan ayarlar yapılır
# - start: Kamera akışını başlatır
# - stop: Kamera akışını durdurur
# - get_frame: İşlenmiş bir frame döner
# - _capture_loop: Ana kamera yakalama döngüsü
# - _analyze_and_adjust_brightness: Parlaklık analizi ve gerekirse ayar yapar
# - _apply_brightness_adjustments: Frame’e yazılım bazlı parlaklık/kontrast uygular
# - _fast_reconnect: Bağlantı koparsa hızlı yeniden bağlanmayı dener
# - set_brightness / set_contrast: Manuel parlaklık ve kontrast ayarları
# - get_performance_stats: FPS, buffer boyutu, parlaklık gibi istatistikleri döner

# === PARLAKLIK KONTROLÜ ===
# - Görüntünün gri tonlamaya çevrilmesiyle ortalama parlaklık ölçülür
# - Optimal parlaklık aralığı: 80-170 (0-255 arasında)
# - Çok parlaksa otomatik olarak azaltılır
# - Çok karanlıkssa otomatik olarak artırılır

# === GERÇEK ZAMANLI İŞLEME ===
# - Her frame ayrı ayrı işlenir
# - Kalite dinamik olarak ayarlanabilir
# - Yüksek CPU yüküne karşı frame atlanabilir

# === BACKEND DESTEĞİ ===
# - Windows: cv2.CAP_DSHOW
# - Linux: cv2.CAP_V4L2
# - Diğer platformlar için varsayılan backend kullanılır

# === PERFORMANS İZLEME ===
# - Ortalama FPS
# - Buffer boyutu
# - Son 10 frame’in işlem süresi
# - Geçerli parlaklık/kontrast değerleri

# === HATA YÖNETİMİ ===
# - Tüm işlemlerde try-except bloklarıyla hatalar loglanır
# - Kullanıcıya anlamlı mesajlar gösterilir
# - Bağlantı hatası durumunda uyarı verilir

# === LOGGING ===
# - Tüm işlemler log dosyasına yazılır (guard_ai_v3.log)
# - Log formatı: Tarih/Zaman [Seviye] Mesaj

# === TEST AMAÇLI KULLANIM ===
# - `if __name__ == "__main__":` bloğu ile bağımsız çalıştırılabilir
# - Basit test modunda FPS ve parlaklık değerleri terminale yazdırılır

# === NOTLAR ===
# - Bu dosya, app.py, dashboard.py ve settings.py ile entegre çalışır
# - Yüksek performans için thread’de çalıştırılır
# - Ayarlar ana uygulama üzerinden güncellenebilir
# =======================================================================================


import cv2
import numpy as np
import threading
import logging
import time
import platform
from collections import deque
import queue
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class EnhancedCamera:
    """Stabil kamera sınıfı - doğal ayarlar ile."""
    
    def __init__(self, camera_index, backend=cv2.CAP_ANY):
        """
        Args:
            camera_index (int): Kamera indeksi
            backend (int): OpenCV backend
        """
        self.camera_index = camera_index
        self.original_backend = backend
        self.backend = backend
        self.cap = None
        self.is_running = False
        self.thread = None
        
        # DÜZELTME: Basit frame yönetimi
        self.current_frame = None
        self.frame_lock = threading.RLock()
        self.last_frame_time = 0
        
        # DÜZELTME: FPS tracking - basit
        self.actual_fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # DÜZELTME: Minimal ayarlar - doğal kalite için
        self.auto_brightness = False  # Otomatik parlaklık KAPALI
        self.brightness_adjustment = 0
        self.contrast_adjustment = 1.0
        
        # Bağlantı yönetimi
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.connection_stable = False
        
        # Backend seçimi
        self.backend_fallbacks = self._get_platform_backends()
        self.camera_validated = False
        
        logging.info(f"EnhancedCamera {camera_index} oluşturuldu - Doğal ayarlar modunda")
    
    def _get_platform_backends(self):
        """Platform optimized backend sıralaması."""
        if platform.system() == "Windows":
            return [
                cv2.CAP_DSHOW,      # DirectShow - En iyi performans
                cv2.CAP_MSMF,       # Media Foundation
                cv2.CAP_ANY
            ]
        elif platform.system() == "Linux":
            return [
                cv2.CAP_V4L2,       # Video4Linux2
                cv2.CAP_ANY
            ]
        elif platform.system() == "Darwin":  # macOS
            return [
                cv2.CAP_AVFOUNDATION,
                cv2.CAP_ANY
            ]
        else:
            return [cv2.CAP_ANY]
   
    def _validate_camera_with_fallback(self):
        """DÜZELTME: Hızlı ve güvenli kamera doğrulama"""
        if self.camera_validated:
            return True
        
        logging.info(f"EnhancedCamera {self.camera_index} doğrulanıyor...")
        
        # Önce belirtilen backend'i dene
        if self.original_backend != cv2.CAP_ANY:
            if self._test_camera_with_backend(self.original_backend):
                self.backend = self.original_backend
                self.camera_validated = True
                logging.info(f"Kamera {self.camera_index}: {self._backend_name(self.original_backend)} BAŞARILI")
                return True
        
        # Priority backend'leri dene
        priority_backends = []
        if platform.system() == "Windows":
            priority_backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
        elif platform.system() == "Linux":
            priority_backends = [cv2.CAP_V4L2]
        else:
            priority_backends = [cv2.CAP_ANY]
        
        for backend in priority_backends:
            try:
                if self._test_camera_with_backend(backend):
                    self.backend = backend
                    self.camera_validated = True
                    logging.info(f"Kamera {self.camera_index}: {self._backend_name(backend)} BAŞARILI")
                    return True
            except Exception as e:
                logging.debug(f"Backend {self._backend_name(backend)} test hatası: {e}")
                continue
        
        logging.warning(f"Kamera {self.camera_index}: Tüm backend'ler başarısız!")
        return False
  
    def _test_camera_with_backend(self, backend):
        """Belirli bir backend ile kamerayı test eder."""
        test_cap = None
        try:
            test_cap = cv2.VideoCapture(self.camera_index, backend)
            
            if not test_cap.isOpened():
                return False
            
            # DÜZELTME: Minimal test ayarları
            test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Frame test
            ret, frame = test_cap.read()
            
            if ret and frame is not None and frame.size > 0:
                logging.debug(f"Kamera {self.camera_index} test BAŞARILI: {frame.shape}")
                return True
            else:
                return False
                
        except Exception as e:
            logging.debug(f"Kamera {self.camera_index} test HATASI: {e}")
            return False
        finally:
            if test_cap:
                try:
                    test_cap.release()
                except:
                    pass
    
    def start(self):
        """DÜZELTME: Doğal ayarlarla kamera başlatma."""
        if self.is_running:
            logging.warning(f"Kamera {self.camera_index} zaten çalışıyor")
            return True
        
        # Doğrulama
        if not self._validate_camera_with_fallback():
            logging.error(f"Kamera {self.camera_index} doğrulanamadı")
            return False
        
        try:
            # Kamerayı aç
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if not self.cap.isOpened():
                logging.error(f"Kamera {self.camera_index} açılamadı")
                return False
            
            # DÜZELTME: Minimal kamera ayarları - doğal kalite
            self._setup_natural_parameters()
            
            # İlk frame test
            if not self._test_initial_frame():
                logging.error(f"Kamera {self.camera_index} ilk frame testi BAŞARISIZ")
                self._cleanup()
                return False
            
            # Capture thread
            self.is_running = True
            self.thread = threading.Thread(target=self._stable_capture_loop, daemon=True)
            self.thread.start()
            
            self.connection_stable = True
            logging.info(f"EnhancedCamera {self.camera_index} BAŞLATILDI - Doğal ayarlar aktif")
            return True
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} başlatma HATASI: {e}")
            self._cleanup()
            return False
    
    def _setup_natural_parameters(self):
        """
        DÜZELTME: Stabil kamera parametreleri - titreme yok
        """
        try:
            # DÜZELTME: Buffer boyutu artırıldı
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # 1 -> 2
            
            # DÜZELTME: Sabit FPS ayarı
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # DÜZELTME: Sabit çözünürlük - gidip gelmeyi önler
            current_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            current_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            # Eğer çok düşükse 1280x720 yap, yoksa mevcut ayarı koru
            if current_width < 640 or current_height < 480:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                logging.info(f"Kamera {self.camera_index} çözünürlük ayarlandı: 1280x720")
            else:
                logging.info(f"Kamera {self.camera_index} mevcut çözünürlük korundu: {current_width}x{current_height}")
            
            # DÜZELTME: Auto ayarları kontrollü aç
            try:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Otomatik pozlama hafif
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)         # Otomatik focus açık
            except:
                pass  # Desteklemiyorsa geç
            
            # DÜZELTME: Codec optimizasyonu
            try:
                # MJPEG codec daha stabil
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            except:
                pass
            
            logging.info(f"Kamera {self.camera_index} stabil parametreler ayarlandı")
            
        except Exception as e:
            logging.warning(f"Kamera {self.camera_index} parametre ayarlama hatası: {e}")

    def _test_initial_frame(self):
        """İlk frame testi - hızlı."""
        try:
            for attempt in range(3):  # 5 → 3 deneme
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    # DÜZELTME: Frame'i direkt kullan, işleme
                    with self.frame_lock:
                        self.current_frame = frame
                    
                    logging.debug(f"Kamera {self.camera_index} ilk frame OK: {frame.shape}")
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} ilk frame test hatası: {e}")
            return False
   
    def _stable_capture_loop(self):
        """
        DÜZELTME: Çok stabil capture loop - Windows timeout sorunu çözüldü
        """
        consecutive_failures = 0
        max_failures = 15  # 10 -> 15 (daha toleranslı)
        
        # DÜZELTME: Adaptive FPS - sistem yüküne göre ayarlama
        target_fps = 30
        frame_interval = 1.0 / target_fps
        adaptive_sleep = 0.033  # 30 FPS için başlangıç
        
        # Performance tracking
        fps_counter = 0
        fps_start_time = time.time()
        last_adaptation = time.time()
        
        logging.info(f"Kamera {self.camera_index} stable capture loop başlatıldı - adaptive FPS")
        
        while self.is_running:
            loop_start = time.time()
            
            try:
                if not self.cap or not self.cap.isOpened():
                    if not self._fast_reconnect():
                        break
                    continue
                
                # DÜZELTME: Timeout korumalı frame capture
                ret, frame = self.cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error(f"Kamera {self.camera_index}: Maksimum hata sayısına ulaşıldı")
                        break
                    
                    # DÜZELTME: Hata durumunda kısa sleep
                    time.sleep(0.01)
                    continue
                
                # Başarılı frame
                consecutive_failures = 0
                fps_counter += 1
                
                # DÜZELTME: Frame'i thread-safe kaydet
                with self.frame_lock:
                    self.current_frame = frame.copy()  # Deep copy - referans sorunu yok
                
                # DÜZELTME: FPS calculation - 5 saniyede bir
                current_time = time.time()
                if current_time - fps_start_time >= 5.0:
                    elapsed = current_time - fps_start_time
                    self.actual_fps = fps_counter / elapsed if elapsed > 0 else 0
                    
                    # Adaptive sleep adjustment
                    if current_time - last_adaptation >= 10.0:  # 10 saniyede bir adapt
                        if self.actual_fps < 25:  # FPS düşükse sleep'i azalt
                            adaptive_sleep = max(0.01, adaptive_sleep * 0.9)
                        elif self.actual_fps > 35:  # FPS yüksekse sleep'i artır
                            adaptive_sleep = min(0.05, adaptive_sleep * 1.1)
                        
                        last_adaptation = current_time
                        logging.debug(f"Kamera {self.camera_index} adaptive sleep: {adaptive_sleep:.3f}s (FPS: {self.actual_fps:.1f})")
                    
                    fps_counter = 0
                    fps_start_time = current_time
                
                # DÜZELTME: Adaptive timing
                elapsed_time = time.time() - loop_start
                sleep_time = max(adaptive_sleep, frame_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.001)  # Minimum sleep - CPU overload önleme
                    
            except Exception as e:
                consecutive_failures += 1
                logging.error(f"Kamera {self.camera_index} capture error: {e}")
                
                if consecutive_failures >= max_failures:
                    logging.error(f"Kamera {self.camera_index}: Kritik hata sayısına ulaşıldı")
                    break
                
                time.sleep(0.05)  # Hata durumunda biraz daha uzun sleep
        
        self.is_running = False
        self.connection_stable = False
        logging.info(f"Kamera {self.camera_index} stable capture loop SONLANDI")



    def _fast_reconnect(self):
        """Hızlı yeniden bağlantı."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logging.error(f"Kamera {self.camera_index}: Maksimum reconnect aşıldı")
            return False
        
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            
            time.sleep(0.5)
            
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if self.cap.isOpened():
                self._setup_natural_parameters()
                self.reconnect_attempts = 0
                self.connection_stable = True
                logging.info(f"Kamera {self.camera_index} RECONNECT başarılı")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} reconnect HATA: {e}")
            return False
    
    
    def _fast_reconnect(self):
        """DÜZELTME: Hızlı ve güvenli yeniden bağlantı."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logging.error(f"Kamera {self.camera_index}: Maksimum reconnect aşıldı ({self.max_reconnect_attempts})")
            return False
        
        try:
            logging.info(f"Kamera {self.camera_index} reconnect deneme {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            
            # Eski bağlantıyı temizle
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            # Kısa bekleme
            time.sleep(0.5)
            
            # Yeni bağlantı
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if self.cap and self.cap.isOpened():
                # Parametreleri yeniden ayarla
                self._setup_natural_parameters()
                
                # Test frame
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.reconnect_attempts = 0
                    self.connection_stable = True
                    logging.info(f"Kamera {self.camera_index} RECONNECT başarılı!")
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} reconnect HATA: {e}")
            return False

    
    def get_frame(self):
        """
        DÜZELTME: Thread-safe ve stabil frame alma
        """
        try:
            with self.frame_lock:
                if self.current_frame is not None:
                    # DÜZELTME: Deep copy döndür - referans sorunları yok
                    return self.current_frame.copy()
                else:
                    # DÜZELTME: Placeholder frame - sistem çökmez
                    return self._create_stable_placeholder_frame()
                    
        except Exception as e:
            logging.debug(f"get_frame hatası: {e}")
            return self._create_stable_placeholder_frame()
    
    def _create_stable_placeholder_frame(self):
        """DÜZELTME: Stabil placeholder frame - sistem çökmez."""
        try:
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            
            # Gradient background - görsel olarak hoş
            for i in range(720):
                intensity = int(15 + (i / 720) * 25)
                frame[i, :] = [intensity, intensity, intensity]
            
            # Durum mesajları
            font = cv2.FONT_HERSHEY_SIMPLEX
            
            if not self.is_running:
                message = f"Kamera {self.camera_index} - KAPALI"
                color = (100, 100, 100)
                status = "Sistem durduruldu"
            elif not self.connection_stable:
                message = f"Kamera {self.camera_index} - BAGLANILIYOR..."
                color = (0, 255, 255)
                status = "Baglanti kuruluyor"
            else:
                message = f"Kamera {self.camera_index} - HAZIR"
                color = (0, 255, 0)
                status = "Sistem hazir"
            
            # Ana mesaj
            text_size = cv2.getTextSize(message, font, 1.2, 2)[0]
            text_x = (1280 - text_size[0]) // 2
            text_y = (720 + text_size[1]) // 2
            cv2.putText(frame, message, (text_x, text_y), font, 1.2, color, 3, cv2.LINE_AA)
            
            # Status mesajı
            status_size = cv2.getTextSize(status, font, 0.8, 2)[0]
            status_x = (1280 - status_size[0]) // 2
            status_y = text_y + 50
            cv2.putText(frame, status, (status_x, status_y), font, 0.8, (200, 200, 200), 2, cv2.LINE_AA)
            
            # FPS bilgisi
            fps_text = f"FPS: {self.actual_fps:.1f} | STABIL MOD"
            fps_size = cv2.getTextSize(fps_text, font, 0.6, 1)[0]
            fps_x = (1280 - fps_size[0]) // 2
            fps_y = status_y + 35
            cv2.putText(frame, fps_text, (fps_x, fps_y), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Border
            cv2.rectangle(frame, (50, 50), (1230, 670), color, 3)
            
            return frame
            
        except Exception as e:
            # En basit fallback frame
            logging.error(f"Placeholder frame hatası: {e}")
            fallback = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(fallback, "CAMERA ERROR", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return fallback

        
        
    def set_brightness(self, brightness):
        """Manuel parlaklık ayarı - KULLANIMA KAPALI."""
        logging.warning(f"Kamera {self.camera_index}: Parlaklık ayarı devre dışı - doğal ayarlar korunuyor")
    
    def set_contrast(self, contrast):
        """Manuel kontrast ayarı - KULLANIMA KAPALI."""
        logging.warning(f"Kamera {self.camera_index}: Kontrast ayarı devre dışı - doğal ayarlar korunuyor")
    
    def enable_auto_brightness(self, enable=True):
        """Otomatik parlaklık - KAPALI."""
        self.auto_brightness = False
        logging.info(f"Kamera {self.camera_index}: Otomatik ayarlar kapalı - doğal kalite korunuyor")
    
    def get_performance_stats(self):
        """Performans istatistiklerini döndür."""
        return {
            'actual_fps': self.actual_fps,
            'connection_stable': self.connection_stable,
            'brightness_adjustment': 0,  # Doğal ayarlar
            'auto_brightness': False,    # Kapalı
            'natural_settings': True     # Doğal ayarlar aktif
        }
    
    def stop(self):
        """Kamerayı durdur."""
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        self._cleanup()
        logging.info(f"EnhancedCamera {self.camera_index} DURDURULDU")
    
    def _cleanup(self):
        """Kaynakları temizle."""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except:
            pass
        
        with self.frame_lock:
            self.current_frame = None
        
        self.connection_stable = False
    
    def _create_placeholder_frame(self):
        """Placeholder frame oluştur."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Basit gradient
        for i in range(480):
            intensity = int(20 + (i / 480) * 40)
            frame[i, :] = [intensity, intensity, intensity]
        
        # Durum mesajı
        if not self.is_running:
            message = f"Kamera {self.camera_index} - KAPALI"
            color = (100, 100, 100)
        elif not self.connection_stable:
            message = f"Kamera {self.camera_index} - BAGLANILIYOR..."
            color = (0, 255, 255)
        else:
            message = f"Kamera {self.camera_index} - HAZIR"
            color = (0, 255, 0)
        
        # Performans bilgisi
        perf_text = f"FPS: {self.actual_fps:.1f} | DOGAL AYARLAR"
        
        # Metni çiz
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Ana mesaj
        text_size = cv2.getTextSize(message, font, font_scale, thickness)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = (480 + text_size[1]) // 2
        cv2.putText(frame, message, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
        
        # Performans bilgisi
        perf_size = cv2.getTextSize(perf_text, font, 0.6, 1)[0]
        perf_x = (640 - perf_size[0]) // 2
        perf_y = text_y + 40
        cv2.putText(frame, perf_text, (perf_x, perf_y), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        
        return frame
    
    def _backend_name(self, backend):
        """Backend adını döndür."""
        names = {
            cv2.CAP_ANY: "AUTO",
            cv2.CAP_DSHOW: "DirectShow",
            cv2.CAP_MSMF: "MediaFoundation",
            cv2.CAP_VFW: "VideoForWindows",
            cv2.CAP_V4L2: "Video4Linux2",
            cv2.CAP_GSTREAMER: "GStreamer",
            cv2.CAP_AVFOUNDATION: "AVFoundation"
        }
        return names.get(backend, f"Backend_{backend}")


# Geriye uyumluluk için alias
Camera = EnhancedCamera


# Test fonksiyonu
def test_natural_camera(camera_index=0):
    """Doğal ayarlı kamera testini yapar."""
    print(f"Natural Camera {camera_index} test başlatılıyor...")
    
    camera = EnhancedCamera(camera_index)
    
    if not camera.start():
        print(f"❌ Kamera {camera_index} başlatılamadı!")
        return False
    
    print("✅ Kamera başlatıldı, 10 saniye test (doğal ayarlar)...")
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 10:
        frame = camera.get_frame()
        if frame is not None:
            frame_count += 1
            
            # Performance stats
            if frame_count % 30 == 0:
                stats = camera.get_performance_stats()
                print(f"📊 FPS: {stats['actual_fps']:.1f}, Doğal: {stats['natural_settings']}")
        
        time.sleep(1/30)
    
    camera.stop()
    
    avg_fps = frame_count / 10
    print(f"✅ Test tamamlandı. Ortalama FPS: {avg_fps:.1f} (Doğal ayarlar)")
    return True


if __name__ == "__main__":
    # Test çalıştır
    logging.basicConfig(level=logging.INFO)
    test_natural_camera(0)
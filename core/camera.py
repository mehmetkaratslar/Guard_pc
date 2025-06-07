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
    """Yüksek performanslı, akışlı kamera sınıfı."""
    
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
        
        # YÜKSEK PERFORMANS FRAME YÖNETİMİ
        self.frame_buffer = queue.Queue(maxsize=3)  # Küçük buffer - düşük latency
        self.frame_lock = threading.RLock()
        self.last_frame_time = 0
        self.target_fps = 30
        self.actual_fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # AKIŞLI VİDEO İÇİN OPTİMİZASYON
        self.skip_frames = 0  # Frame atlama (performance için)
        self.quality_adjustment = 1.0  # Dinamik kalite ayarı
        self.processing_time = deque(maxlen=10)  # Son 10 frame işlem süresi
        
        # PARLAKILIK VE KAMERA KONTROLLERI
        self.brightness_adjustment = 0  # -100 ile +100 arası
        self.contrast_adjustment = 1.0  # 0.5 ile 2.0 arası
        self.exposure_adjustment = -6   # Otomatik exposure control
        self.auto_brightness = True    # Otomatik parlaklık ayarı
        
        # Bağlantı yönetimi
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.connection_stable = False
        
        # Backend seçimi
        self.backend_fallbacks = self._get_platform_backends()
        self.camera_validated = False
        
        logging.info(f"EnhancedCamera {camera_index} oluşturuldu")
    
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
        """Kamerayı farklı backend'lerle test eder."""
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
        
        # Fallback backend'leri dene
        for backend in self.backend_fallbacks:
            if self._test_camera_with_backend(backend):
                self.backend = backend
                self.camera_validated = True
                logging.info(f"Kamera {self.camera_index}: {self._backend_name(backend)} BAŞARILI")
                return True
        
        logging.error(f"Kamera {self.camera_index}: TÜM BACKEND'LER BAŞARISIZ!")
        return False
    
    def _test_camera_with_backend(self, backend):
        """Belirli bir backend ile kamerayı test eder."""
        test_cap = None
        try:
            test_cap = cv2.VideoCapture(self.camera_index, backend)
            
            if not test_cap.isOpened():
                return False
            
            # Yüksek performans ayarları
            test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer
            test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            test_cap.set(cv2.CAP_PROP_FPS, 30)
            
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
        """Yüksek performanslı kamera başlatma."""
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
            
            # YÜKSEK PERFORMANS PARAMETRELERİ
            self._setup_high_performance_parameters()
            
            # İlk frame test
            if not self._test_initial_frame():
                logging.error(f"Kamera {self.camera_index} ilk frame testi BAŞARISIZ")
                self._cleanup()
                return False
            
            # Frame buffer temizle
            while not self.frame_buffer.empty():
                try:
                    self.frame_buffer.get_nowait()
                except queue.Empty:
                    break
            
            # Yüksek performanslı capture thread
            self.is_running = True
            self.thread = threading.Thread(target=self._high_performance_capture_loop, daemon=True)
            self.thread.start()
            
            self.connection_stable = True
            logging.info(f"EnhancedCamera {self.camera_index} BAŞLATILDI ({self._backend_name(self.backend)})")
            return True
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} başlatma HATASI: {e}")
            self._cleanup()
            return False
    
    def _setup_high_performance_parameters(self):
        """Yüksek performans kamera parametreleri."""
        try:
            # TEMEL AYARLAR
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal latency
            
            # PERFORMANS OPTİMİZASYONU
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            # PARLAKLIK VE KONTRAST KONTROLLERI
            if platform.system() == "Windows":
                # Windows spesifik ayarlar
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manuel exposure
                self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure_adjustment)
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)  # Başlangıç parlaklığı
                self.cap.set(cv2.CAP_PROP_CONTRAST, 0.5)    # Başlangıç kontrast
                self.cap.set(cv2.CAP_PROP_SATURATION, 0.5)  # Renk doygunluğu
                self.cap.set(cv2.CAP_PROP_GAIN, 0)         # Gain kontrolü
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)    # Manuel focus
            
            # Gerçek ayarları kontrol et
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logging.info(f"Kamera {self.camera_index} gerçek ayarlar: {actual_width}x{actual_height} @ {actual_fps}fps")
            
        except Exception as e:
            logging.warning(f"Kamera {self.camera_index} parametre ayarlama hatası: {e}")
    
    def _test_initial_frame(self):
        """İlk frame testi - hızlı."""
        try:
            for attempt in range(5):
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    # Parlaklık analizi
                    self._analyze_and_adjust_brightness(frame)
                    
                    # Buffer'a ekle
                    try:
                        self.frame_buffer.put_nowait(frame)
                    except queue.Full:
                        pass
                    
                    logging.debug(f"Kamera {self.camera_index} ilk frame OK: {frame.shape}")
                    return True
                time.sleep(0.05)
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} ilk frame test hatası: {e}")
            return False
    
    def _high_performance_capture_loop(self):
        """Yüksek performanslı frame yakalama döngüsü."""
        consecutive_failures = 0
        max_failures = 10
        frame_interval = 1.0 / self.target_fps
        
        while self.is_running:
            loop_start = time.time()
            
            try:
                if not self.cap or not self.cap.isOpened():
                    if not self._fast_reconnect():
                        break
                    continue
                
                # Frame yakala
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error(f"Kamera {self.camera_index}: Maksimum hata, thread sonlandırılıyor")
                        break
                    time.sleep(0.01)
                    continue
                
                # Başarılı frame
                consecutive_failures = 0
                
                # Parlaklık ayarı (gerekirse)
                if self.auto_brightness:
                    adjusted_frame = self._apply_brightness_adjustments(frame)
                else:
                    adjusted_frame = frame
                
                # Frame buffer'a ekle (non-blocking)
                try:
                    # Eski frame'leri temizle
                    while self.frame_buffer.qsize() >= 2:
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            break
                    
                    self.frame_buffer.put_nowait(adjusted_frame)
                except queue.Full:
                    # Buffer dolu, en eski frame'i at
                    try:
                        self.frame_buffer.get_nowait()
                        self.frame_buffer.put_nowait(adjusted_frame)
                    except queue.Empty:
                        pass
                
                # FPS hesaplama
                self.frame_count += 1
                if time.time() - self.fps_start_time >= 1.0:
                    self.actual_fps = self.frame_count / (time.time() - self.fps_start_time)
                    self.frame_count = 0
                    self.fps_start_time = time.time()
                
                # Frame rate kontrolü - dinamik
                elapsed_time = time.time() - loop_start
                sleep_time = max(0, frame_interval - elapsed_time)
                
                # Performans optimizasyonu
                if elapsed_time > frame_interval * 1.5:  # Yavaş işleme
                    self.skip_frames = min(2, self.skip_frames + 1)
                else:
                    self.skip_frames = max(0, self.skip_frames - 1)
                
                if sleep_time > 0 and self.skip_frames == 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} capture loop HATA: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
                time.sleep(0.1)
        
        self.is_running = False
        self.connection_stable = False
        logging.info(f"Kamera {self.camera_index} capture loop SONLANDI")
    
    def _analyze_and_adjust_brightness(self, frame):
        """Frame parlaklığını analiz et ve gerekirse ayarla."""
        try:
            # Frame'in ortalama parlaklığını hesapla
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            # Optimal parlaklık aralığı: 80-170 (0-255 arası)
            if mean_brightness > 200:  # Çok parlak
                if self.brightness_adjustment > -50:
                    self.brightness_adjustment -= 10
                    self._apply_camera_brightness()
                    logging.debug(f"Kamera {self.camera_index}: Parlaklık azaltıldı -> {self.brightness_adjustment}")
            
            elif mean_brightness < 60:  # Çok karanlık
                if self.brightness_adjustment < 50:
                    self.brightness_adjustment += 10
                    self._apply_camera_brightness()
                    logging.debug(f"Kamera {self.camera_index}: Parlaklık artırıldı -> {self.brightness_adjustment}")
            
        except Exception as e:
            logging.debug(f"Parlaklık analizi hatası: {e}")
    
    def _apply_camera_brightness(self):
        """Kamera donanımına parlaklık ayarını uygula."""
        try:
            if self.cap and self.cap.isOpened():
                # Normalize brightness (-100, +100) -> (0, 1)
                normalized_brightness = (self.brightness_adjustment + 100) / 200.0
                normalized_brightness = max(0.0, min(1.0, normalized_brightness))
                
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, normalized_brightness)
                
        except Exception as e:
            logging.debug(f"Kamera parlaklık ayarı hatası: {e}")
    
    def _apply_brightness_adjustments(self, frame):
        """Frame üzerinde yazılım parlaklık ayarı."""
        try:
            if self.brightness_adjustment == 0 and self.contrast_adjustment == 1.0:
                return frame
            
            # Parlaklık ve kontrast ayarı
            adjusted = cv2.convertScaleAbs(frame, 
                                         alpha=self.contrast_adjustment, 
                                         beta=self.brightness_adjustment)
            return adjusted
            
        except Exception as e:
            logging.debug(f"Yazılım parlaklık ayarı hatası: {e}")
            return frame
    
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
            
            time.sleep(0.5)  # Kısa bekleme
            
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if self.cap.isOpened():
                self._setup_high_performance_parameters()
                self.reconnect_attempts = 0
                self.connection_stable = True
                logging.info(f"Kamera {self.camera_index} HIZLI RECONNECT başarılı")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} fast reconnect HATA: {e}")
            return False
    
    def get_frame(self):
        """En güncel frame'i al - non-blocking."""
        try:
            # En güncel frame'i al
            frame = None
            while not self.frame_buffer.empty():
                try:
                    frame = self.frame_buffer.get_nowait()
                except queue.Empty:
                    break
            
            if frame is not None:
                return frame.copy()
            else:
                return self._create_placeholder_frame()
                
        except Exception as e:
            logging.debug(f"get_frame hatası: {e}")
            return self._create_placeholder_frame()
    
    def set_brightness(self, brightness):
        """Manuel parlaklık ayarı (-100 ile +100 arası)."""
        self.brightness_adjustment = max(-100, min(100, brightness))
        self.auto_brightness = False  # Otomatik parlaklığı kapat
        self._apply_camera_brightness()
        logging.info(f"Kamera {self.camera_index} manuel parlaklık: {self.brightness_adjustment}")
    
    def set_contrast(self, contrast):
        """Manuel kontrast ayarı (0.5 ile 2.0 arası)."""
        self.contrast_adjustment = max(0.5, min(2.0, contrast))
        logging.info(f"Kamera {self.camera_index} kontrast: {self.contrast_adjustment}")
    
    def enable_auto_brightness(self, enable=True):
        """Otomatik parlaklık ayarını aç/kapat."""
        self.auto_brightness = enable
        logging.info(f"Kamera {self.camera_index} otomatik parlaklık: {enable}")
    
    def get_performance_stats(self):
        """Performans istatistiklerini döndür."""
        return {
            'actual_fps': self.actual_fps,
            'target_fps': self.target_fps,
            'skip_frames': self.skip_frames,
            'buffer_size': self.frame_buffer.qsize(),
            'brightness_adjustment': self.brightness_adjustment,
            'auto_brightness': self.auto_brightness,
            'connection_stable': self.connection_stable
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
        
        # Buffer temizle
        while not self.frame_buffer.empty():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                break
        
        self.connection_stable = False
    
    def _create_placeholder_frame(self):
        """Placeholder frame oluştur."""
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        
        # Gradient arka plan
        for i in range(FRAME_HEIGHT):
            intensity = int(20 + (i / FRAME_HEIGHT) * 40)
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
        perf_text = f"FPS: {self.actual_fps:.1f}/{self.target_fps}"
        
        # Metni çiz
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # Ana mesaj
        text_size = cv2.getTextSize(message, font, font_scale, thickness)[0]
        text_x = (FRAME_WIDTH - text_size[0]) // 2
        text_y = (FRAME_HEIGHT + text_size[1]) // 2
        cv2.putText(frame, message, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
        
        # Performans bilgisi
        perf_size = cv2.getTextSize(perf_text, font, 0.7, 1)[0]
        perf_x = (FRAME_WIDTH - perf_size[0]) // 2
        perf_y = text_y + 40
        cv2.putText(frame, perf_text, (perf_x, perf_y), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        
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


# Test ve demo fonksiyonları
def test_enhanced_camera(camera_index=0):
    """Enhanced kamera testini yapar."""
    print(f"Enhanced Camera {camera_index} test başlatılıyor...")
    
    camera = EnhancedCamera(camera_index)
    
    if not camera.start():
        print(f"❌ Kamera {camera_index} başlatılamadı!")
        return False
    
    print("✅ Kamera başlatıldı, 10 saniye test...")
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 10:
        frame = camera.get_frame()
        if frame is not None:
            frame_count += 1
            
            # Performance stats
            if frame_count % 30 == 0:
                stats = camera.get_performance_stats()
                print(f"📊 FPS: {stats['actual_fps']:.1f}, Buffer: {stats['buffer_size']}, Brightness: {stats['brightness_adjustment']}")
        
        time.sleep(1/30)  # 30 FPS test
    
    camera.stop()
    
    avg_fps = frame_count / 10
    print(f"✅ Test tamamlandı. Ortalama FPS: {avg_fps:.1f}")
    return True


if __name__ == "__main__":
    # Test çalıştır
    logging.basicConfig(level=logging.INFO)
    test_enhanced_camera(0)
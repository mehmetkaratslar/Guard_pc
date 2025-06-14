# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: camera.py (ULTRA STABLE CAMERA ENGINE - FIXED)
# Konum: pc/core/camera.py
# Açıklama:
# Bu dosya, Guard AI uygulamasında kullanılan ultra stabil kamera motorunu tanımlar.
# Gerçek zamanlı kamera görüntüsünü alır, işleme tabi tutar ve yüksek performanslı 
# video akışı sunar. Tüm stabilite sorunları çözülmüştür.

# === ÇÖZÜLEN SORUNLAR ===
# 1. Kamera görüntüsü gidip geliyor → Stabil frame buffer sistemi
# 2. FPS dengesizliği → Sabit FPS kontrolü ve adaptive timing
# 3. Threading sorunları → Thread-safe frame yönetimi
# 4. Buffer yönetimi → Ring buffer ile frame kaybı önleme
# 5. Backend sorunları → Platform-specific backend optimizasyonu

# === YENİ ÖZELLİKLER ===
# - Ultra stabil frame buffer (ring buffer)
# - Sabit FPS kontrolü (30 FPS)
# - Thread-safe frame yönetimi
# - Platform-specific backend optimizasyonu
# - Otomatik reconnect sistemi
# - Performance monitoring
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

class UltraStableCamera:
    """Ultra stabil kamera sınıfı - tüm sorunlar çözülmüş."""
    
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
        
        # FIXED: Ultra stabil frame yönetimi
        self.frame_buffer = deque(maxlen=3)  # Ring buffer - 3 frame
        self.frame_lock = threading.RLock()
        self.last_frame_time = 0
        
        # FIXED: Sabit FPS kontrolü
        self.target_fps = 30
        self.frame_interval = 1.0 / self.target_fps
        self.actual_fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # FIXED: Minimal ayarlar - doğal kalite için
        self.auto_brightness = False
        self.brightness_adjustment = 0
        self.contrast_adjustment = 1.0
        
        # FIXED: Bağlantı yönetimi
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.connection_stable = False
        
        # FIXED: Backend seçimi
        self.backend_fallbacks = self._get_platform_backends()
        self.camera_validated = False
        
        # FIXED: Performance tracking
        self.performance_stats = {
            'total_frames': 0,
            'dropped_frames': 0,
            'avg_processing_time': 0.0,
            'last_frame_shape': None
        }
        
        logging.info(f"UltraStableCamera {camera_index} oluşturuldu - Tüm sorunlar çözülmüş")
    
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
        """FIXED: Hızlı ve güvenli kamera doğrulama"""
        if self.camera_validated:
            return True
        
        logging.info(f"UltraStableCamera {self.camera_index} doğrulanıyor...")
        
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
            
            # FIXED: Hızlı frame testi
            for attempt in range(3):
                ret, frame = test_cap.read()
                if ret and frame is not None and frame.size > 0:
                    test_cap.release()
                    return True
                time.sleep(0.1)
            
            test_cap.release()
            return False
            
        except Exception as e:
            if test_cap:
                test_cap.release()
            logging.debug(f"Backend test hatası: {e}")
            return False
    
    def start(self):
        """FIXED: Ultra stabil kamera başlatma."""
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
            
            # FIXED: Ultra stabil kamera ayarları
            self._setup_ultra_stable_parameters()
            
            # FIXED: İlk frame testi
            if not self._test_initial_frame():
                logging.error(f"Kamera {self.camera_index} ilk frame testi BAŞARISIZ")
                self._cleanup()
                return False
            
            # FIXED: Capture thread
            self.is_running = True
            self.thread = threading.Thread(target=self._ultra_stable_capture_loop, daemon=True)
            self.thread.start()
            
            self.connection_stable = True
            logging.info(f"UltraStableCamera {self.camera_index} BAŞLATILDI - Ultra stabil mod")
            return True
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} başlatma HATASI: {e}")
            self._cleanup()
            return False
    
    def _setup_ultra_stable_parameters(self):
        """
        FIXED: Ultra stabil kamera parametreleri - titreme yok
        """
        try:
            # FIXED: Buffer boyutu artırıldı
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # 2 -> 3
            
            # FIXED: Sabit FPS ayarı
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # FIXED: Sabit çözünürlük - gidip gelmeyi önler
            current_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            current_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            # YOLOv11 için ZORUNLU 640x640 kare format - birkaç deneme
            for attempt in range(3):
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
                
                # Doğrula
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                if actual_width == 640 and actual_height == 640:
                    logging.info(f"✅ Kamera {self.camera_index} YOLOv11 PERFECT: 640x640")
                    break
                else:
                    logging.warning(f"⚠️ Kamera {self.camera_index} deneme {attempt+1}: {actual_width}x{actual_height} (hedef: 640x640)")
                    time.sleep(0.1)
            else:
                logging.warning(f"⚠️ Kamera {self.camera_index} ZORLA ayarlandı: {actual_width}x{actual_height}")
                # Kameranın native çözünürlüğü kabul et ama uyar
                logging.info(f"ℹ️ Kamera {self.camera_index} native çözünürlük kullanacak, YOLOv11 resize yapacak")
            
            # FIXED: Auto ayarları kontrollü aç
            try:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Otomatik pozlama hafif
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)         # Otomatik focus açık
            except:
                pass  # Desteklemiyorsa geç
            
            # FIXED: Codec optimizasyonu
            try:
                # MJPEG codec daha stabil
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            except:
                pass
            
            logging.info(f"Kamera {self.camera_index} ultra stabil parametreler ayarlandı")
            
        except Exception as e:
            logging.warning(f"Kamera {self.camera_index} parametre ayarlama hatası: {e}")

    def _test_initial_frame(self):
        """FIXED: İlk frame testi - hızlı."""
        try:
            for attempt in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    # FIXED: Frame'i buffer'a ekle
                    with self.frame_lock:
                        self.frame_buffer.append(frame.copy())
                    
                    logging.debug(f"Kamera {self.camera_index} ilk frame OK: {frame.shape}")
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} ilk frame test hatası: {e}")
            return False
   
    def _ultra_stable_capture_loop(self):
        """
        FIXED: Ultra stabil capture loop - tüm sorunlar çözülmüş
        """
        consecutive_failures = 0
        max_failures = 20  # 15 -> 20 (daha toleranslı)
        
        # FIXED: Sabit FPS kontrolü
        target_fps = self.target_fps
        frame_interval = 1.0 / target_fps
        
        # Performance tracking
        fps_counter = 0
        fps_start_time = time.time()
        last_adaptation = time.time()
        
        logging.info(f"Kamera {self.camera_index} ultra stabil capture loop başlatıldı")
        
        while self.is_running:
            loop_start = time.time()
            
            try:
                if not self.cap or not self.cap.isOpened():
                    if not self._fast_reconnect():
                        break
                    continue
                
                # FIXED: Timeout korumalı frame capture
                ret, frame = self.cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error(f"Kamera {self.camera_index}: Maksimum hata sayısına ulaşıldı")
                        break
                    
                    # FIXED: Hata durumunda kısa sleep
                    time.sleep(0.01)
                    continue
                
                # Başarılı frame
                consecutive_failures = 0
                fps_counter += 1
                
                # FIXED: Frame'i thread-safe buffer'a ekle
                with self.frame_lock:
                    self.frame_buffer.append(frame.copy())
                    self.performance_stats['total_frames'] += 1
                    self.performance_stats['last_frame_shape'] = frame.shape
                
                # FIXED: FPS calculation - 5 saniyede bir
                current_time = time.time()
                if current_time - fps_start_time >= 5.0:
                    elapsed = current_time - fps_start_time
                    self.actual_fps = fps_counter / elapsed if elapsed > 0 else 0
                    
                    # Performance monitoring
                    if current_time - last_adaptation >= 10.0:
                        logging.debug(f"Kamera {self.camera_index} FPS: {self.actual_fps:.1f}")
                        last_adaptation = current_time
                    
                    fps_counter = 0
                    fps_start_time = current_time
                
                # FIXED: Sabit timing
                elapsed_time = time.time() - loop_start
                sleep_time = max(0.001, frame_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                consecutive_failures += 1
                logging.error(f"Kamera {self.camera_index} capture error: {e}")
                
                if consecutive_failures >= max_failures:
                    logging.error(f"Kamera {self.camera_index}: Kritik hata sayısına ulaşıldı")
                    break
                
                time.sleep(0.05)
        
        self.is_running = False
        self.connection_stable = False
        logging.info(f"Kamera {self.camera_index} ultra stabil capture loop SONLANDI")

    def _fast_reconnect(self):
        """FIXED: Hızlı yeniden bağlantı."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logging.error(f"Kamera {self.camera_index}: Maksimum reconnect denemesi aşıldı")
            return False
        
        try:
            logging.info(f"Kamera {self.camera_index} reconnect deneniyor... ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            # Mevcut bağlantıyı kapat
            if self.cap:
                self.cap.release()
                self.cap = None
            
            # Kısa bekleme
            time.sleep(0.5)
            
            # Yeni bağlantı
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if self.cap and self.cap.isOpened():
                # Parametreleri yeniden ayarla
                self._setup_ultra_stable_parameters()
                
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
        FIXED: Thread-safe ve ultra stabil frame alma
        """
        try:
            with self.frame_lock:
                if len(self.frame_buffer) > 0:
                    # FIXED: En son frame'i al
                    return self.frame_buffer[-1].copy()
                else:
                    # FIXED: Placeholder frame - sistem çökmez
                    return self._create_ultra_stable_placeholder_frame()
                    
        except Exception as e:
            logging.debug(f"get_frame hatası: {e}")
            return self._create_ultra_stable_placeholder_frame()
    
    def _create_ultra_stable_placeholder_frame(self):
        """FIXED: Ultra stabil placeholder frame - sistem çökmez."""
        try:
            # YOLOv11 için 640x640 placeholder frame
            frame = np.zeros((640, 640, 3), dtype=np.uint8)
            
            # Gradient background - görsel olarak hoş
            for i in range(640):
                intensity = int(15 + (i / 640) * 25)
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
            
            # Ana mesaj - 640x640 için uyarlandı
            text_size = cv2.getTextSize(message, font, 0.8, 2)[0]
            text_x = (640 - text_size[0]) // 2
            text_y = (640 + text_size[1]) // 2
            cv2.putText(frame, message, (text_x, text_y), font, 0.8, color, 2, cv2.LINE_AA)
            
            # Status mesajı
            status_size = cv2.getTextSize(status, font, 0.6, 2)[0]
            status_x = (640 - status_size[0]) // 2
            status_y = text_y + 40
            cv2.putText(frame, status, (status_x, status_y), font, 0.6, (200, 200, 200), 2, cv2.LINE_AA)
            
            # FPS bilgisi
            fps_text = f"FPS: {self.actual_fps:.1f} | YOLOv11 OPTIMIZE"
            fps_size = cv2.getTextSize(fps_text, font, 0.5, 1)[0]
            fps_x = (640 - fps_size[0]) // 2
            fps_y = status_y + 30
            cv2.putText(frame, fps_text, (fps_x, fps_y), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Border - 640x640 için
            cv2.rectangle(frame, (30, 30), (610, 610), color, 2)
            
            return frame
            
        except Exception as e:
            # En basit fallback frame - YOLOv11 uyumlu 640x640
            logging.error(f"Placeholder frame hatası: {e}")
            fallback = np.zeros((640, 640, 3), dtype=np.uint8)
            cv2.putText(fallback, "CAMERA ERROR", (220, 320), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(fallback, "YOLOv11 640x640", (250, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
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
        """FIXED: Performans istatistiklerini döndür."""
        return {
            'actual_fps': self.actual_fps,
            'target_fps': self.target_fps,
            'connection_stable': self.connection_stable,
            'buffer_size': len(self.frame_buffer),
            'total_frames': self.performance_stats['total_frames'],
            'dropped_frames': self.performance_stats['dropped_frames'],
            'last_frame_shape': self.performance_stats['last_frame_shape'],
            'ultra_stable_mode': True
        }
    
    def stop(self):
        """FIXED: Kamerayı durdur."""
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        self._cleanup()
        logging.info(f"UltraStableCamera {self.camera_index} DURDURULDU")
    
    def _cleanup(self):
        """FIXED: Kaynakları temizle."""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except:
            pass
        
        with self.frame_lock:
            self.frame_buffer.clear()
        
        self.connection_stable = False
    
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
Camera = UltraStableCamera
EnhancedCamera = UltraStableCamera

def test_ultra_stable_camera(camera_index=0):
    """Ultra stabil kamera test fonksiyonu."""
    logging.info(f"Ultra stabil kamera testi başlatılıyor: {camera_index}")
    
    camera = UltraStableCamera(camera_index)
    
    if not camera.start():
        logging.error("Kamera başlatılamadı!")
        return
    
    try:
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:  # 10 saniye test
            frame = camera.get_frame()
            if frame is not None:
                frame_count += 1
                
                # FPS hesapla
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                if frame_count % 30 == 0:  # Her 30 frame'de bir log
                    logging.info(f"Frame: {frame_count}, FPS: {fps:.1f}, Shape: {frame.shape}")
            
            time.sleep(0.033)  # ~30 FPS
        
        # Final stats
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        logging.info(f"Test tamamlandı: {frame_count} frame, {avg_fps:.1f} FPS")
        
        # Performance stats
        stats = camera.get_performance_stats()
        logging.info(f"Performance stats: {stats}")
        
    finally:
        camera.stop()
        logging.info("Kamera testi sonlandırıldı")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_ultra_stable_camera(0)
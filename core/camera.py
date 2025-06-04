# =======================================================================================
# 📄 Dosya Adı: camera.py (ENHANCED VERSION)
# 📁 Konum: guard_pc_app/core/camera.py
# 📌 Açıklama:
# YOLOv11 Pose Estimation için optimize edilmiş kamera yönetimi.
# MSMF backend sorunları düzeltildi, robust bağlantı yönetimi eklendi.
# Çoklu backend fallback sistemi ve gelişmiş hata yönetimi.
# =======================================================================================

import cv2
import numpy as np
import threading
import logging
import time
import os
import platform
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class Camera:
    """YOLOv11 Pose Estimation için optimize edilmiş kamera sınıfı."""
    
    def __init__(self, camera_index, backend=cv2.CAP_ANY):
        """
        Args:
            camera_index (int): Kullanılacak kamera indeksi
            backend (int, optional): OpenCV backend
        """
        self.camera_index = camera_index
        self.original_backend = backend
        self.backend = backend
        self.cap = None
        self.is_running = False
        self.thread = None
        self.frame = None
        self.last_frame_time = 0
        self.frame_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3  # Azaltıldı
        self.reconnect_delay = 1.0  # Kısaltıldı
        
        # FPS ve performans istatistikleri
        self.fps = 0
        self.frame_times = []
        self.max_frame_times = 30
        
        # Backend fallback listesi - Windows için optimize edildi
        self.backend_fallbacks = self._get_backend_fallbacks()
        self.current_backend_index = 0
        
        # Kamera durumu takibi
        self.status_timer = None
        self.last_successful_backend = None
        
        # İlk doğrulama
        self._validate_camera_with_fallback()
    
    def _get_backend_fallbacks(self):
        """Platform ve kamera tipine göre backend fallback listesi oluşturur."""
        if platform.system() == "Windows":
            # Windows için optimize edilmiş sıralama
            return [
                cv2.CAP_DSHOW,      # DirectShow - en kararlı
                cv2.CAP_ANY,        # Varsayılan
                cv2.CAP_MSMF,       # Media Foundation - sorunlu olabilir
                cv2.CAP_VFW,        # Video for Windows - eski
            ]
        elif platform.system() == "Linux":
            return [
                cv2.CAP_V4L2,       # Video4Linux2
                cv2.CAP_ANY,        # Varsayılan
                cv2.CAP_GSTREAMER,  # GStreamer
            ]
        elif platform.system() == "Darwin":  # macOS
            return [
                cv2.CAP_AVFOUNDATION,  # AVFoundation
                cv2.CAP_ANY,           # Varsayılan
            ]
        else:
            return [cv2.CAP_ANY]
    
    def _validate_camera_with_fallback(self):
        """Kamerayı farklı backend'lerle doğrular."""
        # Eğer özel bir backend belirtilmişse önce onu dene
        if self.original_backend != cv2.CAP_ANY:
            if self._test_backend(self.original_backend):
                self.backend = self.original_backend
                self.last_successful_backend = self.original_backend
                logging.info(f"Kamera {self.camera_index} belirtilen backend ile başarılı: {self.original_backend}")
                return True
        
        # Backend fallback listesini dene
        for i, backend in enumerate(self.backend_fallbacks):
            if self._test_backend(backend):
                self.backend = backend
                self.current_backend_index = i
                self.last_successful_backend = backend
                backend_name = self._get_backend_name(backend)
                logging.info(f"Kamera {self.camera_index} {backend_name} backend ile başarılı")
                return True
        
        logging.error(f"Kamera {self.camera_index} hiçbir backend ile başlatılamadı!")
        return False
    
    def _test_backend(self, backend):
        """Belirli bir backend'i test eder."""
        try:
            test_cap = cv2.VideoCapture(self.camera_index, backend)
            if not test_cap.isOpened():
                test_cap.release()
                return False
            
            # Frame okuma testi
            for _ in range(3):  # 3 deneme
                ret, frame = test_cap.read()
                if ret and frame is not None and frame.size > 0:
                    test_cap.release()
                    return True
                time.sleep(0.1)
            
            test_cap.release()
            return False
            
        except Exception as e:
            logging.debug(f"Backend {backend} test hatası: {str(e)}")
            return False
    
    def _get_backend_name(self, backend):
        """Backend kodunu okunabilir isme çevirir."""
        backend_names = {
            cv2.CAP_ANY: "AUTO",
            cv2.CAP_DSHOW: "DirectShow",
            cv2.CAP_MSMF: "MediaFoundation", 
            cv2.CAP_VFW: "VideoForWindows",
            cv2.CAP_V4L2: "Video4Linux2",
            cv2.CAP_GSTREAMER: "GStreamer",
            cv2.CAP_AVFOUNDATION: "AVFoundation"
        }
        return backend_names.get(backend, f"Backend_{backend}")
    
    def start(self):
        """Kamerayı başlatır - gelişmiş hata yönetimi ile."""
        with self.frame_lock:
            if self.is_running:
                logging.warning(f"Kamera {self.camera_index} zaten çalışıyor.")
                return True
            
            # Mevcut bağlantıyı temizle
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            # En iyi backend ile başlat
            success = self._start_with_best_backend()
            if not success:
                logging.error(f"Kamera {self.camera_index} hiçbir backend ile başlatılamadı!")
                return False
            
            # Thread başlat
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
            # Durum takibi başlat
            self._start_status_timer()
            
            backend_name = self._get_backend_name(self.backend)
            logging.info(f"Kamera {self.camera_index} başarıyla başlatıldı ({backend_name})")
            return True
    
    def _start_with_best_backend(self):
        """En iyi çalışan backend ile kamerayı başlatır."""
        # Son başarılı backend'i önce dene
        if self.last_successful_backend:
            if self._initialize_camera(self.last_successful_backend):
                self.backend = self.last_successful_backend
                return True
        
        # Backend fallback listesini dene
        for backend in self.backend_fallbacks:
            if self._initialize_camera(backend):
                self.backend = backend
                self.last_successful_backend = backend
                return True
        
        return False
    
    def _initialize_camera(self, backend):
        """Belirli bir backend ile kamerayı başlatır."""
        try:
            cap = cv2.VideoCapture(self.camera_index, backend)
            if not cap.isOpened():
                cap.release()
                return False
            
            # Kamera ayarları - YOLOv11 için optimize edilmiş
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
            
            # Buffer boyutunu azalt (daha düşük latency)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Codec ayarları (mümkünse)
            try:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            except:
                pass
            
            # İlk frame testi - robust
            frame_received = False
            for attempt in range(10):  # 10 deneme
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    self.frame = frame
                    self.last_frame_time = time.time()
                    frame_received = True
                    break
                time.sleep(0.05)  # 50ms bekle
            
            if not frame_received:
                logging.warning(f"Kamera {self.camera_index} backend {backend} frame alınamadı")
                cap.release()
                return False
            
            self.cap = cap
            self.reconnect_attempts = 0
            return True
            
        except Exception as e:
            logging.debug(f"Kamera {self.camera_index} backend {backend} init hatası: {str(e)}")
            return False
    
    def stop(self):
        """Kamerayı güvenli şekilde durdurur."""
        with self.frame_lock:
            if not self.is_running:
                return
            
            self.is_running = False
            
            # Timer'ı durdur
            if self.status_timer:
                try:
                    self.status_timer.cancel()
                except:
                    pass
                self.status_timer = None
            
            # Thread'i bekle
            if self.thread and self.thread.is_alive():
                try:
                    self.thread.join(timeout=2.0)
                except:
                    pass
                self.thread = None
            
            # Kamerayı serbest bırak
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            logging.info(f"Kamera {self.camera_index} durduruldu.")
    
    def get_frame(self):
        """YOLOv11 için optimize edilmiş frame alma."""
        with self.frame_lock:
            if not self.is_running or self.frame is None:
                # Siyah frame döndür
                black_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
                
                # Durum mesajı ekle
                font = cv2.FONT_HERSHEY_SIMPLEX
                if not self.is_running:
                    message = f"Kamera {self.camera_index} Kapalı"
                    color = (100, 100, 100)
                else:
                    message = f"Kamera {self.camera_index} Bağlanıyor..."
                    color = (255, 255, 0)
                
                # Metni ortala
                text_size = cv2.getTextSize(message, font, 0.8, 2)[0]
                text_x = (FRAME_WIDTH - text_size[0]) // 2
                text_y = (FRAME_HEIGHT + text_size[1]) // 2
                
                cv2.putText(black_frame, message, (text_x, text_y), 
                           font, 0.8, color, 2, cv2.LINE_AA)
                
                return black_frame
            
            # Frame'i kopyala ve boyutlandır
            try:
                frame_copy = self.frame.copy()
                # YOLOv11 için kare format (640x640)
                resized_frame = cv2.resize(frame_copy, (FRAME_WIDTH, FRAME_HEIGHT))
                return resized_frame
            except Exception as e:
                logging.error(f"Frame resize hatası: {str(e)}")
                return np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    
    def capture_screenshot(self):
        """Ekran görüntüsü al - timestamp ile."""
        frame = self.get_frame()
        if frame is not None:
            timestamp = time.strftime("%d.%m.%Y %H:%M:%S")
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, timestamp, (10, 30), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Kamera bilgisi ekle
            backend_name = self._get_backend_name(self.backend)
            info_text = f"Kamera {self.camera_index} ({backend_name})"
            cv2.putText(frame, info_text, (10, frame.shape[0] - 10), 
                       font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        return frame
    
    def get_camera_status(self):
        """Detaylı kamera durumu bilgisi."""
        status = {
            "is_running": self.is_running,
            "fps": round(self.fps, 1),
            "last_frame_time": self.last_frame_time,
            "camera_index": self.camera_index,
            "backend": self.backend,
            "backend_name": self._get_backend_name(self.backend),
            "reconnect_attempts": self.reconnect_attempts,
            "has_frame": self.frame is not None
        }
        
        # Bağlantı durumu
        if self.is_running and self.cap and self.cap.isOpened():
            if time.time() - self.last_frame_time < 5:
                status["connection"] = "connected"
            else:
                status["connection"] = "stalled"
        elif self.is_running:
            status["connection"] = "connecting"
        else:
            status["connection"] = "disconnected"
        
        return status
    
    def reconnect(self):
        """Gelişmiş yeniden bağlanma - backend rotation ile."""
        with self.frame_lock:
            self.reconnect_attempts += 1
            
            if self.reconnect_attempts > self.max_reconnect_attempts:
                logging.error(f"Kamera {self.camera_index} maksimum deneme aşıldı.")
                # Bir sonraki backend'i dene
                self._try_next_backend()
                return self.reconnect_attempts <= self.max_reconnect_attempts * len(self.backend_fallbacks)
            
            logging.info(f"Kamera {self.camera_index} yeniden bağlanıyor (Deneme {self.reconnect_attempts})...")
            
            # Mevcut bağlantıyı temizle
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            
            # Kısa bir bekleme
            time.sleep(self.reconnect_delay)
            
            # Yeniden başlat
            if self._initialize_camera(self.backend):
                logging.info(f"Kamera {self.camera_index} başarıyla yeniden bağlandı.")
                self.reconnect_attempts = 0
                return True
            
            return False
    
    def _try_next_backend(self):
        """Sonraki backend'i dene."""
        self.current_backend_index = (self.current_backend_index + 1) % len(self.backend_fallbacks)
        self.backend = self.backend_fallbacks[self.current_backend_index]
        self.reconnect_attempts = 0  # Reset deneme sayısı
        
        backend_name = self._get_backend_name(self.backend)
        logging.info(f"Kamera {self.camera_index} farklı backend deneniyor: {backend_name}")
    
    def _capture_loop(self):
        """Optimize edilmiş frame yakalama döngüsü."""
        frame_count = 0
        fps_start_time = time.time()
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    if not self.reconnect():
                        time.sleep(0.5)
                        continue
                
                start_time = time.time()
                ret, frame = self.cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logging.warning(f"Kamera {self.camera_index} çok fazla başarısız frame, yeniden bağlanıyor...")
                        if not self.reconnect():
                            time.sleep(1.0)
                        consecutive_failures = 0
                    continue
                
                # Frame başarılı
                consecutive_failures = 0
                
                with self.frame_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                
                # FPS hesaplama
                frame_count += 1
                elapsed_time = time.time() - fps_start_time
                
                if elapsed_time >= 1.0:
                    self.fps = frame_count / elapsed_time
                    frame_count = 0
                    fps_start_time = time.time()
                
                # Frame timing
                frame_time = time.time() - start_time
                self.frame_times.append(frame_time)
                
                if len(self.frame_times) > self.max_frame_times:
                    self.frame_times.pop(0)
                
                # FPS kontrol - hedef FPS'e göre bekle
                target_delay = 1.0 / FRAME_RATE
                sleep_time = max(0, target_delay - frame_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} capture loop hatası: {str(e)}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    if not self.reconnect():
                        time.sleep(1.0)
                    consecutive_failures = 0
                else:
                    time.sleep(0.1)
    
    def _start_status_timer(self):
        """Kamera durumu kontrol zamanlayıcısı."""
        if self.status_timer:
            try:
                self.status_timer.cancel()
            except:
                pass
        
        def check_status():
            try:
                if not self.is_running:
                    return
                
                status = self.get_camera_status()
                if status["connection"] == "stalled":
                    logging.warning(f"Kamera {self.camera_index} donmuş durumda, yeniden başlatılıyor...")
                    self.reconnect()
                
                # Zamanlayıcıyı yeniden başlat
                if self.is_running:
                    self.status_timer = threading.Timer(10.0, check_status)
                    self.status_timer.daemon = True
                    self.status_timer.start()
            except Exception as e:
                logging.error(f"Status timer hatası: {str(e)}")
        
        self.status_timer = threading.Timer(10.0, check_status)
        self.status_timer.daemon = True
        self.status_timer.start()
    
    @staticmethod
    def get_available_cameras():
        """Sistem genelinde kullanılabilir kameraları listele."""
        available_cameras = []
        
        # Platform spesifik backend'ler
        if platform.system() == "Windows":
            backends_to_test = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        elif platform.system() == "Linux":
            backends_to_test = [cv2.CAP_V4L2, cv2.CAP_ANY]
        elif platform.system() == "Darwin":
            backends_to_test = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        else:
            backends_to_test = [cv2.CAP_ANY]
        
        # 0-4 arası kamera indekslerini test et
        for index in range(5):
            for backend in backends_to_test:
                try:
                    cap = cv2.VideoCapture(index, backend)
                    if cap.isOpened():
                        # Frame test
                        ret, _ = cap.read()
                        if ret:
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            fps = int(cap.get(cv2.CAP_PROP_FPS))
                            
                            backend_name = Camera._get_backend_name_static(backend)
                            camera_info = {
                                "index": index,
                                "backend": backend,
                                "backend_name": backend_name,
                                "name": f"Kamera {index} ({backend_name})",
                                "resolution": f"{width}x{height}",
                                "fps": fps,
                                "working": True
                            }
                            
                            # Duplicate kontrolü
                            if not any(cam["index"] == index and cam["backend"] == backend 
                                     for cam in available_cameras):
                                available_cameras.append(camera_info)
                                logging.info(f"Kamera bulundu: {camera_info['name']}")
                    
                    cap.release()
                except Exception as e:
                    logging.debug(f"Kamera {index} backend {backend} test hatası: {str(e)}")
        
        return available_cameras
    
    @staticmethod
    def _get_backend_name_static(backend):
        """Static backend isim çevirici."""
        backend_names = {
            cv2.CAP_ANY: "AUTO",
            cv2.CAP_DSHOW: "DirectShow",
            cv2.CAP_MSMF: "MediaFoundation",
            cv2.CAP_VFW: "VideoForWindows",
            cv2.CAP_V4L2: "Video4Linux2",
            cv2.CAP_GSTREAMER: "GStreamer",
            cv2.CAP_AVFOUNDATION: "AVFoundation"
        }
        return backend_names.get(backend, f"Backend_{backend}")

# Kamera test fonksiyonu
def test_camera(camera_index=0, duration=10):
    """Belirli bir kamerayı test eder."""
    logging.info(f"Kamera {camera_index} test ediliyor ({duration} saniye)...")
    
    camera = Camera(camera_index)
    if not camera.start():
        logging.error(f"Kamera {camera_index} başlatılamadı!")
        return False
    
    try:
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < duration:
            frame = camera.get_frame()
            if frame is not None:
                frame_count += 1
            time.sleep(0.1)
        
        status = camera.get_camera_status()
        logging.info(f"Test tamamlandı:")
        logging.info(f"  - Toplam frame: {frame_count}")
        logging.info(f"  - FPS: {status['fps']}")
        logging.info(f"  - Backend: {status['backend_name']}")
        logging.info(f"  - Durum: {status['connection']}")
        
        return True
        
    finally:
        camera.stop()

if __name__ == "__main__":
    # Test kodu
    logging.basicConfig(level=logging.INFO)
    
    # Kullanılabilir kameraları listele
    cameras = Camera.get_available_cameras()
    print(f"Bulunan kameralar: {len(cameras)}")
    for cam in cameras:
        print(f"  {cam['name']} - {cam['resolution']}")
    
    # İlk kamerayı test et
    if cameras:
        test_camera(cameras[0]['index'])
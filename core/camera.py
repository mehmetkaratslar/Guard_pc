# =======================================================================================
# 📄 Dosya Adı: camera.py
# 📁 Konum: guard_pc_app/core/camera.py
# 📌 Açıklama:
# Kamera işlemlerini yöneten sınıf.
# Çoklu kamera desteği optimize edildi, CAMERA_CONFIGS ile uyumlu.
# Harici kamera başlatma için ek hata yönetimi eklendi.
# CAMERA_INDEX bağımlılığı kaldırıldı.
# start ve get_frame’e ayrıntılı loglama eklendi.
# 🔗 Bağlantılı Dosyalar:
# - config/settings.py: Kamera ayarları (CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE)
# - ui/dashboard.py: Çoklu kamera önizleme
# - core/fall_detection.py: Kamera çerçevelerini işleme
# =======================================================================================

import cv2
import numpy as np
import threading
import logging
import time
import os
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class Camera:
    """Kamera işlemlerini yöneten sınıf."""
    
    def __init__(self, camera_index, backend=cv2.CAP_ANY):
        """
        Args:
            camera_index (int): Kullanılacak kamera indeksi
            backend (int, optional): OpenCV backend (örneğin, cv2.CAP_MSMF, cv2.CAP_DSHOW)
        """
        self.camera_index = camera_index
        self.backend = backend
        self.cap = None
        self.is_running = False
        self.thread = None
        self.frame = None
        self.last_frame_time = 0
        self.frame_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
        # FPS ve performans istatistikleri
        self.fps = 0
        self.frame_times = []
        self.max_frame_times = 30
        
        # Kamera bulunabilirliğini kontrol et
        self._validate_camera()
        
        # Kamera durumu takibi için zamanlayıcı
        self.status_timer = None
    
    def _validate_camera(self):
        """Kamera kullanılabilirliğini kontrol eder."""
        try:
            temp_cap = cv2.VideoCapture(self.camera_index, self.backend)
            if not temp_cap.isOpened():
                logging.warning(f"Kamera {self.camera_index} (backend: {self.backend}) açılamadı.")
                temp_cap.release()
                return False
            # Ekstra kontrol: İlk kareyi oku
            ret, _ = temp_cap.read()
            if not ret:
                logging.warning(f"Kamera {self.camera_index} (backend: {self.backend}) kare okunamadı.")
                temp_cap.release()
                return False
            temp_cap.release()
            logging.info(f"Kamera {self.camera_index} (backend: {self.backend}) kullanılabilir.")
            return True
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} doğrulama hatası: {str(e)}")
            return False
    
    def start(self):
        """Kamerayı başlatır ve kare yakalama thread'ini başlatır."""
        with self.frame_lock:
            if self.is_running:
                logging.warning(f"Kamera {self.camera_index} zaten çalışıyor.")
                return True
            
            try:
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                
                self.cap = cv2.VideoCapture(self.camera_index, self.backend)
                if not self.cap.isOpened():
                    logging.error(f"Kamera {self.camera_index} (backend: {self.backend}) açılamadı.")
                    return False
                
                # Kamera ayarlarını yap
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
                
                # İlk kareyi oku
                for _ in range(5):  # 5 deneme yap
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        break
                    time.sleep(0.1)
                else:
                    logging.error(f"Kamera {self.camera_index} ilk kare okunamadı.")
                    self.cap.release()
                    return False
                
                self.frame = frame
                self.last_frame_time = time.time()
                self.reconnect_attempts = 0
                
                self.is_running = True
                self.thread = threading.Thread(target=self._capture_loop)
                self.thread.daemon = True
                self.thread.start()
                
                self._start_status_timer()
                
                logging.info(f"Kamera {self.camera_index} başlatıldı.")
                return True
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} başlatılırken hata: {str(e)}")
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                return False
    
    def stop(self):
        """Kamerayı ve kare yakalama thread'ini durdurur."""
        with self.frame_lock:
            if not self.is_running:
                logging.warning(f"Kamera {self.camera_index} zaten durmuş durumda.")
                return
            
            self.is_running = False
            
            if self.status_timer:
                self.status_timer.cancel()
                self.status_timer = None
            
            if self.thread:
                try:
                    self.thread.join(timeout=1.0)
                except Exception as e:
                    logging.warning(f"Kamera {self.camera_index} thread durdurulurken hata: {str(e)}")
                self.thread = None
            
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception as e:
                    logging.warning(f"Kamera {self.camera_index} kaynağı serbest bırakılırken hata: {str(e)}")
                self.cap = None
            
            logging.info(f"Kamera {self.camera_index} durduruldu.")
    
    def get_frame(self):
        """En son yakalanan kareyi döndürür ve 640x640 boyutuna ayarlar."""
        with self.frame_lock:
            if self.frame is None or not self.is_running:
                black_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
                font = cv2.FONT_HERSHEY_SIMPLEX
                if not self.is_running:
                    cv2.putText(black_frame, f"Kamera {self.camera_index} Kapalı", (50, FRAME_HEIGHT//2), 
                                font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(black_frame, f"Kamera {self.camera_index} Bağlanıyor...", (50, FRAME_HEIGHT//2), 
                                font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                logging.debug(f"Kamera {self.camera_index} geçerli çerçeve yok.")
                return black_frame
            
            frame_copy = self.frame.copy()
            resized_frame = cv2.resize(frame_copy, (FRAME_WIDTH, FRAME_HEIGHT))
            logging.debug(f"Kamera {self.camera_index} çerçeve alındı: {resized_frame.shape}")
            return resized_frame
    
    def capture_screenshot(self):
        """Anlık ekran görüntüsü alır ve doğru boyuta ayarlar."""
        frame = self.get_frame()
        timestamp = time.strftime("%d.%m.%Y %H:%M:%S")
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, timestamp, (10, 30), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        return frame
    
    def get_camera_status(self):
        """Kamera durumu hakkında bilgi döndürür."""
        status = {
            "is_running": self.is_running,
            "fps": self.fps,
            "last_frame_time": self.last_frame_time,
            "camera_index": self.camera_index,
            "backend": self.backend
        }
        
        if self.is_running and self.cap and self.cap.isOpened():
            status["connection"] = "connected"
        elif self.is_running:
            status["connection"] = "connecting"
        else:
            status["connection"] = "disconnected"
        
        if self.is_running and time.time() - self.last_frame_time > 5:
            status["connection"] = "stalled"
        
        return status
    
    def get_available_cameras(self):
        """Kullanılabilir kameraları tarar ve listeler."""
        available_cameras = []
        
        for config in CAMERA_CONFIGS:
            index = config['index']
            backend = config['backend']
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    # Ekstra kontrol: İlk kareyi oku
                    ret, _ = cap.read()
                    if not ret:
                        logging.warning(f"Kamera {index} (backend: {backend}) kare okunamadı.")
                        cap.release()
                        continue
                    camera_name = config.get('name', f"Kamera {index}")
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    available_cameras.append({
                        "index": index,
                        "name": camera_name,
                        "resolution": f"{width}x{height}",
                        "backend": backend
                    })
                    logging.info(f"Kamera bulundu: {camera_name} (indeks: {index}, backend: {backend})")
                
                cap.release()
            except Exception as e:
                logging.debug(f"Kamera {index} (backend: {backend}) taranırken hata: {str(e)}")
        
        for index in range(5):
            if not any(cam['index'] == index for cam in available_cameras):
                for backend in [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]:
                    try:
                        cap = cv2.VideoCapture(index, backend)
                        if cap.isOpened():
                            ret, _ = cap.read()
                            if not ret:
                                logging.warning(f"Kamera {index} (backend: {backend}) kare okunamadı.")
                                cap.release()
                                continue
                            camera_name = f"Kamera {index}"
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            
                            available_cameras.append({
                                "index": index,
                                "name": camera_name,
                                "resolution": f"{width}x{height}",
                                "backend": backend
                            })
                            logging.info(f"Kamera bulundu: {camera_name} (indeks: {index}, backend: {backend})")
                        
                        cap.release()
                    except Exception as e:
                        logging.debug(f"Kamera {index} (backend: {backend}) taranırken hata: {str(e)}")
        
        if not available_cameras:
            logging.error("Hiçbir kamera bulunamadı!")
        return available_cameras
    
    def change_camera(self, camera_index, backend=None):
        """Kamera kaynağını değiştirir."""
        if self.camera_index == camera_index and self.backend == (backend or self.backend):
            return True
            
        was_running = self.is_running
        if was_running:
            self.stop()
            
        self.camera_index = camera_index
        self.backend = backend if backend is not None else cv2.CAP_ANY
        
        if was_running:
            return self.start()
        return True
    
    def _start_status_timer(self):
        """Kamera durumunu düzenli olarak kontrol eden zamanlayıcı."""
        if self.status_timer:
            self.status_timer.cancel()
            
        def check_status():
            status = self.get_camera_status()
            if status["connection"] == "stalled" and self.is_running:
                logging.warning(f"Kamera {self.camera_index} yanıt vermiyor. Yeniden başlatılıyor...")
                self.reconnect()
                
            if self.is_running:
                self.status_timer = threading.Timer(5.0, check_status)
                self.status_timer.daemon = True
                self.status_timer.start()
        
        self.status_timer = threading.Timer(5.0, check_status)
        self.status_timer.daemon = True
        self.status_timer.start()
    
    def reconnect(self):
        """Kamera bağlantısını yeniden kurar."""
        with self.frame_lock:
            self.reconnect_attempts += 1
            
            if self.reconnect_attempts > self.max_reconnect_attempts:
                logging.error(f"Kamera {self.camera_index} maksimum yeniden bağlanma denemesi aşıldı ({self.max_reconnect_attempts}).")
                self.stop()
                return False
            
            logging.info(f"Kamera {self.camera_index} bağlantısı yeniden kuruluyor (Deneme {self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except:
                    pass
            
            try:
                self.cap = cv2.VideoCapture(self.camera_index, self.backend)
                if not self.cap.isOpened():
                    logging.error(f"Kamera {self.camera_index} (backend: {self.backend}) açılamadı.")
                    time.sleep(self.reconnect_delay)
                    return False
                
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
                
                for _ in range(5):
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        break
                    time.sleep(0.1)
                else:
                    logging.error(f"Kamera {self.camera_index} ilk kare okunamadı.")
                    self.cap.release()
                    return False
                
                self.frame = frame
                self.last_frame_time = time.time()
                self.reconnect_attempts = 0
                
                logging.info(f"Kamera {self.camera_index} bağlantısı başarıyla yeniden kuruldu.")
                return True
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} yeniden bağlanırken hata: {str(e)}")
                time.sleep(self.reconnect_delay)
                return False
    
    def _capture_loop(self):
        """Sürekli olarak kamera karelerini yakalayan thread fonksiyonu."""
        frame_count = 0
        fps_start_time = time.time()
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    logging.warning(f"Kamera {self.camera_index} bağlantısı koptu, yeniden bağlanıyor...")
                    self.reconnect()
                    time.sleep(0.5)
                    continue
                
                start_time = time.time()
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    logging.warning(f"Kamera {self.camera_index} kare okunamadı, yeniden bağlanıyor...")
                    self.reconnect()
                    time.sleep(0.1)
                    continue
                
                with self.frame_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                
                frame_count += 1
                elapsed_time = time.time() - fps_start_time
                
                if elapsed_time >= 1.0:
                    self.fps = frame_count / elapsed_time
                    frame_count = 0
                    fps_start_time = time.time()
                
                frame_time = time.time() - start_time
                self.frame_times.append(frame_time)
                
                if len(self.frame_times) > self.max_frame_times:
                    self.frame_times.pop(0)
                
                target_delay = 1.0 / FRAME_RATE
                sleep_time = max(0, target_delay - frame_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} kare yakalama sırasında hata: {str(e)}")
                self.reconnect()
                time.sleep(0.1)
# guard_pc_app/core/camera.py
import cv2
import numpy as np
import threading
import logging
import time
import os
from config.settings import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class Camera:
    """Kamera işlemlerini yöneten sınıf."""
    
    _instance = None
    _init_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Singleton örneği döndürür."""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
    
    def __init__(self, camera_index=CAMERA_INDEX):
        """
        Args:
            camera_index (int): Kullanılacak kamera indeksi
        """
        # Singleton kontrolü
        if Camera._instance is not None:
            raise RuntimeError("Camera sınıfı zaten başlatılmış. get_instance() methodunu kullanın.")
        
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self.thread = None
        self.frame = None
        self.last_frame_time = 0
        self.frame_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0  # Yeniden bağlanma denemesi arasındaki süre (saniye)
        
        # FPS ve performans istatistikleri
        self.fps = 0
        self.frame_times = []
        self.max_frame_times = 30  # son 30 kare için FPS hesapla
        
        # Kamera bulunabilirliğini kontrol et
        self._validate_camera()
        
        # Kamera durumu takibi için zamanlayıcı
        self.status_timer = None
    
    def _validate_camera(self):
        """Kamera kullanılabilirliğini kontrol eder."""
        try:
            temp_cap = cv2.VideoCapture(self.camera_index)
            if not temp_cap.isOpened():
                logging.warning(f"Kamera {self.camera_index} açılamadı. Başka kameralar deneniyor...")
                
                # Alternatif kamera ara
                for i in range(3):  # 0, 1, 2 indekslerini dene
                    if i != self.camera_index:
                        temp_cap = cv2.VideoCapture(i)
                        if temp_cap.isOpened():
                            self.camera_index = i
                            logging.info(f"Alternatif kamera bulundu: {i}")
                            temp_cap.release()
                            return
                        temp_cap.release()
                
                logging.error("Hiçbir kamera bulunamadı!")
            else:
                temp_cap.release()
                logging.info(f"Kamera {self.camera_index} kullanılabilir.")
        except Exception as e:
            logging.error(f"Kamera doğrulama hatası: {str(e)}")
    
    def start(self):
        """Kamerayı başlatır ve kare yakalama thread'ini başlatır."""
        with self.frame_lock:
            if self.is_running:
                logging.warning("Kamera zaten çalışıyor.")
                return False
            
            try:
                # Önceki kamera nesnesi varsa temizle
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                
                # Yeni kamera nesnesi oluştur
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    logging.error(f"Kamera {self.camera_index} açılamadı.")
                    return False
                
                # Kamera ayarlarını yap
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
                
                # İlk kareyi oku
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("İlk kare okunamadı.")
                    self.cap.release()
                    return False
                
                self.frame = frame
                self.last_frame_time = time.time()
                self.reconnect_attempts = 0
                
                # Thread'i başlat
                self.is_running = True
                self.thread = threading.Thread(target=self._capture_loop)
                self.thread.daemon = True
                self.thread.start()
                
                # Kamera durumu kontrolü zamanlayıcısını başlat
                self._start_status_timer()
                
                logging.info(f"Kamera başlatıldı: {self.camera_index}")
                return True
                
            except Exception as e:
                logging.error(f"Kamera başlatılırken hata oluştu: {str(e)}")
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                return False
    
    def stop(self):
        """Kamerayı ve kare yakalama thread'ini durdurur."""
        with self.frame_lock:
            if not self.is_running:
                logging.warning("Kamera zaten durmuş durumda.")
                return
            
            self.is_running = False
            
            # Durum zamanlayıcısını durdur
            if self.status_timer:
                self.status_timer.cancel()
                self.status_timer = None
            
            # Thread'i durdur
            if self.thread:
                try:
                    self.thread.join(timeout=1.0)
                except Exception as e:
                    logging.warning(f"Thread durdurulurken hata: {str(e)}")
                self.thread = None
            
            # Kamera nesnesini temizle
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception as e:
                    logging.warning(f"Kamera kaynağı serbest bırakılırken hata: {str(e)}")
                self.cap = None
            
            logging.info("Kamera durduruldu.")
    
    def get_frame(self):
        """En son yakalanan kareyi döndürür ve 640x640 boyutuna ayarlar."""
        with self.frame_lock:
            if self.frame is None:
                # Görüntü yoksa boş siyah ekran
                black_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
                
                # Kamera bağlantı durumunu göster
                font = cv2.FONT_HERSHEY_SIMPLEX
                if not self.is_running:
                    cv2.putText(black_frame, "Kamera Kapalı", (50, FRAME_HEIGHT//2), 
                            font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(black_frame, "Kamera Bağlanıyor...", (50, FRAME_HEIGHT//2), 
                            font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                
                return black_frame
            
            # Son kareyi al ve 640x640 boyutuna yeniden boyutlandır
            frame_copy = self.frame.copy()
            return cv2.resize(frame_copy, (FRAME_WIDTH, FRAME_HEIGHT))
    
    def capture_screenshot(self):
        """Anlık ekran görüntüsü alır ve doğru boyuta ayarlar."""
        frame = self.get_frame()  # Bu metot zaten 640x640 boyutunda döndürür
        
        # Ekran görüntüsüne zaman damgası ekle
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
        }
        
        if self.is_running and self.cap and self.cap.isOpened():
            status["connection"] = "connected"
        elif self.is_running:
            status["connection"] = "connecting"
        else:
            status["connection"] = "disconnected"
        
        # Son alınan karenin zamanını kontrol et
        if self.is_running and time.time() - self.last_frame_time > 3:
            status["connection"] = "stalled"
        
        return status
    
    def get_available_cameras(self):
        """Kullanılabilir kameraları tarar ve listeler."""
        available_cameras = []
        
        # İlk 5 kamera indeksini dene (0-4)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Kamera adını al (desteklenen platformlarda)
                camera_name = f"Kamera {i}"
                try:
                    # Windows'ta kamera adını almaya çalış
                    name = cap.getBackendName()
                    if name and name != "":
                        camera_name = f"{name} (Kamera {i})"
                except:
                    pass
                
                # Çözünürlük bilgisini al
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                available_cameras.append({
                    "index": i,
                    "name": camera_name,
                    "resolution": f"{width}x{height}"
                })
                
                cap.release()
        
        return available_cameras
    
    def change_camera(self, camera_index):
        """Kamera kaynağını değiştirir."""
        if self.camera_index == camera_index:
            return True
            
        # Mevcut kamerayı durdur
        was_running = self.is_running
        if was_running:
            self.stop()
            
        # Kamera indeksini güncelle
        self.camera_index = camera_index
        
        # Yeni kamerayı başlat (eğer daha önce çalışıyorduysa)
        if was_running:
            return self.start()
        return True
    
    def _start_status_timer(self):
        """Kamera durumunu düzenli olarak kontrol eden zamanlayıcı."""
        if self.status_timer:
            self.status_timer.cancel()
            
        def check_status():
            status = self.get_camera_status()
            
            # Kamera takılı kalmış durumdaysa yeniden başlatmayı dene
            if status["connection"] == "stalled" and self.is_running:
                logging.warning("Kamera yanıt vermiyor. Yeniden başlatılıyor...")
                self.reconnect()
                
            # Zamanlayıcıyı her 5 saniyede bir tekrarla
            if self.is_running:
                self.status_timer = threading.Timer(5.0, check_status)
                self.status_timer.daemon = True
                self.status_timer.start()
        
        # İlk kontrolü başlat
        self.status_timer = threading.Timer(5.0, check_status)
        self.status_timer.daemon = True
        self.status_timer.start()
    
    def reconnect(self):
        """Kamera bağlantısını yeniden kurar."""
        with self.frame_lock:
            self.reconnect_attempts += 1
            
            if self.reconnect_attempts > self.max_reconnect_attempts:
                logging.error(f"Maksimum yeniden bağlanma denemesi aşıldı ({self.max_reconnect_attempts}). Kamera kapatılıyor.")
                self.stop()
                return False
            
            logging.info(f"Kamera bağlantısı yeniden kuruluyor (Deneme {self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            
            # Mevcut kamera nesnesini temizle
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except:
                    pass
            
            # Yeni kamera nesnesi oluştur
            try:
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    logging.error(f"Kamera {self.camera_index} açılamadı.")
                    time.sleep(self.reconnect_delay)
                    return False
                
                # Kamera ayarlarını yap
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
                
                # İlk kareyi oku
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("İlk kare okunamadı.")
                    self.cap.release()
                    time.sleep(self.reconnect_delay)
                    return False
                
                self.frame = frame
                self.last_frame_time = time.time()
                
                logging.info("Kamera bağlantısı başarıyla yeniden kuruldu.")
                return True
                
            except Exception as e:
                logging.error(f"Kamera yeniden bağlanırken hata: {str(e)}")
                time.sleep(self.reconnect_delay)
                return False
    
    def _capture_loop(self):
        """Sürekli olarak kamera karelerini yakalayan thread fonksiyonu."""
        frame_count = 0
        fps_start_time = time.time()
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    time.sleep(0.5)
                    continue
                
                # Kareyi oku
                start_time = time.time()
                ret, frame = self.cap.read()
                
                if not ret:
                    logging.warning("Kare okunamadı, yeniden deneniyor...")
                    with self.frame_lock:
                        # Tam olarak siyah bir görüntü gelirse kamera yanıt vermiyor olabilir
                        if self.frame is not None and np.mean(self.frame) < 1.0:
                            logging.warning("Kamera yanıt vermiyor olabilir.")
                    
                    # Kısa bir bekleme
                    time.sleep(0.1)
                    continue
                
                # Başarılı kare okuma, frame ve zaman bilgisini güncelle
                with self.frame_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                
                # FPS hesaplama
                frame_count += 1
                elapsed_time = time.time() - fps_start_time
                
                # Her 1 saniyede FPS'i güncelle
                if elapsed_time >= 1.0:
                    self.fps = frame_count / elapsed_time
                    frame_count = 0
                    fps_start_time = time.time()
                
                # Kare işleme süresini kaydet
                frame_time = time.time() - start_time
                self.frame_times.append(frame_time)
                
                # Son n kareyi tut
                if len(self.frame_times) > self.max_frame_times:
                    self.frame_times.pop(0)
                
                # Hedef FPS'e göre uyku süresi ayarla
                target_delay = 1.0 / FRAME_RATE
                sleep_time = max(0, target_delay - frame_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Kare yakalama sırasında hata: {str(e)}")
                time.sleep(0.1)
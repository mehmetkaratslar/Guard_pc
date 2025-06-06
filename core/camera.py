# =======================================================================================
# 📄 Dosya Adı: camera.py (KAMERA BAŞLATMA SORUNU ÇÖZÜMÜ)
# 📁 Konum: guard_pc_app/core/camera.py
# 📌 Açıklama:
# Kamera başlatma sorunlarını çözen güncellenmiş versiyon
# =======================================================================================

import cv2
import numpy as np
import threading
import logging
import time
import platform
from collections import deque
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class Camera:
    """Geliştirilmiş kamera sınıfı - başlatma sorunları çözüldü."""
    
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
        
        # Frame yönetimi
        self.frame = None
        self.frame_lock = threading.RLock()
        self.last_frame_time = 0
        
        # Bağlantı yönetimi
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.connection_stable = False
        
        # Backend listesi - platform bazlı
        self.backend_fallbacks = self._get_platform_backends()
        
        # Kamera validation
        self.camera_validated = False
        
        logging.info(f"Kamera {camera_index} nesnesi oluşturuldu")
    
    def _get_platform_backends(self):
        """Platform için en uygun backend sıralaması."""
        if platform.system() == "Windows":
            return [
                cv2.CAP_DSHOW,      # DirectShow - Windows için en iyi
                cv2.CAP_MSMF,       # Media Foundation
                cv2.CAP_ANY         # Fallback
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
        
        logging.info(f"Kamera {self.camera_index} doğrulanıyor...")
        
        # Önce belirtilen backend'i dene
        if self.original_backend != cv2.CAP_ANY:
            if self._test_camera_with_backend(self.original_backend):
                self.backend = self.original_backend
                self.camera_validated = True
                logging.info(f"Kamera {self.camera_index}: {self._backend_name(self.original_backend)} backend başarılı")
                return True
        
        # Fallback backend'leri dene
        for backend in self.backend_fallbacks:
            if self._test_camera_with_backend(backend):
                self.backend = backend
                self.camera_validated = True
                logging.info(f"Kamera {self.camera_index}: {self._backend_name(backend)} backend başarılı")
                return True
        
        logging.error(f"Kamera {self.camera_index}: Hiçbir backend ile çalışmıyor!")
        return False
    
    def _test_camera_with_backend(self, backend):
        """Belirli bir backend ile kamerayı test eder."""
        test_cap = None
        try:
            # Kamera bağlantısını test et
            test_cap = cv2.VideoCapture(self.camera_index, backend)
            
            if not test_cap.isOpened():
                return False
            
            # Buffer size ayarla
            test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Temel parametreleri ayarla
            test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            test_cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Frame okumayı test et
            ret, frame = test_cap.read()
            
            if ret and frame is not None and frame.size > 0:
                logging.debug(f"Kamera {self.camera_index} test başarılı: {frame.shape}")
                return True
            else:
                logging.debug(f"Kamera {self.camera_index} frame okunamadı")
                return False
                
        except Exception as e:
            logging.debug(f"Kamera {self.camera_index} test hatası: {e}")
            return False
        finally:
            if test_cap:
                try:
                    test_cap.release()
                except:
                    pass
    
    def start(self):
        """Kamerayı başlatır."""
        if self.is_running:
            logging.warning(f"Kamera {self.camera_index} zaten çalışıyor")
            return True
        
        # Önce kamerayı doğrula
        if not self._validate_camera_with_fallback():
            logging.error(f"Kamera {self.camera_index} doğrulanamadı")
            return False
        
        try:
            # Kamerayı aç
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if not self.cap.isOpened():
                logging.error(f"Kamera {self.camera_index} açılamadı")
                return False
            
            # Kamera parametrelerini ayarla
            self._setup_camera_parameters()
            
            # İlk frame'i test et
            if not self._test_initial_frame():
                logging.error(f"Kamera {self.camera_index} ilk frame testi başarısız")
                self._cleanup()
                return False
            
            # Capture thread'ini başlat
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
            self.connection_stable = True
            logging.info(f"Kamera {self.camera_index} başarıyla başlatıldı ({self._backend_name(self.backend)})")
            return True
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} başlatma hatası: {e}")
            self._cleanup()
            return False
    
    def _setup_camera_parameters(self):
        """Kamera parametrelerini optimize eder."""
        try:
            # Temel parametreler
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Platform spesifik optimizasyonlar
            if platform.system() == "Windows":
                # Windows için ek ayarlar
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            
            logging.debug(f"Kamera {self.camera_index} parametreleri ayarlandı")
            
        except Exception as e:
            logging.warning(f"Kamera {self.camera_index} parametre ayarlama hatası: {e}")
    
    def _test_initial_frame(self):
        """İlk frame'i test eder."""
        try:
            for attempt in range(5):
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    with self.frame_lock:
                        self.frame = frame
                        self.last_frame_time = time.time()
                    logging.debug(f"Kamera {self.camera_index} ilk frame başarılı: {frame.shape}")
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} ilk frame test hatası: {e}")
            return False
    
    def _capture_loop(self):
        """Frame yakalama döngüsü."""
        consecutive_failures = 0
        max_failures = 10
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    logging.warning(f"Kamera {self.camera_index} bağlantısı koptu, yeniden bağlanılıyor...")
                    if not self._reconnect():
                        break
                    continue
                
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error(f"Kamera {self.camera_index}: Çok fazla hata, thread sonlandırılıyor")
                        break
                    time.sleep(0.1)
                    continue
                
                # Başarılı frame
                consecutive_failures = 0
                
                with self.frame_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                
                # FPS kontrolü
                time.sleep(1.0 / FRAME_RATE)
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} capture loop hatası: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
                time.sleep(0.5)
        
        self.is_running = False
        self.connection_stable = False
        logging.info(f"Kamera {self.camera_index} capture loop sonlandı")
    
    def _reconnect(self):
        """Kamera yeniden bağlantısı."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logging.error(f"Kamera {self.camera_index}: Maksimum yeniden bağlantı denemesi aşıldı")
            return False
        
        try:
            # Mevcut bağlantıyı kapat
            if self.cap:
                self.cap.release()
                self.cap = None
            
            time.sleep(1.0)  # Bekle
            
            # Yeniden bağlan
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            
            if self.cap.isOpened():
                self._setup_camera_parameters()
                if self._test_initial_frame():
                    self.reconnect_attempts = 0
                    self.connection_stable = True
                    logging.info(f"Kamera {self.camera_index} yeniden bağlandı")
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} yeniden bağlantı hatası: {e}")
            return False
    
    def stop(self):
        """Kamerayı durdurur."""
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        self._cleanup()
        logging.info(f"Kamera {self.camera_index} durduruldu")
    
    def _cleanup(self):
        """Kaynakları temizler."""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except:
            pass
        
        with self.frame_lock:
            self.frame = None
        
        self.connection_stable = False
    
    def get_frame(self):
        """Mevcut frame'i döndürür."""
        with self.frame_lock:
            if self.frame is not None:
                return self.frame.copy()
            else:
                # Placeholder frame oluştur
                return self._create_placeholder_frame()
    
    def _create_placeholder_frame(self):
        """Placeholder frame oluşturur."""
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
        
        # Metni ortala
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(message, font, font_scale, thickness)[0]
        text_x = (FRAME_WIDTH - text_size[0]) // 2
        text_y = (FRAME_HEIGHT + text_size[1]) // 2
        
        cv2.putText(frame, message, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
        
        return frame
    
    def _backend_name(self, backend):
        """Backend adını döndürür."""
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


# Kamera keşif ve test fonksiyonları
def discover_and_test_cameras():
    """Sistem kameralarını keşfeder ve test eder."""
    available_cameras = []
    
    logging.info("Kameralar taranıyor ve test ediliyor...")
    
    # Windows için optimize edilmiş tarama
    if platform.system() == "Windows":
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
    else:
        backends = [cv2.CAP_ANY]
    
    for index in range(5):  # 0-4 arası test et
        for backend in backends:
            try:
                logging.info(f"Kamera {index} test ediliyor ({Camera(0, backend)._backend_name(backend)})...")
                
                test_camera = Camera(index, backend)
                
                if test_camera._validate_camera_with_fallback():
                    # Gerçek başlatma testi
                    if test_camera.start():
                        # Kısa süre çalıştır
                        time.sleep(2)
                        frame = test_camera.get_frame()
                        test_camera.stop()
                        
                        if frame is not None and frame.size > 0:
                            camera_info = {
                                "index": index,
                                "backend": backend,
                                "backend_name": test_camera._backend_name(backend),
                                "name": f"Kamera {index}",
                                "status": "working",
                                "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
                            }
                            
                            available_cameras.append(camera_info)
                            logging.info(f"✅ Kamera {index} çalışıyor: {camera_info['backend_name']}")
                            break  # Bu indeks için başka backend deneme
                    else:
                        logging.warning(f"⚠️ Kamera {index} başlatılamadı: {test_camera._backend_name(backend)}")
                else:
                    logging.warning(f"⚠️ Kamera {index} doğrulanamadı: {test_camera._backend_name(backend)}")
                    
            except Exception as e:
                logging.debug(f"Kamera {index} test hatası ({backend}): {e}")
    
    logging.info(f"Toplam {len(available_cameras)} çalışan kamera bulundu")
    return available_cameras


def test_camera_quick(camera_index=0):
    """Hızlı kamera testi."""
    print(f"Kamera {camera_index} hızlı test başlatılıyor...")
    
    camera = Camera(camera_index)
    
    print("1. Kamera doğrulanıyor...")
    if not camera._validate_camera_with_fallback():
        print(f"❌ Kamera {camera_index} doğrulanamadı!")
        return False
    
    print("2. Kamera başlatılıyor...")
    if not camera.start():
        print(f"❌ Kamera {camera_index} başlatılamadı!")
        return False
    
    print("3. Frame test ediliyor...")
    for i in range(10):
        frame = camera.get_frame()
        if frame is not None and frame.size > 0:
            print(f"✅ Frame {i+1}: {frame.shape}")
        else:
            print(f"❌ Frame {i+1}: Boş")
        time.sleep(0.5)
    
    print("4. Kamera durduruluyor...")
    camera.stop()
    
    print(f"✅ Kamera {camera_index} test tamamlandı!")
    return True


if __name__ == "__main__":
    # Test ve demo
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔍 Kamera keşif ve test başlatılıyor...")
    cameras = discover_and_test_cameras()
    
    if cameras:
        print(f"\n✅ {len(cameras)} çalışan kamera bulundu:")
        for cam in cameras:
            print(f"  📹 {cam['name']} - {cam['resolution']} ({cam['backend_name']})")
        
        # İlk kamerayı detaylı test et
        if cameras:
            print(f"\n🧪 İlk kamera detaylı test ediliyor...")
            test_camera_quick(cameras[0]['index'])
    else:
        print("❌ Hiç çalışan kamera bulunamadı!")
        print("\nSorun giderme önerileri:")
        print("1. Kamera fiziksel olarak bağlı mı?")
        print("2. Başka bir uygulama kamerayı kullanıyor mu?")
        print("3. Kamera sürücüleri güncel mi?")
        print("4. Antivirus/güvenlik yazılımı kamerayı engelliyor mu?")
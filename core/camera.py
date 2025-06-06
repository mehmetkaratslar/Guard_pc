# =======================================================================================
# 📄 Dosya Adı: camera.py (ULTRA OPTIMIZED VERSION V2)
# 📁 Konum: guard_pc_app/core/camera.py
# 📌 Açıklama:
# Ultra optimize edilmiş kamera yönetimi - yüksek performans, düşük latency
# Gelişmiş backend fallback, robust hata yönetimi, memory optimization
# =======================================================================================

import cv2
import numpy as np
import threading
import logging
import time
import platform
from collections import deque
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT, FRAME_RATE

class UltraOptimizedCamera:
    """Ultra optimize edilmiş kamera sınıfı - yüksek performans ve düşük latency."""
    
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
        
        # Frame yönetimi - optimize edilmiş
        self.frame = None
        self.frame_buffer = deque(maxlen=2)  # Çift buffer
        self.frame_lock = threading.RLock()  # Re-entrant lock
        self.last_frame_time = 0
        
        # Bağlantı yönetimi
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 0.5  # Daha hızlı reconnect
        self.connection_stable = False
        
        # Performans metrikleri
        self.fps = 0
        self.avg_frame_time = 0
        self.frame_count = 0
        self.fps_calculation_start = time.time()
        self.performance_stats = {
            'frames_processed': 0,
            'frames_dropped': 0,
            'avg_processing_time': 0,
            'connection_uptime': 0
        }
        
        # Backend yönetimi - optimize edilmiş
        self.backend_fallbacks = self._get_optimized_backends()
        self.current_backend_index = 0
        self.last_successful_backend = None
        
        # Thread yönetimi
        self.should_stop = threading.Event()
        self.frame_ready = threading.Event()
        
        # Kamera ayarları cache
        self.camera_properties = {}
        
        # İlk doğrulama
        self._initialize_camera_system()
    
    def _get_optimized_backends(self):
        """Platform için optimize edilmiş backend sıralaması."""
        if platform.system() == "Windows":
            return [
                cv2.CAP_DSHOW,      # En hızlı ve kararlı
                cv2.CAP_ANY,        # Fallback
                cv2.CAP_MSMF        # Son seçenek
            ]
        elif platform.system() == "Linux":
            return [
                cv2.CAP_V4L2,       # Linux için optimal
                cv2.CAP_ANY,
                cv2.CAP_GSTREAMER
            ]
        elif platform.system() == "Darwin":  # macOS
            return [
                cv2.CAP_AVFOUNDATION,
                cv2.CAP_ANY
            ]
        else:
            return [cv2.CAP_ANY]
    
    def _initialize_camera_system(self):
        """Kamera sistemini başlatır."""
        success = False
        
        # Belirtilen backend'i önce dene
        if self.original_backend != cv2.CAP_ANY:
            if self._test_backend_fast(self.original_backend):
                self.backend = self.original_backend
                self.last_successful_backend = self.original_backend
                success = True
                logging.info(f"Kamera {self.camera_index}: Belirtilen backend başarılı ({self._backend_name(self.original_backend)})")
        
        # Fallback listesini dene
        if not success:
            for i, backend in enumerate(self.backend_fallbacks):
                if self._test_backend_fast(backend):
                    self.backend = backend
                    self.current_backend_index = i
                    self.last_successful_backend = backend
                    success = True
                    logging.info(f"Kamera {self.camera_index}: {self._backend_name(backend)} backend ile başarılı")
                    break
        
        if not success:
            logging.error(f"Kamera {self.camera_index}: Hiçbir backend ile başlatılamadı!")
            return False
        
        return True
    
    def _test_backend_fast(self, backend):
        """Hızlı backend testi."""
        try:
            test_cap = cv2.VideoCapture(self.camera_index, backend)
            if not test_cap.isOpened():
                test_cap.release()
                return False
            
            # Hızlı frame testi
            test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ret, frame = test_cap.read()
            test_cap.release()
            
            return ret and frame is not None and frame.size > 0
            
        except Exception:
            return False
    
    def start(self):
        """Ultra hızlı kamera başlatma."""
        with self.frame_lock:
            if self.is_running:
                logging.warning(f"Kamera {self.camera_index} zaten çalışıyor")
                return True
            
            # Mevcut kaynakları temizle
            self._cleanup_resources()
            
            # Kamerayı başlat
            if not self._start_optimized_capture():
                logging.error(f"Kamera {self.camera_index} başlatılamadı")
                return False
            
            # Thread başlat
            self.should_stop.clear()
            self.is_running = True
            self.thread = threading.Thread(target=self._ultra_fast_capture_loop, daemon=True)
            self.thread.start()
            
            # İstatistikleri sıfırla
            self._reset_performance_stats()
            
            logging.info(f"Kamera {self.camera_index} ultra optimize modda başlatıldı ({self._backend_name(self.backend)})")
            return True
    
    def _start_optimized_capture(self):
        """Optimize edilmiş kamera başlatma."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
            if not self.cap.isOpened():
                return False
            
            # Ultra optimize edilmiş ayarlar
            optimization_settings = [
                (cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH),
                (cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT),
                (cv2.CAP_PROP_FPS, FRAME_RATE),
                (cv2.CAP_PROP_BUFFERSIZE, 1),  # Minimum latency
                (cv2.CAP_PROP_AUTOFOCUS, 0),   # Autofocus kapalı (daha hızlı)
                (cv2.CAP_PROP_AUTO_EXPOSURE, 0.25),  # Manuel exposure
            ]
            
            for prop, value in optimization_settings:
                try:
                    self.cap.set(prop, value)
                    self.camera_properties[prop] = value
                except:
                    pass
            
            # Codec optimize edildi
            try:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            except:
                pass
            
            # İlk frame testi
            for _ in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.frame_lock:
                        self.frame = frame
                        self.last_frame_time = time.time()
                    self.connection_stable = True
                    return True
                time.sleep(0.02)
            
            return False
            
        except Exception as e:
            logging.error(f"Kamera {self.camera_index} optimize edilmiş başlatma hatası: {e}")
            return False
    
    def stop(self):
        """Ultra hızlı kamera durdurma."""
        if not self.is_running:
            return
        
        # Stop signal gönder
        self.should_stop.set()
        self.is_running = False
        
        # Thread'i bekle (kısa timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Kaynakları temizle
        self._cleanup_resources()
        
        logging.info(f"Kamera {self.camera_index} durduruldu")
    
    def _cleanup_resources(self):
        """Kaynakları temizle."""
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        with self.frame_lock:
            self.frame = None
            self.frame_buffer.clear()
        
        self.connection_stable = False
    
    def get_frame(self):
        """Ultra hızlı frame alma."""
        with self.frame_lock:
            if not self.is_running or self.frame is None:
                return self._create_status_frame()
            
            try:
                # En son frame'i kopyala
                frame_copy = self.frame.copy()
                
                # Resize (gerekirse)
                if frame_copy.shape[:2] != (FRAME_HEIGHT, FRAME_WIDTH):
                    frame_copy = cv2.resize(frame_copy, (FRAME_WIDTH, FRAME_HEIGHT), 
                                          interpolation=cv2.INTER_LINEAR)
                
                return frame_copy
                
            except Exception as e:
                logging.error(f"Frame alma hatası: {e}")
                return self._create_status_frame()
    
    def _create_status_frame(self):
        """Durum frame'i oluştur."""
        status_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        
        # Arka plan gradient
        for i in range(FRAME_HEIGHT):
            intensity = int(20 + (i / FRAME_HEIGHT) * 40)
            status_frame[i, :] = [intensity, intensity, intensity]
        
        # Durum mesajı
        if not self.is_running:
            message = f"Kamera {self.camera_index} - KAPALI"
            color = (100, 100, 100)
        elif not self.connection_stable:
            message = f"Kamera {self.camera_index} - BAGLANILIYOR..."
            color = (0, 255, 255)  # Sarı
        else:
            message = f"Kamera {self.camera_index} - HAZIR"
            color = (0, 255, 0)  # Yeşil
        
        # Metni ortala
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(message, font, font_scale, thickness)[0]
        text_x = (FRAME_WIDTH - text_size[0]) // 2
        text_y = (FRAME_HEIGHT + text_size[1]) // 2
        
        cv2.putText(status_frame, message, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
        
        # Performans bilgisi
        if self.is_running:
            fps_text = f"FPS: {self.fps:.1f}"
            cv2.putText(status_frame, fps_text, (20, 40), font, 0.7, (0, 255, 136), 2, cv2.LINE_AA)
            
            backend_text = f"Backend: {self._backend_name(self.backend)}"
            cv2.putText(status_frame, backend_text, (20, FRAME_HEIGHT - 20), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        return status_frame
    
    def _ultra_fast_capture_loop(self):
        """Ultra hızlı frame yakalama döngüsü."""
        consecutive_failures = 0
        max_failures = 5
        target_frame_time = 1.0 / FRAME_RATE
        
        while not self.should_stop.is_set():
            loop_start = time.time()
            
            try:
                if not self.cap or not self.cap.isOpened():
                    if not self._quick_reconnect():
                        time.sleep(0.1)
                        continue
                
                # Frame yakala
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.warning(f"Kamera {self.camera_index}: Çok fazla hata, yeniden bağlanılıyor...")
                        self._quick_reconnect()
                        consecutive_failures = 0
                    continue
                
                # Başarılı frame
                consecutive_failures = 0
                self.connection_stable = True
                
                # Frame'i güncelle
                with self.frame_lock:
                    self.frame = frame
                    self.last_frame_time = time.time()
                    
                    # Buffer'a ekle
                    self.frame_buffer.append(frame.copy())
                
                # Performans hesaplama
                self._update_performance_stats(loop_start)
                
                # FPS kontrolü
                elapsed = time.time() - loop_start
                sleep_time = max(0, target_frame_time - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"Kamera {self.camera_index} capture loop hatası: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    self._quick_reconnect()
                    consecutive_failures = 0
                time.sleep(0.05)
    
    def _quick_reconnect(self):
        """Hızlı yeniden bağlanma."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            # Farklı backend dene
            self._try_next_backend()
            if self.reconnect_attempts > self.max_reconnect_attempts * len(self.backend_fallbacks):
                logging.error(f"Kamera {self.camera_index}: Tüm backend'ler denendi, başarısız")
                return False
        
        logging.debug(f"Kamera {self.camera_index}: Hızlı yeniden bağlanma (#{self.reconnect_attempts})")
        
        # Mevcut bağlantıyı temizle
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        # Kısa bekleme
        time.sleep(self.reconnect_delay)
        
        # Yeniden başlat
        if self._start_optimized_capture():
            self.reconnect_attempts = 0
            self.connection_stable = True
            return True
        
        return False
    
    def _try_next_backend(self):
        """Sonraki backend'e geç."""
        self.current_backend_index = (self.current_backend_index + 1) % len(self.backend_fallbacks)
        self.backend = self.backend_fallbacks[self.current_backend_index]
        self.reconnect_attempts = 0
        
        logging.info(f"Kamera {self.camera_index}: {self._backend_name(self.backend)} backend'e geçiliyor")
    
    def _update_performance_stats(self, start_time):
        """Performans istatistiklerini güncelle."""
        frame_time = time.time() - start_time
        self.frame_count += 1
        
        # FPS hesaplama
        elapsed = time.time() - self.fps_calculation_start
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_calculation_start = time.time()
        
        # Ortalama frame süresi
        if hasattr(self, '_frame_times'):
            self._frame_times.append(frame_time)
            if len(self._frame_times) > 30:
                self._frame_times.pop(0)
        else:
            self._frame_times = [frame_time]
        
        self.avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        
        # İstatistikleri güncelle
        self.performance_stats['frames_processed'] += 1
        self.performance_stats['avg_processing_time'] = self.avg_frame_time
    
    def _reset_performance_stats(self):
        """Performans istatistiklerini sıfırla."""
        self.performance_stats = {
            'frames_processed': 0,
            'frames_dropped': 0,
            'avg_processing_time': 0,
            'connection_uptime': time.time()
        }
        self.frame_count = 0
        self.fps_calculation_start = time.time()
        self._frame_times = []
    
    def get_detailed_status(self):
        """Detaylı kamera durumu."""
        status = {
            "camera_index": self.camera_index,
            "is_running": self.is_running,
            "connection_stable": self.connection_stable,
            "backend": self._backend_name(self.backend),
            "fps": round(self.fps, 2),
            "avg_frame_time": round(self.avg_frame_time * 1000, 2),  # ms
            "reconnect_attempts": self.reconnect_attempts,
            "has_frame": self.frame is not None,
            "last_frame_age": time.time() - self.last_frame_time if self.last_frame_time > 0 else float('inf'),
            "performance": self.performance_stats.copy()
        }
        
        # Bağlantı durumu
        if self.is_running and self.connection_stable:
            if status["last_frame_age"] < 2:
                status["connection_status"] = "excellent"
            elif status["last_frame_age"] < 5:
                status["connection_status"] = "good"
            else:
                status["connection_status"] = "poor"
        elif self.is_running:
            status["connection_status"] = "connecting"
        else:
            status["connection_status"] = "disconnected"
        
        return status
    
    def capture_high_quality_screenshot(self):
        """Yüksek kaliteli screenshot."""
        frame = self.get_frame()
        if frame is None:
            return None
        
        # Timestamp ekle
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Arka plan kutusu
        text_size = cv2.getTextSize(timestamp, font, 0.8, 2)[0]
        cv2.rectangle(frame, (10, 10), (text_size[0] + 20, 50), (0, 0, 0), -1)
        cv2.putText(frame, timestamp, (15, 35), font, 0.8, (0, 255, 136), 2, cv2.LINE_AA)
        
        # Kamera bilgisi
        info_text = f"Camera {self.camera_index} | {self._backend_name(self.backend)} | {self.fps:.1f} FPS"
        info_size = cv2.getTextSize(info_text, font, 0.6, 1)[0]
        cv2.rectangle(frame, (10, frame.shape[0] - 30), (info_size[0] + 20, frame.shape[0] - 5), (0, 0, 0), -1)
        cv2.putText(frame, info_text, (15, frame.shape[0] - 15), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        
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


class CameraManager:
    """Ultra optimize edilmiş kamera yöneticisi."""
    
    def __init__(self):
        self.cameras = {}
        self.active_cameras = []
        self.manager_lock = threading.Lock()
        
    def add_camera(self, camera_index, backend=cv2.CAP_ANY):
        """Kamera ekle."""
        with self.manager_lock:
            if camera_index in self.cameras:
                logging.warning(f"Kamera {camera_index} zaten mevcut")
                return False
            
            camera = UltraOptimizedCamera(camera_index, backend)
            self.cameras[camera_index] = camera
            
            logging.info(f"Kamera {camera_index} yöneticiye eklendi")
            return True
    
    def start_camera(self, camera_index):
        """Belirli kamerayı başlat."""
        with self.manager_lock:
            if camera_index in self.cameras:
                success = self.cameras[camera_index].start()
                if success and camera_index not in self.active_cameras:
                    self.active_cameras.append(camera_index)
                return success
            return False
    
    def stop_camera(self, camera_index):
        """Belirli kamerayı durdur."""
        with self.manager_lock:
            if camera_index in self.cameras:
                self.cameras[camera_index].stop()
                if camera_index in self.active_cameras:
                    self.active_cameras.remove(camera_index)
                return True
            return False
    
    def start_all_cameras(self):
        """Tüm kameraları başlat."""
        with self.manager_lock:
            success_count = 0
            for camera_index in self.cameras:
                if self.start_camera(camera_index):
                    success_count += 1
            
            logging.info(f"{success_count}/{len(self.cameras)} kamera başlatıldı")
            return success_count
    
    def stop_all_cameras(self):
        """Tüm kameraları durdur."""
        with self.manager_lock:
            for camera_index in list(self.active_cameras):
                self.stop_camera(camera_index)
            
            logging.info("Tüm kameralar durduruldu")
    
    def get_frame(self, camera_index):
        """Belirli kameradan frame al."""
        if camera_index in self.cameras:
            return self.cameras[camera_index].get_frame()
        return None
    
    def get_all_frames(self):
        """Tüm aktif kameralardan frame al."""
        frames = {}
        for camera_index in self.active_cameras:
            frame = self.get_frame(camera_index)
            if frame is not None:
                frames[camera_index] = frame
        return frames
    
    def get_camera_status(self, camera_index):
        """Kamera durumu al."""
        if camera_index in self.cameras:
            return self.cameras[camera_index].get_detailed_status()
        return None
    
    def get_all_camera_status(self):
        """Tüm kamera durumları."""
        status = {}
        for camera_index in self.cameras:
            status[camera_index] = self.get_camera_status(camera_index)
        return status


def discover_cameras():
    """Sistem kameralarını keşfet."""
    available_cameras = []
    
    # Platform spesifik backend'ler
    if platform.system() == "Windows":
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    elif platform.system() == "Linux":
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
    elif platform.system() == "Darwin":
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_ANY]
    
    logging.info("Kameralar taranıyor...")
    
    for index in range(10):  # 0-9 arası test et
        for backend in backends:
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = int(cap.get(cv2.CAP_PROP_FPS))
                        
                        backend_name = UltraOptimizedCamera(0, backend)._backend_name(backend)
                        
                        camera_info = {
                            "index": index,
                            "backend": backend,
                            "backend_name": backend_name,
                            "name": f"Kamera {index}",
                            "resolution": f"{width}x{height}",
                            "fps": fps,
                            "status": "available"
                        }
                        
                        # Duplicate kontrolü
                        if not any(cam["index"] == index for cam in available_cameras):
                            available_cameras.append(camera_info)
                            logging.info(f"Kamera bulundu: {camera_info['name']} ({backend_name})")
                
                cap.release()
                
            except Exception as e:
                logging.debug(f"Kamera {index} test hatası: {e}")
    
    logging.info(f"Toplam {len(available_cameras)} kamera bulundu")
    return available_cameras


def benchmark_camera(camera_index=0, duration=10):
    """Kamera performans testi."""
    logging.info(f"Kamera {camera_index} performans testi başlatılıyor ({duration}s)...")
    
    camera = UltraOptimizedCamera(camera_index)
    if not camera.start():
        logging.error("Kamera başlatılamadı!")
        return None
    
    try:
        start_time = time.time()
        frame_count = 0
        total_processing_time = 0
        
        while time.time() - start_time < duration:
            process_start = time.time()
            frame = camera.get_frame()
            process_time = time.time() - process_start
            
            if frame is not None:
                frame_count += 1
                total_processing_time += process_time
            
            time.sleep(0.01)  # 100 FPS test
        
        # Sonuçlar
        test_duration = time.time() - start_time
        status = camera.get_detailed_status()
        
        results = {
            "camera_index": camera_index,
            "test_duration": test_duration,
            "frames_captured": frame_count,
            "average_fps": frame_count / test_duration,
            "camera_reported_fps": status["fps"],
            "average_processing_time": (total_processing_time / frame_count * 1000) if frame_count > 0 else 0,
            "backend": status["backend"],
            "connection_status": status["connection_status"],
            "performance_grade": "A" if status["fps"] > 25 else "B" if status["fps"] > 15 else "C"
        }
        
        logging.info(f"Test tamamlandı:")
        logging.info(f"  📸 Frame sayısı: {frame_count}")
        logging.info(f"  ⚡ Ortalama FPS: {results['average_fps']:.1f}")
        logging.info(f"  🔧 Backend: {results['backend']}")
        logging.info(f"  📊 Performans: {results['performance_grade']}")
        
        return results
        
    finally:
        camera.stop()


# Alias for backward compatibility
Camera = UltraOptimizedCamera

if __name__ == "__main__":
    # Test ve demo
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔍 Kamera keşif başlatılıyor...")
    cameras = discover_cameras()
    
    if cameras:
        print(f"\n✅ {len(cameras)} kamera bulundu:")
        for cam in cameras:
            print(f"  📹 {cam['name']} - {cam['resolution']} @ {cam['fps']} FPS ({cam['backend_name']})")
        
        # İlk kamerayı test et
        print(f"\n🧪 İlk kamera test ediliyor...")
        benchmark_camera(cameras[0]['index'], 5)
    else:
        print("❌ Hiç kamera bulunamadı!")
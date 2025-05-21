# File: core/stream_server.py
# Açıklama: Düşme algılama sisteminden MJPEG video akışı sağlayan Flask sunucusu

import cv2
import threading
import time
import logging
import numpy as np
from flask import Flask, Response, jsonify
from flask_cors import CORS
import os

# Proje kök dizinine göre log dosyasının yolunu belirle
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Günlük ayarlarını yapılandır
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'stream_server.log'))
    ]
)
logger = logging.getLogger('stream_server')

app = Flask(__name__)
CORS(app)  # CORS desteği ekle (mobil uygulamadan erişim için)

# Sunucu yapılandırma ayarları
SERVER_HOST = '0.0.0.0'  # Tüm arayüzlerden erişime izin ver
SERVER_PORT = 5000
MJPEG_QUALITY = 80      # JPEG kalitesi (0-100)
MAX_FPS = 60           # Maksimum FPS (saniyedeki kare sayısı)
STREAM_WIDTH = 640      # Akış genişliği
STREAM_HEIGHT = 480     # Akış yüksekliği

class VideoCamera:
    """Kamera işlemleri ve düşme algılama işlemlerini yönetir."""
    
    def __init__(self, camera_id=0):
        """
        VideoCamera sınıfını başlatır.
        
        Args:
            camera_id (int): Kamera ID'si (varsayılan: 0, birincil kamera)
        """
        logger.info(f"Kamera {camera_id} başlatılıyor...")

        # OpenCV backend'ini DirectShow olarak ayarla (Windows için)
        self.video = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, STREAM_WIDTH)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, STREAM_HEIGHT)
        self.video.set(cv2.CAP_PROP_FPS, MAX_FPS)

        # Kamera kontrolü
        if not self.video.isOpened():
            logger.error(f"Kamera {camera_id} açılamadı!")
            raise ValueError(f"Kamera {camera_id} açılamadı!")

        # Düşme durumu ve güven değeri (Basitleştirilmiş, fall_detector olmadan)
        self.is_fall_detected = False
        self.fall_confidence = 0.0
        self.last_fall_time = 0
        self.fall_cooldown = 5  # Saniye cinsinden düşme bildirimi bekleme süresi
        
        # İşleme durumları
        self.enable_fall_detection = True
        
        # Thread güvenli erişim için kilit
        self.lock = threading.Lock()
        self.current_frame = None
        
        # Frame alma thread'i
        self.stop_thread = False
        self.frame_thread = threading.Thread(target=self._update_frames, args=())
        self.frame_thread.daemon = True
        self.frame_thread.start()
        
        # Düşme algılama thread'i
        self.detection_thread = threading.Thread(target=self._update_detection, args=())
        self.detection_thread.daemon = True
        self.detection_thread.start()
        
        # FPS hesaplama
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        
        logger.info("VideoCamera sınıfı başlatıldı")
    
    def _update_frames(self):
        """Arka plan thread'inde sürekli olarak kameradan kare alır."""
        try:
            while not self.stop_thread:
                start_time = time.time()
                success, frame = self.video.read()
                
                if not success:
                    logger.warning("Kare okunamadı, yeniden deneniyor...")
                    time.sleep(0.1)
                    continue
                
                # FPS hesapla
                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= 4.0:  # Her saniyede bir güncelle
                    self.fps = self.frame_count / elapsed_time
                    self.frame_count = 0
                    self.start_time = time.time()
                
                # Kareyi thread-safe şekilde güncelle
                with self.lock:
                    self.current_frame = frame.copy()
                
                # FPS kontrolü için uyku süresi
                target_delay = 1.0 / MAX_FPS
                elapsed_time = time.time() - start_time
                sleep_time = max(0, target_delay - elapsed_time)
                time.sleep(sleep_time)
        
        except Exception as e:
            logger.error(f"Kare güncelleme döngüsünde hata: {str(e)}", exc_info=True)
        finally:
            logger.info("Kare alma thread'i durduruldu.")
    
    def _update_detection(self):
        """Arka plan thread'inde düşme algılama işlemini yürütür."""
        try:
            while not self.stop_thread:
                if not self.enable_fall_detection:
                    time.sleep(0.1)
                    continue
                
                # Kareyi al
                with self.lock:
                    if self.current_frame is None:
                        time.sleep(0.1)
                        continue
                    frame = self.current_frame.copy()
                
                # Basit bir örnek: Karedeki parlaklık değişimini kontrol et
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)
                if brightness < 50:  # Örnek bir eşik değeri
                    current_time = time.time()
                    if current_time - self.last_fall_time > self.fall_cooldown:
                        self.is_fall_detected = True
                        self.fall_confidence = 0.9  # Örnek bir değer
                        self.last_fall_time = current_time
                        logger.warning(f"DÜŞME ALGILANDI! Güven: {self.fall_confidence:.4f}")
                
                # Düşme algılama görsel belirtileri ekle
                with self.lock:
                    if self.current_frame is not None and self.is_fall_detected:
                        cv2.rectangle(self.current_frame, (0, 0), (self.current_frame.shape[1], self.current_frame.shape[0]), (0, 0, 255), 10)
                        cv2.putText(
                            self.current_frame, 
                            f"DÜŞME ALGILANDI! ({self.fall_confidence:.2f})", 
                            (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            1, 
                            (0, 0, 255), 
                            2
                        )
                
                # FPS bilgisini ekle
                with self.lock:
                    if self.current_frame is not None:
                        cv2.putText(
                            self.current_frame, 
                            f"FPS: {self.fps:.1f}", 
                            (self.current_frame.shape[1] - 120, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.7, 
                            (0, 255, 0), 
                            2
                        )
                
                time.sleep(0.1)  # Düşme algılama için daha düşük bir sıklık yeterli
        
        except Exception as e:
            logger.error(f"Düşme algılama döngüsünde hata: {str(e)}", exc_info=True)
        finally:
            logger.info("Düşme algılama thread'i durduruldu.")
    
    def get_frame(self):
        """
        Mevcut kareyi JPEG formatında döndürür.
        
        Returns:
            bytes: JPEG formatında sıkıştırılmış kare verileri
        """
        with self.lock:
            if self.current_frame is None:
                # Eğer henüz kare alınmadıysa boş bir kare döndür
                empty_frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), dtype=np.uint8)
                ret, jpeg = cv2.imencode('.jpg', empty_frame)
                return jpeg.tobytes()
            
            # JPEG formatına dönüştürme ve kalite ayarı (düşük gecikme için)
            ret, jpeg = cv2.imencode(
                '.jpg', 
                self.current_frame, 
                [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY]
            )
            
            if not ret:
                logger.warning("Kare JPEG formatına dönüştürülemedi")
                return None
                
            return jpeg.tobytes()
    
    def reset_fall_detection(self):
        """Düşme algılama durumunu sıfırlar."""
        with self.lock:
            self.is_fall_detected = False
            self.fall_confidence = 0.0
            logger.info("Düşme algılama durumu sıfırlandı")
            return True
    
    def toggle_fall_detection(self):
        """Düşme algılama durumunu etkinleştirir/devre dışı bırakır."""
        with self.lock:
            self.enable_fall_detection = not self.enable_fall_detection
            logger.info(f"Düşme algılama: {self.enable_fall_detection}")
            return self.enable_fall_detection
    
    def __del__(self):
        """Nesne yok edilirken kaynakları temizler."""
        self.stop_thread = True
        if hasattr(self, 'frame_thread'):
            self.frame_thread.join(timeout=1.0)
        if hasattr(self, 'detection_thread'):
            self.detection_thread.join(timeout=1.0)
        if hasattr(self, 'video') and self.video.isOpened():
            self.video.release()
        logger.info("VideoCamera nesnesi temizlendi")

# Tek bir kamera nesnesi oluştur (tüm bağlantılar için paylaşılacak)
try:
    camera = VideoCamera()
    logger.info("Kamera başarıyla başlatıldı")
except Exception as e:
    logger.error(f"Kamera başlatılamadı: {str(e)}", exc_info=True)
    camera = None

# MJPEG akışı için jeneratör fonksiyonu
def gen_frames():
    """
    MJPEG akışı için kare jeneratörü.
    
    Yields:
        bytes: MJPEG formatında kare başlıkları ve JPEG verileri
    """
    try:
        frame_count = 0
        start_time = time.time()
        while camera is not None:
            frame = camera.get_frame()
            
            if frame is None:
                logger.warning("Boş kare alındı, 100ms bekleniyor")
                time.sleep(0.1)
                continue
                
            # MJPEG formatı için gerekli başlıklar ve sınırlayıcılar
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                  
            # FPS kontrolü için gecikme
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time > 1:  # Her saniye FPS logla
                fps = frame_count / elapsed_time
                logger.debug(f"Akış FPS: {fps:.2f}")
                frame_count = 0
                start_time = time.time()

            target_delay = 1.0 / MAX_FPS
            time.sleep(max(0, target_delay))
    
    except Exception as e:
        logger.error(f"Kare jeneratöründe hata: {str(e)}", exc_info=True)
    finally:
        logger.info("Kare jeneratörü sonlandı")

# Flask rotaları
@app.route('/video_feed')
def video_feed():
    """Video akışını sağlayan endpoint."""
    if camera is None:
        return "Kamera başlatılamadı", 503
        
    return Response(
        gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/fall_status')
def fall_status():
    """Düşme durumunu JSON formatında döndürür."""
    if camera is None:
        return jsonify({'error': 'Kamera başlatılamadı'}), 503
        
    return jsonify({
        'fall_detected': camera.is_fall_detected,
        'confidence': float(camera.fall_confidence),
        'detection_enabled': camera.enable_fall_detection,
        'last_fall_time': camera.last_fall_time
    })

@app.route('/reset_fall', methods=['POST'])
def reset_fall():
    """Düşme algılama durumunu sıfırlar."""
    if camera is None:
        return jsonify({'error': 'Kamera başlatılamadı'}), 503
        
    success = camera.reset_fall_detection()
    return jsonify({'success': success})

@app.route('/toggle_detection', methods=['POST'])
def toggle_detection():
    """Düşme algılama durumunu etkinleştirir/devre dışı bırakır."""
    if camera is None:
        return jsonify({'error': 'Kamera başlatılamadı'}), 503
        
    status = camera.toggle_fall_detection()
    return jsonify({'detection_enabled': status})

@app.route('/server_status')
def server_status():
    """Sunucu durumunu döndürür."""
    if camera is None:
        logger.error("Kamera başlatılamadı, server_status çağrıldı")
        return jsonify({'status': 'error', 'message': 'Kamera başlatılamadı'}), 503
        
    logger.info(f"Server status requested: FPS={camera.fps}, Fall Detection={camera.enable_fall_detection}")
    return jsonify({
        'status': 'ok',
        'fps': camera.fps,
        'fall_detection': camera.enable_fall_detection
    })

@app.route('/api/stream:5000/server_status')
def api_stream_server_status():
    """Geçici bir yönlendirme rotası."""
    logger.warning("Yanlış rota: /api/stream:5000/server_status çağrıldı, /server_status rotasına yönlendiriliyor")
    return server_status()  # /server_status rotasına yönlendir

if __name__ == '__main__':
    try:
        logger.info(f"Sunucu başlatılıyor {SERVER_HOST}:{SERVER_PORT}...")
        app.run(host=SERVER_HOST, port=SERVER_PORT, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Sunucu başlatılırken hata: {str(e)}", exc_info=True)
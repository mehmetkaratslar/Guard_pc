# =======================================================================================
# 📄 Dosya Adı   : stream_server.py
# 📁 Konum       : pc/core/stream_server.py
# 📌 Açıklama    : Düşme algılama sisteminde MJPEG video akışı sağlayan Flask sunucusudur.
#                 Kamera akışını 640x640 boyutunda işler, her 5 saniyede bir
#                 AI ile düşme tespiti yapar. Düşme tespit edilirse:
#                   - Ekranda uyarı gösterilir.
#                   - Olay Firestore'a kaydedilir.
#                   - Bildirim (e-posta, push, telegram) gönderilir.
#
# 🔗 Bağlantılı Dosyalar:
#   - utils/logger.py           : Loglama ayarları
#   - firebase/notification.py  : Bildirim gönderimi (e-posta, sms, telegram, push)
#   - firebase/recorder.py      : Olay kaydı (Firestore)
#   - ml/fall_detector.py       : Düşme algılama modeli
#   - config/settings.py        : Ayar ve sabitler
#
# 🗒️ Notlar:
#   - /video_feed      : Canlı MJPEG kamera akışı (mobil/web arayüzü izler)
#   - /fall_status     : Son düşme algılama durumu (JSON)
#   - /reset_fall      : Düşme durumunu sıfırlar (POST)
#   - /server_status   : Sunucu ve kamera durumunu döndürür (JSON)
# =======================================================================================


import cv2
import threading
import time
import logging
import numpy as np
from flask import Flask, Response, jsonify
from flask_cors import CORS
import os

# =============== Loglama Ayarları ===============
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'stream_server.log'))
    ]
)
logger = logging.getLogger('stream_server')

# =============== Flask Uygulaması ===============
app = Flask(__name__)
CORS(app)

# =============== Kamera ve Akış Ayarları ===============
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
MJPEG_QUALITY = 80
MAX_FPS = 60
STREAM_WIDTH = 640
STREAM_HEIGHT = 640   # ARTIK 640x640 KARE!

# =============== Model ve Bildirim Fonksiyonları (YER TUTUCU) ===============
# Gerçek model dosyanı burada yükleyebilirsin!
# from ml.fall_detector import FallDetector
# fall_detector = FallDetector('resources/models/fall_model.pt')

def notify_fall(frame, confidence):
    """
    Düşme olayı bildirimi gönderir (Kendi fonksiyonunu buraya entegre et).
    - frame: Kare görüntüsü (numpy array)
    - confidence: Olayın olasılığı
    """
    # Örn: firebase/notification.py fonksiyonu
    logger.info("[BILDIRIM] Düşme bildirimi gönderildi.")
    # send_notification_to_firebase(frame, confidence) # SENİN FONKSİYONUN

def save_fall_event(frame, confidence):
    """
    Düşme olayını olay geçmişine kaydeder.
    - frame: Kare görüntüsü
    - confidence: Olasılık
    """
    logger.info("[KAYIT] Düşme olayı geçmişe kaydedildi.")
    # save_event_to_firestore(frame, confidence) # SENİN FONKSİYONUN

# =============== VideoCamera Sınıfı ===============
class VideoCamera:
    """
    Kamera işlemleri ve düşme algılama işlemlerini yönetir.
    """

    def __init__(self, camera_id=0):
        logger.info(f"Kamera {camera_id} başlatılıyor...")
        # Kamera açılırken 640x640 olarak ayarla
        self.video = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, STREAM_WIDTH)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, STREAM_HEIGHT)
        self.video.set(cv2.CAP_PROP_FPS, MAX_FPS)

        if not self.video.isOpened():
            logger.error(f"Kamera {camera_id} açılamadı!")
            raise ValueError(f"Kamera {camera_id} açılamadı!")

        # Düşme durumu ve güven değeri
        self.is_fall_detected = False
        self.fall_confidence = 0.0
        self.last_fall_time = 0
        self.fall_cooldown = 5  # Saniye cinsinden minimum bildirim arası

        self.lock = threading.Lock()
        self.current_frame = None

        self.stop_thread = False
        self.frame_thread = threading.Thread(target=self._update_frames, args=())
        self.frame_thread.daemon = True
        self.frame_thread.start()

        # Sadece her 5 sn'de bir çalışacak şekilde timer ile detection
        self.detection_interval = 5.0  # SANİYEDE BİR TETİKLE!
        self.detection_thread = threading.Thread(target=self._run_detection_timer, args=())
        self.detection_thread.daemon = True
        self.detection_thread.start()

        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

        logger.info("VideoCamera sınıfı başlatıldı")

    def _update_frames(self):
        """
        Kameradan sürekli kare alır ve son kareyi günceller.
        """
        try:
            while not self.stop_thread:
                start_time = time.time()
                success, frame = self.video.read()
                if not success:
                    logger.warning("Kare okunamadı, yeniden deneniyor...")
                    time.sleep(0.1)
                    continue
                # Kareyi 640x640 crop veya resize et (garanti)
                frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT))

                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= 2.0:
                    self.fps = self.frame_count / elapsed_time
                    self.frame_count = 0
                    self.start_time = time.time()

                with self.lock:
                    self.current_frame = frame.copy()

                # FPS kontrolü
                target_delay = 1.0 / MAX_FPS
                elapsed = time.time() - start_time
                time.sleep(max(0, target_delay - elapsed))
        except Exception as e:
            logger.error(f"Kare güncelleme döngüsünde hata: {str(e)}", exc_info=True)
        finally:
            logger.info("Kare alma thread'i durduruldu.")

    def _run_detection_timer(self):
        """
        Her 5 saniyede bir düşme algılama fonksiyonunu çağırır.
        """
        try:
            while not self.stop_thread:
                time.sleep(self.detection_interval)  # 5 sn bekle
                with self.lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        continue

                # ==== MODEL ENTEGRASYONU (KENDİ MODELİNİ BURADA ÇAĞIR) ====
                # (Örnek kod - yerini kendi modeline göre değiştir!)
                # fall_detected, confidence = fall_detector.predict(frame)
                # ---- SADE TEST ----
                fall_detected = np.random.rand() < 0.05  # 5% olasılık simülasyonu (örnek)
                confidence = np.random.uniform(0.75, 1.0) if fall_detected else 0.0

                if fall_detected:
                    now = time.time()
                    if now - self.last_fall_time > self.fall_cooldown:
                        self.is_fall_detected = True
                        self.fall_confidence = confidence
                        self.last_fall_time = now

                        # Kareye uyarı çiz
                        with self.lock:
                            cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0,0,255), 10)
                            cv2.putText(frame, f"DÜŞME ALGILANDI! ({confidence:.2f})", (20, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                            self.current_frame = frame

                        logger.warning(f"DÜŞME ALGILANDI! Güven: {confidence:.2f}")

                        # Bildirim ve olay kaydı fonksiyonlarını çağır
                        notify_fall(frame, confidence)
                        save_fall_event(frame, confidence)
                else:
                    self.is_fall_detected = False
                    self.fall_confidence = 0.0

        except Exception as e:
            logger.error(f"Düşme algılama döngüsünde hata: {str(e)}", exc_info=True)
        finally:
            logger.info("Düşme algılama thread'i durduruldu.")

    def get_frame(self):
        """
        Mevcut kareyi JPEG formatında döndürür.
        """
        with self.lock:
            if self.current_frame is None:
                empty = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), dtype=np.uint8)
                ret, jpeg = cv2.imencode('.jpg', empty)
                return jpeg.tobytes()
            # FPS bilgisini köşeye ekle
            cv2.putText(self.current_frame, f"FPS: {self.fps:.1f}", (self.current_frame.shape[1] - 120, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            ret, jpeg = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
            if not ret:
                logger.warning("Kare JPEG formatına dönüştürülemedi")
                return None
            return jpeg.tobytes()

    def reset_fall_detection(self):
        with self.lock:
            self.is_fall_detected = False
            self.fall_confidence = 0.0
            logger.info("Düşme algılama durumu sıfırlandı")
            return True

    def __del__(self):
        self.stop_thread = True
        if hasattr(self, 'frame_thread'):
            self.frame_thread.join(timeout=1.0)
        if hasattr(self, 'detection_thread'):
            self.detection_thread.join(timeout=1.0)
        if hasattr(self, 'video') and self.video.isOpened():
            self.video.release()
        logger.info("VideoCamera nesnesi temizlendi")

# =================== Kamera Nesnesi ===================
try:
    camera = VideoCamera()
    logger.info("Kamera başarıyla başlatıldı")
except Exception as e:
    logger.error(f"Kamera başlatılamadı: {str(e)}", exc_info=True)
    camera = None

# =================== MJPEG Akışı İçin Generator ===================
def gen_frames():
    try:
        while camera is not None:
            frame = camera.get_frame()
            if frame is None:
                logger.warning("Boş kare alındı, 100ms bekleniyor")
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            time.sleep(max(0, 1.0 / MAX_FPS))
    except Exception as e:
        logger.error(f"Kare jeneratöründe hata: {str(e)}", exc_info=True)
    finally:
        logger.info("Kare jeneratörü sonlandı")

# =================== Flask Rotaları ===================
@app.route('/video_feed')
def video_feed():
    if camera is None:
        return "Kamera başlatılamadı", 503
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/fall_status')
def fall_status():
    if camera is None:
        return jsonify({'error': 'Kamera başlatılamadı'}), 503
    return jsonify({
        'fall_detected': camera.is_fall_detected,
        'confidence': float(camera.fall_confidence),
        'last_fall_time': camera.last_fall_time
    })

@app.route('/reset_fall', methods=['POST'])
def reset_fall():
    if camera is None:
        return jsonify({'error': 'Kamera başlatılamadı'}), 503
    success = camera.reset_fall_detection()
    return jsonify({'success': success})

@app.route('/server_status')
def server_status():
    if camera is None:
        logger.error("Kamera başlatılamadı, server_status çağrıldı")
        return jsonify({'status': 'error', 'message': 'Kamera başlatılamadı'}), 503
    logger.info(f"Server status requested: FPS={camera.fps}")
    return jsonify({
        'status': 'ok',
        'fps': camera.fps,
        'fall_detection': True
    })

if __name__ == '__main__':
    try:
        logger.info(f"Sunucu başlatılıyor {SERVER_HOST}:{SERVER_PORT}...")
        app.run(host=SERVER_HOST, port=SERVER_PORT, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Sunucu başlatılırken hata: {str(e)}", exc_info=True)

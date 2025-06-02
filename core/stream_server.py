# =======================================================================================
# 📄 Dosya Adı   : stream_server.py
# 📁 Konum       : pc/core/stream_server.py
# 📌 Açıklama    : YOLOv11 entegreli MJPEG video akışı sağlayan Flask sunucusu
#                 Gerçek zamanlı düşme algılama ve canlı görüntü akışı
#
# 🔗 Bağlantılı Dosyalar:
#   - core/fall_detection.py   : YOLOv11 düşme algılama modeli
#   - core/camera.py           : Kamera yönetimi
#   - core/notification.py     : Bildirim gönderimi
#   - data/database.py         : Olay kaydı (Firestore)
#   - config/settings.py       : Ayar ve sabitler
#
# 🗒️ Notlar:
#   - /video_feed              : YOLOv11 tespit kutularıyla canlı MJPEG akışı
#   - /raw_feed               : Ham kamera görüntüsü (tespit kutuları olmadan)
#   - /fall_status            : Son düşme algılama durumu (JSON)
#   - /reset_fall             : Düşme durumunu sıfırlar (POST)
#   - /server_status          : Sunucu, kamera ve model durumu (JSON)
#   - /model_info             : YOLOv11 model bilgileri (JSON)
# =======================================================================================

import cv2
import threading
import time
import logging
import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import os
import json
import uuid

# YOLOv11 ve sistem bileşenlerini import et
from core.fall_detection import FallDetector
from core.camera import Camera
from data.database import FirestoreManager
from data.storage import StorageManager

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

# =============== Kamera ve Model Ayarları ===============
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
MJPEG_QUALITY = 85
MAX_FPS = 30
STREAM_WIDTH = 640
STREAM_HEIGHT = 640

class YOLOv11StreamServer:
    """
    YOLOv11 entegreli video akış sunucusu
    """

    def __init__(self):
        """Sunucu bileşenlerini başlatır"""
        logger.info("YOLOv11 Stream Server başlatılıyor...")
        
        # Sistem bileşenleri
        self.camera = None
        self.fall_detector = None
        self.db_manager = None
        self.storage_manager = None
        
        # Düşme algılama durumu
        self.last_fall_detection = {
            'detected': False,
            'confidence': 0.0,
            'timestamp': 0,
            'event_id': None
        }
        
        # Performans ölçümleri
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        
        # Thread güvenliği
        self.detection_lock = threading.Lock()
        
        # Sistem bileşenlerini başlat
        self._initialize_components()
        
        logger.info("YOLOv11 Stream Server başlatıldı")

    def _initialize_components(self):
        """Sistem bileşenlerini başlatır"""
        try:
            # Kamera sistemi
            self.camera = Camera.get_instance()
            logger.info("Kamera sistemi başlatıldı")
            
            # YOLOv11 düşme algılama modeli
            self.fall_detector = FallDetector.get_instance()
            if self.fall_detector.is_model_loaded:
                logger.info("YOLOv11 düşme algılama modeli başlatıldı")
            else:
                logger.warning("YOLOv11 modeli yüklenemedi")
            
            # Veritabanı ve depolama
            try:
                self.db_manager = FirestoreManager()
                self.storage_manager = StorageManager()
                logger.info("Veritabanı ve depolama sistemleri başlatıldı")
            except Exception as e:
                logger.warning(f"Veritabanı başlatılamadı: {e}")
                
        except Exception as e:
            logger.error(f"Sistem bileşenleri başlatılırken hata: {e}")

    def get_camera_frame(self, with_detection=True):
        """
        Kameradan frame alır ve isteğe bağlı olarak YOLOv11 tespitlerini ekler
        
        Args:
            with_detection (bool): Tespit kutularını ekle
            
        Returns:
            bytes: JPEG frame data
        """
        try:
            if not self.camera or not self.camera.is_running:
                return self._generate_error_frame("Kamera bağlı değil")
            
            # Kameradan frame al
            frame = self.camera.get_frame()
            if frame is None or frame.size == 0:
                return self._generate_error_frame("Frame alınamadı")
            
            # Frame'i 640x640 boyutuna ayarla
            frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT))
            
            # YOLOv11 tespitlerini ekle (isteğe bağlı)
            if with_detection and self.fall_detector and self.fall_detector.is_model_loaded:
                frame = self._add_detection_overlay(frame)
            
            # FPS bilgisini ekle
            frame = self._add_fps_overlay(frame)
            
            # JPEG'e dönüştür
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
            
            if not ret:
                return self._generate_error_frame("Frame encode edilemedi")
            
            return jpeg.tobytes()
            
        except Exception as e:
            logger.error(f"Frame alma hatası: {e}")
            return self._generate_error_frame(f"Hata: {str(e)}")

    def _add_detection_overlay(self, frame):
        """
        Frame'e YOLOv11 tespit kutularını ekler
        
        Args:
            frame (numpy.ndarray): İşlenecek frame
            
        Returns:
            numpy.ndarray: Tespit kutuları eklenmiş frame
        """
        try:
            # YOLOv11 ile düşme tespiti yap ve görselleştir
            annotated_frame = self.fall_detector.get_detection_visualization(frame)
            
            # Düşme algılama durumunu kontrol et (performans için seyrek)
            current_time = time.time()
            if current_time - self.last_fall_detection['timestamp'] > 3.0:  # 3 saniyede bir kontrol
                is_fall, confidence = self.fall_detector.detect_fall(frame)
                
                with self.detection_lock:
                    if is_fall:
                        self.last_fall_detection.update({
                            'detected': True,
                            'confidence': float(confidence),
                            'timestamp': current_time,
                            'event_id': str(uuid.uuid4())
                        })
                        
                        # Düşme algılandığında olay kaydet (arka planda)
                        threading.Thread(
                            target=self._handle_fall_event,
                            args=(frame.copy(), confidence),
                            daemon=True
                        ).start()
                        
                        logger.info(f"YOLOv11 Düşme algılandı! Güven: {confidence:.4f}")
            
            # Aktif düşme uyarısı varsa frame'e ekle
            if self.last_fall_detection['detected'] and \
               current_time - self.last_fall_detection['timestamp'] < 10.0:  # 10 saniye boyunca göster
                annotated_frame = self._add_fall_alert_overlay(annotated_frame)
            
            return annotated_frame
            
        except Exception as e:
            logger.error(f"Detection overlay hatası: {e}")
            return frame

    def _add_fall_alert_overlay(self, frame):
        """
        Düşme uyarısı overlay'i ekler
        
        Args:
            frame (numpy.ndarray): Frame
            
        Returns:
            numpy.ndarray: Uyarı eklenmiş frame
        """
        try:
            # Kırmızı kenar ekle
            cv2.rectangle(frame, (0, 0), (frame.shape[1]-1, frame.shape[0]-1), (0, 0, 255), 8)
            
            # Uyarı metni
            alert_text = "DÜŞME ALGILANDI!"
            confidence_text = f"Güven: {self.last_fall_detection['confidence']:.2f}"
            
            # Metin boyutları
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.2
            thickness = 3
            
            # Metin konumları
            (text_width, text_height), _ = cv2.getTextSize(alert_text, font, font_scale, thickness)
            text_x = (frame.shape[1] - text_width) // 2
            text_y = 50
            
            # Arka plan dikdörtgeni
            cv2.rectangle(frame, 
                         (text_x - 10, text_y - text_height - 10),
                         (text_x + text_width + 10, text_y + 10),
                         (0, 0, 255), -1)
            
            # Ana uyarı metni
            cv2.putText(frame, alert_text, (text_x, text_y), 
                       font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            
            # Güven değeri metni
            (conf_width, conf_height), _ = cv2.getTextSize(confidence_text, font, 0.8, 2)
            conf_x = (frame.shape[1] - conf_width) // 2
            conf_y = text_y + 40
            
            cv2.rectangle(frame,
                         (conf_x - 5, conf_y - conf_height - 5),
                         (conf_x + conf_width + 5, conf_y + 5),
                         (0, 0, 200), -1)
            
            cv2.putText(frame, confidence_text, (conf_x, conf_y),
                       font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
            return frame
            
        except Exception as e:
            logger.error(f"Fall alert overlay hatası: {e}")
            return frame

    def _add_fps_overlay(self, frame):
        """
        Frame'e FPS bilgisini ekler
        
        Args:
            frame (numpy.ndarray): Frame
            
        Returns:
            numpy.ndarray: FPS bilgisi eklenmiş frame
        """
        try:
            # FPS hesapla
            self.frame_count += 1
            elapsed_time = time.time() - self.start_time
            
            if elapsed_time >= 2.0:  # Her 2 saniyede güncelle
                self.fps = self.frame_count / elapsed_time
                self.frame_count = 0
                self.start_time = time.time()
            
            # FPS metnini ekle
            fps_text = f"FPS: {self.fps:.1f}"
            model_status = "YOLOv11: ON" if (self.fall_detector and self.fall_detector.is_model_loaded) else "YOLOv11: OFF"
            
            # Sol üst köşeye FPS
            cv2.putText(frame, fps_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Sağ üst köşeye model durumu
            text_size = cv2.getTextSize(model_status, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            text_x = frame.shape[1] - text_size[0] - 10
            
            cv2.putText(frame, model_status, (text_x, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if "ON" in model_status else (0, 0, 255), 2, cv2.LINE_AA)
            
            return frame
            
        except Exception as e:
            logger.error(f"FPS overlay hatası: {e}")
            return frame

    def _generate_error_frame(self, error_message):
        """
        Hata mesajı içeren frame oluşturur
        
        Args:
            error_message (str): Hata mesajı
            
        Returns:
            bytes: JPEG frame data
        """
        try:
            # Siyah frame oluştur
            frame = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), dtype=np.uint8)
            
            # Hata metnini ekle
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(error_message, font, 0.8, 2)[0]
            text_x = (STREAM_WIDTH - text_size[0]) // 2
            text_y = (STREAM_HEIGHT + text_size[1]) // 2
            
            cv2.putText(frame, error_message, (text_x, text_y),
                       font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
            
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
            return jpeg.tobytes() if ret else b''
            
        except Exception as e:
            logger.error(f"Error frame oluşturma hatası: {e}")
            return b''

    def _handle_fall_event(self, frame, confidence):
        """
        Düşme olayını işler ve veritabanına kaydeder
        
        Args:
            frame (numpy.ndarray): Olay anındaki frame
            confidence (float): Düşme güven değeri
        """
        try:
            if not self.db_manager or not self.storage_manager:
                logger.warning("Veritabanı veya depolama sistemi mevcut değil")
                return
            
            # Event ID oluştur
            event_id = self.last_fall_detection['event_id']
            if not event_id:
                event_id = str(uuid.uuid4())
            
            # Frame'i kaydet (test amaçlı - gerçek sistemde kullanıcı ID'si gerekli)
            # Burada test kullanıcısı kullanıyoruz
            test_user_id = "test_user_stream"
            
            # Görüntüyü storage'a yükle
            image_url = self.storage_manager.upload_screenshot(
                test_user_id,
                frame,
                event_id
            )
            
            # Olay verilerini oluştur
            event_data = {
                "id": event_id,
                "user_id": test_user_id,
                "timestamp": time.time(),
                "confidence": float(confidence),
                "image_url": image_url,
                "detection_method": "YOLOv11_Stream",
                "source": "stream_server"
            }
            
            # Veritabanına kaydet
            success = self.db_manager.save_fall_event(test_user_id, event_data)
            
            if success:
                logger.info(f"YOLOv11 Stream: Düşme olayı kaydedildi - ID: {event_id}")
            else:
                logger.error("YOLOv11 Stream: Düşme olayı kaydedilemedi")
                
        except Exception as e:
            logger.error(f"Fall event işleme hatası: {e}")

# =============== Global Stream Server Instance ===============
stream_server = YOLOv11StreamServer()

# =============== Flask Route Handlers ===============

def generate_video_frames(with_detection=True):
    """MJPEG video frame generator"""
    try:
        while True:
            frame = stream_server.get_camera_frame(with_detection=with_detection)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            time.sleep(max(0, 1.0 / MAX_FPS))
    except Exception as e:
        logger.error(f"Video frame generator hatası: {e}")

@app.route('/video_feed')
def video_feed():
    """YOLOv11 tespit kutularıyla canlı video akışı"""
    try:
        return Response(
            generate_video_frames(with_detection=True),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"Video feed hatası: {e}")
        return "Video feed hatası", 500

@app.route('/raw_feed')
def raw_feed():
    """Ham kamera görüntüsü (tespit kutuları olmadan)"""
    try:
        return Response(
            generate_video_frames(with_detection=False),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"Raw feed hatası: {e}")
        return "Raw feed hatası", 500

@app.route('/fall_status')
def fall_status():
    """Son düşme algılama durumunu döndürür"""
    try:
        with stream_server.detection_lock:
            status = stream_server.last_fall_detection.copy()
        
        # Zaman damgasını okunabilir formata çevir
        if status['timestamp'] > 0:
            status['timestamp_readable'] = time.strftime(
                "%Y-%m-%d %H:%M:%S", 
                time.localtime(status['timestamp'])
            )
        
        return jsonify({
            'success': True,
            'fall_status': status,
            'server_time': time.time()
        })
        
    except Exception as e:
        logger.error(f"Fall status hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reset_fall', methods=['POST'])
def reset_fall():
    """Düşme algılama durumunu sıfırlar"""
    try:
        with stream_server.detection_lock:
            stream_server.last_fall_detection = {
                'detected': False,
                'confidence': 0.0,
                'timestamp': 0,
                'event_id': None
            }
        
        logger.info("Düşme algılama durumu sıfırlandı")
        return jsonify({
            'success': True,
            'message': 'Düşme durumu sıfırlandı'
        })
        
    except Exception as e:
        logger.error(f"Reset fall hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/server_status')
def server_status():
    """Sunucu, kamera ve model durumunu döndürür"""
    try:
        # Kamera durumu
        camera_status = {
            'connected': stream_server.camera is not None,
            'running': stream_server.camera.is_running if stream_server.camera else False,
            'fps': stream_server.fps
        }
        
        if stream_server.camera:
            camera_status.update(stream_server.camera.get_camera_status())
        
        # Model durumu
        model_status = {
            'loaded': False,
            'info': {}
        }
        
        if stream_server.fall_detector:
            model_status['loaded'] = stream_server.fall_detector.is_model_loaded
            if model_status['loaded']:
                model_status['info'] = stream_server.fall_detector.get_model_info()
        
        # Sistem durumu
        system_status = {
            'uptime': time.time() - stream_server.start_time,
            'database_connected': stream_server.db_manager is not None,
            'storage_connected': stream_server.storage_manager is not None
        }
        
        return jsonify({
            'success': True,
            'server_status': 'running',
            'camera': camera_status,
            'yolov11_model': model_status,
            'system': system_status,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Server status hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/model_info')
def model_info():
    """YOLOv11 model bilgilerini döndürür"""
    try:
        if not stream_server.fall_detector:
            return jsonify({
                'success': False,
                'error': 'Model yüklenmemiş'
            }), 404
        
        info = stream_server.fall_detector.get_model_info()
        
        return jsonify({
            'success': True,
            'model_info': info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Model info hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/start_camera', methods=['POST'])
def start_camera():
    """Kamerayı başlatır"""
    try:
        if not stream_server.camera:
            return jsonify({
                'success': False,
                'error': 'Kamera sistemi mevcut değil'
            }), 500
        
        if stream_server.camera.is_running:
            return jsonify({
                'success': True,
                'message': 'Kamera zaten çalışıyor'
            })
        
        success = stream_server.camera.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Kamera başlatıldı'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Kamera başlatılamadı'
            }), 500
            
    except Exception as e:
        logger.error(f"Start camera hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    """Kamerayı durdurur"""
    try:
        if not stream_server.camera:
            return jsonify({
                'success': False,
                'error': 'Kamera sistemi mevcut değil'
            }), 500
        
        if not stream_server.camera.is_running:
            return jsonify({
                'success': True,
                'message': 'Kamera zaten durmuş'
            })
        
        stream_server.camera.stop()
        
        return jsonify({
            'success': True,
            'message': 'Kamera durduruldu'
        })
        
    except Exception as e:
        logger.error(f"Stop camera hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reload_model', methods=['POST'])
def reload_model():
    """YOLOv11 modelini yeniden yükler"""
    try:
        if not stream_server.fall_detector:
            return jsonify({
                'success': False,
                'error': 'Model sistemi mevcut değil'
            }), 500
        
        success = stream_server.fall_detector.reload_model()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Model başarıyla yeniden yüklendi',
                'model_info': stream_server.fall_detector.get_model_info()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Model yeniden yüklenemedi'
            }), 500
            
    except Exception as e:
        logger.error(f"Reload model hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Ana sayfa - şık ve modern YOLOv11 test sayfası"""
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <title>Guard YOLOv11 Stream Server</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                transition: background 0.3s ease;
            }
            .dark-theme {
                background: linear-gradient(135deg, #1e2a44 0%, #2a4066 100%);
                color: #e0e0e0;
            }
            .container {
                max-width: 900px;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
                transition: all 0.3s ease;
            }
            .dark-theme .container {
                background: rgba(30, 42, 68, 0.95);
                color: #e0e0e0;
            }
            h1 {
                color: #1a2a44;
                text-align: center;
                font-size: 2.2rem;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            .dark-theme h1 { color: #ffffff; }
            .video-container {
                text-align: center;
                margin: 20px 0;
                background: #f0f2f5;
                border-radius: 15px;
                padding: 20px;
                transition: all 0.3s ease;
            }
            .dark-theme .video-container { background: #2a4066; }
            .video-stream {
                border: 3px solid #e0e0e0;
                border-radius: 12px;
                max-width: 100%;
                transition: border-color 0.3s ease;
            }
            .dark-theme .video-stream { border-color: #4a6fa5; }
            .controls {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 15px;
                margin: 20px 0;
            }
            .btn {
                background: linear-gradient(45deg, #4CAF50, #66BB6A);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 50px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }
            .btn.danger {
                background: linear-gradient(45deg, #f44336, #ef5350);
            }
            .status {
                margin: 20px 0;
                padding: 20px;
                background: #e3f2fd;
                border-radius: 12px;
                border-left: 5px solid #2196F3;
                transition: all 0.3s ease;
            }
            .dark-theme .status { background: #2a4066; border-left-color: #64b5f6; }
            .info {
                margin-top: 20px;
                padding: 20px;
                background: #f0f2f5;
                border-radius: 12px;
                font-size: 0.9rem;
                line-height: 1.8;
                transition: all 0.3s ease;
            }
            .dark-theme .info { background: #2a4066; }
            .info ul { margin-left: 20px; }
            .theme-toggle {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            }
            .theme-toggle:hover {
                background: #45a049;
                transform: rotate(360deg);
            }
            @media (max-width: 600px) {
                .container { padding: 20px; }
                h1 { font-size: 1.8rem; }
                .btn { padding: 10px 18px; font-size: 0.9rem; }
            }
        </style>
    </head>
    <body>
        <button class="theme-toggle" onclick="toggleTheme()">🌙</button>
        <div class="container">
            <h1><span>🛡️</span> Guard YOLOv11 Düşme Algılama Sistemi</h1>
            
            <div class="video-container">
                <h3>Canlı YOLOv11 Algılama</h3>
                <img src="/video_feed" class="video-stream" alt="YOLOv11 Video Stream">
            </div>
            
            <div class="controls">
                <button class="btn" onclick="startCamera()"><span>📹</span> Kamerayı Başlat</button>
                <button class="btn danger" onclick="stopCamera()"><span>⏹️</span> Kamerayı Durdur</button>
                <button class="btn" onclick="reloadModel()"><span>🔄</span> Model Yenile</button>
                <button class="btn" onclick="resetFall()"><span>🔄</span> Düşme Sıfırla</button>
            </div>
            
            <div class="status">
                <h4>📊 Sistem Durumu</h4>
                <div id="status-info">Durum bilgisi yükleniyor...</div>
            </div>
            
            <div class="info">
                <h4>📝 API Endpoints</h4>
                <ul>
                    <li><strong>/video_feed</strong> - YOLOv11 tespit kutularıyla canlı video</li>
                    <li><strong>/raw_feed</strong> - Ham kamera görüntüsü</li>
                    <li><strong>/fall_status</strong> - Düşme algılama durumu</li>
                    <li><strong>/server_status</strong> - Sunucu durumu</li>
                    <li><strong>/model_info</strong> - YOLOv11 model bilgileri</li>
                </ul>
            </div>
        </div>
        
        <script>
            function toggleTheme() {
                document.body.classList.toggle('dark-theme');
                localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
            }

            // Tema yükleme
            if (localStorage.getItem('theme') === 'dark') {
                document.body.classList.add('dark-theme');
            }

            function updateStatus() {
                fetch('/server_status')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const status = data;
                            document.getElementById('status-info').innerHTML = `
                                <strong>Kamera:</strong> ${status.camera.running ? '✅ Aktif' : '❌ Kapalı'} (FPS: ${status.camera.fps || 0})<br>
                                <strong>YOLOv11:</strong> ${status.yolov11_model.loaded ? '✅ Yüklü' : '❌ Yüklenmemiş'}<br>
                                <strong>Veritabanı:</strong> ${status.system.database_connected ? '✅ Bağlı' : '❌ Bağlı değil'}<br>
                                <strong>Çalışma Süresi:</strong> ${Math.round(status.system.uptime)} saniye
                            `;
                        }
                    })
                    .catch(error => {
                        document.getElementById('status-info').innerHTML = '❌ Durum bilgisi alınamadı';
                    });
            }
            
            function startCamera() {
                fetch('/start_camera', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => alert(data.message || data.error));
            }
            
            function stopCamera() {
                fetch('/stop_camera', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => alert(data.message || data.error));
            }
            
            function reloadModel() {
                fetch('/reload_model', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => alert(data.message || data.error));
            }
            
            function resetFall() {
                fetch('/reset_fall', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => alert(data.message || data.error));
            }
            
            // Sayfa yüklendiğinde ve her 5 saniyede bir durum güncelle
            updateStatus();
            setInterval(updateStatus, 5000);
        </script>
    </body>
    </html>
    """
    return html_content

# =============== Ana Başlatma Fonksiyonu ===============
def run_stream_server(host=SERVER_HOST, port=SERVER_PORT, debug=False):
    """
    YOLOv11 Stream Server'ı başlatır
    
    Args:
        host (str): Sunucu host adresi
        port (int): Sunucu portu
        debug (bool): Debug modu
    """
    try:
        logger.info(f"YOLOv11 Stream Server başlatılıyor: http://{host}:{port}")
        
        # Kamerayı otomatik başlat
        if stream_server.camera:
            stream_server.camera.start()
            logger.info("Kamera otomatik olarak başlatıldı")
        
        # Flask sunucusunu başlat
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=False  # Reloader ile model yeniden yüklenmesini engelle
        )
        
    except Exception as e:
        logger.error(f"Stream server başlatılırken hata: {e}")
        raise

if __name__ == '__main__':
    try:
        run_stream_server()
    except KeyboardInterrupt:
        logger.info("Stream server durduruldu")
    except Exception as e:
        logger.error(f"Stream server hatası: {e}")
        raise
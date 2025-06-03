# =======================================================================================
# 📄 Dosya Adı: stream_server.py
# 📁 Konum: guard_pc_app/core/stream_server.py
# 📌 Açıklama:
# YOLOv11 tabanlı video akış sunucusu.
# Camera.get_instance hatası düzeltildi, Camera sınıfı doğrudan örnekleniyor.
# Mobil uygulama için görüntüleme desteği korundu.
# 🔗 Bağlantılı Dosyalar:
# - core/camera.py: Kamera yönetimi
# - config/settings.py: CAMERA_CONFIGS
# =======================================================================================

import logging
import cv2
from flask import Flask, Response
import threading
from core.camera import Camera
from config.settings import CAMERA_CONFIGS

app = Flask(__name__)

class StreamServer:
    """YOLOv11 tabanlı video akış sunucusu."""
    
    def __init__(self):
        """Stream sunucusunu başlatır."""
        self.cameras = []
        self.is_running = False
        self._initialize_cameras()
    
    def _initialize_cameras(self):
        """Kameraları başlatır."""
        try:
            for config in CAMERA_CONFIGS:
                camera = Camera(camera_index=config['index'], backend=config['backend'])
                if camera._validate_camera():
                    self.cameras.append(camera)
                    logging.info(f"Kamera eklendi: {config['name']} (indeks: {config['index']}, backend: {config['backend']})")
                else:
                    logging.warning(f"Kamera {config['index']} başlatılamadı.")
            
            if not self.cameras:
                logging.error("Hiçbir kamera başlatılamadı!")
        except Exception as e:
            logging.error(f"Sistem bileşenleri başlatılırken hata: {str(e)}")

    def generate_frames(self, camera_index=0):
        """Video akışını üretir."""
        if not self.cameras or camera_index >= len(self.cameras):
            logging.error(f"Geçersiz kamera indeksi: {camera_index}")
            return
        
        camera = self.cameras[camera_index]
        while self.is_running:
            try:
                frame = camera.get_frame()
                if frame is None:
                    continue
                
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
            except Exception as e:
                logging.error(f"Frame üretimi sırasında hata: {str(e)}")
                time.sleep(0.1)

    @app.route('/video_feed/<int:camera_index>')
    def video_feed(camera_index):
        """Video akışını Flask üzerinden sunar."""
        server = app.config['stream_server']
        return Response(server.generate_frames(camera_index),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    def start(self):
        """Sunucuyu başlatır."""
        try:
            self.is_running = True
            app.config['stream_server'] = self
            logging.info("YOLOv11 Stream Server başlatılıyor...")
            app.run(host='0.0.0.0', port=5000, threaded=True)
            logging.info("YOLOv11 Stream Server başlatıldı")
        except Exception as e:
            logging.error(f"Stream Server başlatılırken hata: {str(e)}")
            self.is_running = False

    def stop(self):
        """Sunucuyu durdurur."""
        self.is_running = False
        for camera in self.cameras:
            camera.stop()
        logging.info("YOLOv11 Stream Server durduruldu")

def run_api_server_in_thread():
    """API sunucusunu bir thread olarak çalıştırır."""
    server = StreamServer()
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    server = StreamServer()
    server.start()
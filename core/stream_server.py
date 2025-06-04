# =======================================================================================
# 📄 Dosya Adı: stream_server.py (ENHANCED VERSION)
# 📁 Konum: guard_pc_app/core/stream_server.py
# 📌 Açıklama:
# YOLOv11 Pose Estimation entegreli video stream server.
# Gelişmiş kamera yönetimi ve pose visualization desteği.
# Mobil uygulama için optimize edilmiş stream endpoint'leri.
# =======================================================================================

import logging
import cv2
import time
import json
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import threading
from core.camera import Camera
from core.fall_detection import FallDetector
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT
import numpy as np

app = Flask(__name__)
CORS(app)  # CORS desteği ekle

class StreamServer:
    """YOLOv11 Pose Estimation entegreli video stream sunucusu."""
    
    def __init__(self):
        """Stream sunucusunu başlatır."""
        self.cameras = {}  # {camera_id: Camera object}
        self.is_running = False
        self.fall_detector = None
        self.pose_visualization_enabled = True
        self.stream_stats = {
            'total_connections': 0,
            'active_streams': 0,
            'total_frames_served': 0,
            'start_time': time.time()
        }
        self._initialize_components()
    
    def _initialize_components(self):
        """Kameraları ve AI bileşenlerini başlatır."""
        try:
            # Kameraları başlat
            for config in CAMERA_CONFIGS:
                camera_id = f"camera_{config['index']}"
                logging.info(f"Stream Server: Kamera başlatılıyor - {config['name']}")
                
                camera = Camera(camera_index=config['index'], backend=config['backend'])
                if camera._validate_camera_with_fallback():
                    self.cameras[camera_id] = {
                        'camera': camera,
                        'config': config,
                        'active_streams': 0,
                        'total_frames': 0,
                        'last_access': time.time()
                    }
                    logging.info(f"Stream Server: Kamera eklendi - {config['name']}")
                else:
                    logging.warning(f"Stream Server: Kamera {config['index']} başlatılamadı")
            
            # Fall detector'ı başlat
            try:
                self.fall_detector = FallDetector.get_instance()
                logging.info("Stream Server: YOLOv11 Fall Detector başlatıldı")
            except Exception as e:
                logging.warning(f"Stream Server: Fall Detector başlatılamadı: {str(e)}")
                self.fall_detector = None
            
            if not self.cameras:
                logging.error("Stream Server: Hiçbir kamera başlatılamadı!")
            else:
                logging.info(f"Stream Server: {len(self.cameras)} kamera başlatıldı")
                
        except Exception as e:
            logging.error(f"Stream Server başlatılırken hata: {str(e)}")
    
    def start_camera(self, camera_id):
        """Belirli bir kamerayı başlatır."""
        if camera_id in self.cameras:
            camera_info = self.cameras[camera_id]
            if not camera_info['camera'].is_running:
                success = camera_info['camera'].start()
                if success:
                    logging.info(f"Stream Server: Kamera {camera_id} başlatıldı")
                return success
            return True
        return False
    
    def stop_camera(self, camera_id):
        """Belirli bir kamerayı durdurur."""
        if camera_id in self.cameras:
            camera_info = self.cameras[camera_id]
            if camera_info['camera'].is_running:
                camera_info['camera'].stop()
                logging.info(f"Stream Server: Kamera {camera_id} durduruldu")
    
    def generate_frames(self, camera_id, include_pose=True, include_detection=True):
        """
        Video akışı üretir - YOLOv11 Pose entegrasyonu ile.
        
        Args:
            camera_id (str): Kamera ID'si
            include_pose (bool): Pose visualization dahil et
            include_detection (bool): Fall detection dahil et
        """
        if camera_id not in self.cameras:
            logging.error(f"Stream Server: Geçersiz kamera ID: {camera_id}")
            yield self._generate_error_frame(f"Kamera {camera_id} bulunamadı")
            return
        
        camera_info = self.cameras[camera_id]
        camera = camera_info['camera']
        
        # Kamerayı başlat
        if not camera.is_running:
            if not self.start_camera(camera_id):
                yield self._generate_error_frame(f"Kamera {camera_id} başlatılamadı")
                return
        
        camera_info['active_streams'] += 1
        self.stream_stats['active_streams'] += 1
        self.stream_stats['total_connections'] += 1
        
        logging.info(f"Stream Server: {camera_id} stream başlatıldı (Pose: {include_pose}, Detection: {include_detection})")
        
        try:
            frame_count = 0
            last_fps_time = time.time()
            fps = 0
            
            while self.is_running:
                start_time = time.time()
                
                try:
                    # Frame al
                    frame = camera.get_frame()
                    if frame is None or frame.size == 0:
                        yield self._generate_error_frame("Kamera bağlantısı yok")
                        time.sleep(0.1)
                        continue
                    
                    # AI işleme
                    processed_frame = frame.copy()
                    
                    if self.fall_detector and (include_pose or include_detection):
                        try:
                            # YOLOv11 Pose Estimation + DeepSORT
                            annotated_frame, tracks = self.fall_detector.get_detection_visualization(frame)
                            
                            if include_pose:
                                processed_frame = annotated_frame
                            
                            # Fall detection (sadece detection aktifse)
                            if include_detection:
                                is_fall, confidence, track_id = self.fall_detector.detect_fall(frame, tracks)
                                
                                if is_fall and confidence > 0.6:
                                    # Fall alert overlay ekle
                                    self._add_fall_alert_overlay(processed_frame, confidence, track_id)
                            
                            # Tracking bilgilerini overlay olarak ekle
                            if tracks:
                                self._add_tracking_overlay(processed_frame, tracks, fps)
                        
                        except Exception as e:
                            logging.error(f"AI işleme hatası: {str(e)}")
                            # AI hatası durumunda normal frame kullan
                            processed_frame = frame
                    
                    # Stream info overlay
                    self._add_stream_overlay(processed_frame, camera_id, fps, include_pose, include_detection)
                    
                    # Frame'i encode et
                    ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                             [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    if not ret:
                        yield self._generate_error_frame("Frame encode hatası")
                        continue
                    
                    frame_bytes = buffer.tobytes()
                    
                    # MJPEG stream format
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                           frame_bytes + b'\r\n')
                    
                    # İstatistikleri güncelle
                    frame_count += 1
                    camera_info['total_frames'] += 1
                    camera_info['last_access'] = time.time()
                    self.stream_stats['total_frames_served'] += 1
                    
                    # FPS hesapla
                    if time.time() - last_fps_time >= 1.0:
                        fps = frame_count / (time.time() - last_fps_time)
                        frame_count = 0
                        last_fps_time = time.time()
                    
                    # Frame rate kontrolü (~30 FPS)
                    elapsed = time.time() - start_time
                    sleep_time = max(0, 1/30 - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                except Exception as e:
                    logging.error(f"Frame işleme hatası: {str(e)}")
                    yield self._generate_error_frame("Frame işleme hatası")
                    time.sleep(0.1)
                    
        except GeneratorExit:
            # Stream kapatıldı
            pass
        except Exception as e:
            logging.error(f"Stream hatası: {str(e)}")
        finally:
            # Cleanup
            camera_info['active_streams'] -= 1
            self.stream_stats['active_streams'] -= 1
            logging.info(f"Stream Server: {camera_id} stream sonlandı")
    
    def _add_fall_alert_overlay(self, frame, confidence, track_id):
        """Düşme uyarısı overlay'i ekler."""
        h, w = frame.shape[:2]
        
        # Kırmızı overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        # Alert text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"FALL DETECTED! ID:{track_id} Conf:{confidence:.2f}"
        text_size = cv2.getTextSize(text, font, 1.2, 2)[0]
        text_x = (w - text_size[0]) // 2
        
        cv2.putText(frame, text, (text_x, 50), font, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, text, (text_x, 50), font, 1.2, (0, 0, 255), 2)
    
    def _add_tracking_overlay(self, frame, tracks, fps):
        """Tracking bilgileri overlay'i ekler."""
        h, w = frame.shape[:2]
        y_offset = h - 120
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, y_offset - 10), (300, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (255, 255, 255)
        
        # Tracking stats
        cv2.putText(frame, f"YOLOv11 + DeepSORT", (15, y_offset + 15), 
                   font, font_scale, (0, 255, 255), 1)
        cv2.putText(frame, f"Active Tracks: {len(tracks)}", (15, y_offset + 35), 
                   font, font_scale, color, 1)
        cv2.putText(frame, f"FPS: {fps:.1f}", (15, y_offset + 55), 
                   font, font_scale, color, 1)
        
        # Track details
        for i, track in enumerate(tracks[:3]):  # Max 3 track göster
            track_id = track.get('track_id', 'N/A')
            confidence = track.get('confidence', 0)
            cv2.putText(frame, f"ID:{track_id} ({confidence:.2f})", (15, y_offset + 75 + i*15), 
                       font, 0.5, (0, 255, 0), 1)
    
    def _add_stream_overlay(self, frame, camera_id, fps, pose_enabled, detection_enabled):
        """Stream bilgi overlay'i ekler."""
        h, w = frame.shape[:2]
        
        # Timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Header overlay
        cv2.rectangle(frame, (0, 0), (w, 30), (50, 50, 50), -1)
        
        # Camera info
        cv2.putText(frame, f"{camera_id.replace('_', ' ').title()}", (10, 20), 
                   font, 0.6, (255, 255, 255), 1)
        
        # AI status
        ai_status = []
        if pose_enabled:
            ai_status.append("Pose")
        if detection_enabled:
            ai_status.append("Detection")
        
        if ai_status:
            ai_text = f"AI: {'+'.join(ai_status)}"
            cv2.putText(frame, ai_text, (150, 20), font, 0.5, (0, 255, 255), 1)
        
        # Timestamp
        cv2.putText(frame, timestamp, (w - 150, 20), font, 0.5, (255, 255, 255), 1)
    
    def _generate_error_frame(self, error_message):
        """Hata frame'i üretir."""
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(error_message, font, 1, 2)[0]
        text_x = (FRAME_WIDTH - text_size[0]) // 2
        text_y = (FRAME_HEIGHT + text_size[1]) // 2
        
        cv2.putText(frame, error_message, (text_x, text_y), font, 1, (0, 0, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            return (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                   frame_bytes + b'\r\n')
        return b''

# Flask routes
@app.route('/')
def index():
    """Ana sayfa - API bilgileri."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    return jsonify({
        "service": "Guard AI Stream Server",
        "version": "2.0.0",
        "description": "YOLOv11 Pose Estimation + DeepSORT Video Stream API",
        "cameras": list(server.cameras.keys()),
        "endpoints": {
            "camera_list": "/api/cameras",
            "camera_status": "/api/cameras/{camera_id}/status",
            "video_stream": "/video_feed/{camera_id}",
            "pose_stream": "/video_feed/{camera_id}/pose",
            "detection_stream": "/video_feed/{camera_id}/detection",
            "stats": "/api/stats"
        },
        "features": [
            "YOLOv11 Pose Estimation",
            "DeepSORT Multi-Object Tracking", 
            "Real-time Fall Detection",
            "Live Pose Visualization",
            "Multiple Camera Support",
            "Cross-platform Compatibility"
        ]
    })

@app.route('/api/cameras')
def get_cameras():
    """Kullanılabilir kameraları listele."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    cameras_info = []
    for camera_id, camera_info in server.cameras.items():
        camera = camera_info['camera']
        status = camera.get_camera_status()
        
        cameras_info.append({
            "id": camera_id,
            "name": camera_info['config']['name'],
            "index": camera_info['config']['index'],
            "backend": camera_info['config']['backend'],
            "backend_name": status.get('backend_name', 'Unknown'),
            "status": status['connection'],
            "is_running": status['is_running'],
            "fps": status['fps'],
            "active_streams": camera_info['active_streams'],
            "total_frames": camera_info['total_frames']
        })
    
    return jsonify({
        "cameras": cameras_info,
        "total_cameras": len(cameras_info),
        "ai_features": {
            "pose_estimation": server.fall_detector is not None,
            "fall_detection": server.fall_detector is not None,
            "tracking": server.fall_detector is not None
        }
    })

@app.route('/api/cameras/<camera_id>/status')
def get_camera_status(camera_id):
    """Belirli bir kamera durumunu getir."""
    server = app.config.get('stream_server')
    if not server or camera_id not in server.cameras:
        return jsonify({"error": "Camera not found"}), 404
    
    camera_info = server.cameras[camera_id]
    camera = camera_info['camera']
    status = camera.get_camera_status()
    
    return jsonify({
        "camera_id": camera_id,
        "config": camera_info['config'],
        "status": status,
        "stream_info": {
            "active_streams": camera_info['active_streams'],
            "total_frames": camera_info['total_frames'],
            "last_access": camera_info['last_access']
        }
    })

@app.route('/api/stats')
def get_server_stats():
    """Server istatistiklerini getir."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    uptime = time.time() - server.stream_stats['start_time']
    
    return jsonify({
        "server_stats": server.stream_stats,
        "uptime_seconds": uptime,
        "uptime_formatted": f"{int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}",
        "ai_status": {
            "fall_detector_loaded": server.fall_detector is not None,
            "pose_visualization": server.pose_visualization_enabled,
            "model_info": server.fall_detector.get_model_info() if server.fall_detector else None
        },
        "camera_summary": {
            "total_cameras": len(server.cameras),
            "active_cameras": sum(1 for c in server.cameras.values() if c['camera'].is_running),
            "total_streams": sum(c['active_streams'] for c in server.cameras.values())
        }
    })

@app.route('/video_feed/<camera_id>')
def video_feed_basic(camera_id):
    """Temel video stream (sadece kamera)."""
    server = app.config.get('stream_server')
    if not server:
        return "Stream server not initialized", 500
    
    return Response(server.generate_frames(camera_id, include_pose=False, include_detection=False),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/<camera_id>/pose')
def video_feed_pose(camera_id):
    """Pose visualization stream."""
    server = app.config.get('stream_server')
    if not server:
        return "Stream server not initialized", 500
    
    return Response(server.generate_frames(camera_id, include_pose=True, include_detection=False),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/<camera_id>/detection')
def video_feed_detection(camera_id):
    """Full AI stream (pose + detection)."""
    server = app.config.get('stream_server')
    if not server:
        return "Stream server not initialized", 500
    
    return Response(server.generate_frames(camera_id, include_pose=True, include_detection=True),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/cameras/<camera_id>/start', methods=['POST'])
def start_camera_endpoint(camera_id):
    """Kamerayı başlat."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    if camera_id not in server.cameras:
        return jsonify({"error": "Camera not found"}), 404
    
    success = server.start_camera(camera_id)
    return jsonify({
        "success": success,
        "message": f"Camera {camera_id} {'started' if success else 'failed to start'}"
    })

@app.route('/api/cameras/<camera_id>/stop', methods=['POST'])
def stop_camera_endpoint(camera_id):
    """Kamerayı durdur."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    if camera_id not in server.cameras:
        return jsonify({"error": "Camera not found"}), 404
    
    server.stop_camera(camera_id)
    return jsonify({
        "success": True,
        "message": f"Camera {camera_id} stopped"
    })

@app.route('/api/pose/toggle', methods=['POST'])
def toggle_pose_visualization():
    """Pose görselleştirmesini aç/kapat."""
    server = app.config.get('stream_server')
    if not server:
        return jsonify({"error": "Stream server not initialized"}), 500
    
    server.pose_visualization_enabled = not server.pose_visualization_enabled
    return jsonify({
        "pose_visualization_enabled": server.pose_visualization_enabled,
        "message": f"Pose visualization {'enabled' if server.pose_visualization_enabled else 'disabled'}"
    })

def create_app():
    """Flask app factory."""
    return app

def run_stream_server(host='0.0.0.0', port=5000, debug=False):
    """Stream server'ı çalıştır."""
    try:
        server = StreamServer()
        server.is_running = True
        
        app.config['stream_server'] = server
        
        logging.info(f"YOLOv11 Stream Server başlatılıyor: http://{host}:{port}")
        logging.info(f"Kullanılabilir kameralar: {len(server.cameras)}")
        
        if server.fall_detector:
            model_info = server.fall_detector.get_model_info()
            logging.info(f"AI Model: {model_info.get('model_name', 'Unknown')}")
            logging.info(f"Device: {model_info.get('device', 'Unknown')}")
        
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)
        
    except Exception as e:
        logging.error(f"Stream Server başlatılamadı: {str(e)}")
        raise
    finally:
        # Cleanup
        if 'stream_server' in app.config:
            server = app.config['stream_server']
            server.is_running = False
            for camera_info in server.cameras.values():
                try:
                    camera_info['camera'].stop()
                except:
                    pass

def run_api_server_in_thread(host='0.0.0.0', port=5000):
    """API sunucusunu thread olarak çalıştır."""
    def run_server():
        run_stream_server(host, port, debug=False)
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    logging.info(f"YOLOv11 Stream Server thread başlatıldı: http://{host}:{port}")
    return thread

if __name__ == "__main__":
    # Test/development çalıştırma
    logging.basicConfig(level=logging.INFO)
    run_stream_server(debug=True)
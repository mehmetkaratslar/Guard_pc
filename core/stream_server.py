# =======================================================================================
# 📄 Dosya Adı: stream_server.py (ENHANCED VERSION V3)
# 📁 Konum: guard_pc_app/core/stream_server.py
# 📌 Açıklama:
# Gelişmiş YOLOv11 Pose Estimation entegreli video stream server
# Flask-Limiter uyumluluk düzeltmeleri ve basitleştirilmiş yapı
# =======================================================================================

import logging
import cv2
import time
import json
import threading
from datetime import datetime, timedelta
from threading import Thread, Lock, Event
from collections import defaultdict, deque
from functools import wraps
import numpy as np

from flask import Flask, Response, jsonify, request, abort
from flask_cors import CORS

# Optional dependencies için try-except
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    logging.warning("flask-limiter bulunamadı, rate limiting devre dışı")

try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logging.warning("flask-socketio bulunamadı, WebSocket devre dışı")

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("PyJWT bulunamadı, authentication devre dışı")

try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logging.info("Redis cache bağlantısı başarılı")
except:
    redis_client = None
    REDIS_AVAILABLE = False
    logging.warning("Redis cache kullanılamıyor, memory cache kullanılacak")

from core.camera import Camera
from core.fall_detection import FallDetector
from config.settings import CAMERA_CONFIGS, FRAME_WIDTH, FRAME_HEIGHT

# Flask app konfigürasyonu
app = Flask(__name__)
app.config['SECRET_KEY'] = 'guard_ai_secret_key_2025'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# CORS konfigürasyonu
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/video_feed/*": {"origins": "*"},
    r"/ws/*": {"origins": "*"}
})

# SocketIO konfigürasyonu (eğer mevcut ise)
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading',
                       ping_timeout=60, ping_interval=25)
else:
    socketio = None

# Rate limiting (eğer mevcut ise)
if LIMITER_AVAILABLE:
    try:
        # Yeni flask-limiter versiyonu için
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )
    except TypeError:
        # Eski flask-limiter versiyonu için
        try:
            limiter = Limiter(
                app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"]
            )
        except:
            limiter = None
            logging.warning("Rate limiter başlatılamadı")
else:
    limiter = None

class StreamCache:
    """Basitleştirilmiş cache sistemi."""
    
    def __init__(self):
        self.memory_cache = {}
        self.cache_stats = defaultdict(int)
        self.lock = Lock()
    
    def get(self, key):
        """Cache'den veri al."""
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"stream:{key}")
                if data:
                    self.cache_stats['redis_hits'] += 1
                    return json.loads(data)
            except:
                pass
        
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if entry['expires'] > time.time():
                    self.cache_stats['memory_hits'] += 1
                    return entry['data']
                else:
                    del self.memory_cache[key]
        
        self.cache_stats['misses'] += 1
        return None
    
    def set(self, key, data, ttl=300):
        """Cache'e veri kaydet."""
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(f"stream:{key}", ttl, json.dumps(data))
                self.cache_stats['redis_sets'] += 1
            except:
                pass
        
        with self.lock:
            self.memory_cache[key] = {
                'data': data,
                'expires': time.time() + ttl
            }
            self.cache_stats['memory_sets'] += 1
    
    def clear(self):
        """Cache'i temizle."""
        if REDIS_AVAILABLE:
            try:
                for key in redis_client.scan_iter(match="stream:*"):
                    redis_client.delete(key)
            except:
                pass
        
        with self.lock:
            self.memory_cache.clear()

class StreamAnalytics:
    """Basitleştirilmiş stream analytics."""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.realtime_data = defaultdict(lambda: deque(maxlen=100))
        self.start_time = time.time()
        self.lock = Lock()
    
    def record_event(self, event_type, camera_id=None, **kwargs):
        """Event kaydet."""
        with self.lock:
            timestamp = time.time()
            
            if camera_id:
                self.metrics[camera_id][event_type] += 1
                self.realtime_data[f"{camera_id}_{event_type}"].append(timestamp)
            
            self.metrics['global'][event_type] += 1
            self.realtime_data[f"global_{event_type}"].append(timestamp)
    
    def get_metrics(self, camera_id=None):
        """Metrikleri al."""
        with self.lock:
            if camera_id:
                return dict(self.metrics[camera_id])
            return {
                'global': dict(self.metrics['global']),
                'cameras': {k: dict(v) for k, v in self.metrics.items() if k != 'global'},
                'uptime': time.time() - self.start_time
            }

class EnhancedStreamServer:
    """Gelişmiş video stream sunucusu."""
    
    def __init__(self):
        """Stream sunucusunu başlatır."""
        self.cameras = {}
        self.is_running = False
        self.fall_detector = None
        self.cache = StreamCache()
        self.analytics = StreamAnalytics()
        
        # Konfigürasyon
        self.config = {
            'pose_visualization': True,
            'detection_enabled': True,
            'stream_quality': 'medium',
            'max_concurrent_streams': 10,
            'frame_cache_ttl': 1,
            'auth_required': False
        }
        
        # Stream yönetimi
        self.active_streams = {}
        self.stream_locks = defaultdict(Lock)
        self.quality_profiles = {
            'low': {'width': 320, 'height': 240, 'fps': 15, 'quality': 60},
            'medium': {'width': 640, 'height': 480, 'fps': 25, 'quality': 75},
            'high': {'width': 1280, 'height': 720, 'fps': 30, 'quality': 85},
            'ultra': {'width': 1920, 'height': 1080, 'fps': 30, 'quality': 95}
        }
        
        # Model yönetimi
        self.available_models = {
            'yolo11n': {'path': 'yolo11n-pose.pt', 'speed': 'fastest', 'accuracy': 'low'},
            'yolo11s': {'path': 'yolo11s-pose.pt', 'speed': 'fast', 'accuracy': 'medium'},
            'yolo11m': {'path': 'yolo11m-pose.pt', 'speed': 'medium', 'accuracy': 'high'},
            'yolo11l': {'path': 'yolo11l-pose.pt', 'speed': 'slow', 'accuracy': 'highest'}
        }
        self.current_model = 'yolo11l'
        
        # Health monitoring
        self.health_status = {
            'overall': 'healthy',
            'cameras': {},
            'ai_model': 'unknown',
            'last_check': time.time()
        }
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Sistem bileşenlerini başlat."""
        try:
            # Kameraları başlat
            for config in CAMERA_CONFIGS:
                camera_id = f"camera_{config['index']}"
                logging.info(f"Stream Server: Kamera başlatılıyor - {config['name']}")
                
                camera = Camera(camera_index=config['index'], backend=config['backend'])
                self.cameras[camera_id] = {
                    'camera': camera,
                    'config': config,
                    'active_streams': 0,
                    'total_frames': 0,
                    'last_access': time.time(),
                    'status': 'initializing',
                    'errors': deque(maxlen=10),
                    'restart_count': 0
                }
                
                # Kamera durumunu güncelle
                try:
                    if hasattr(camera, '_validate_camera_with_fallback') and camera._validate_camera_with_fallback():
                        self.cameras[camera_id]['status'] = 'ready'
                        logging.info(f"Stream Server: Kamera hazır - {config['name']}")
                    else:
                        self.cameras[camera_id]['status'] = 'error'
                        logging.warning(f"Stream Server: Kamera hatası - {config['name']}")
                except Exception as e:
                    self.cameras[camera_id]['status'] = 'error'
                    logging.error(f"Stream Server: Kamera {camera_id} başlatma hatası: {e}")
            
            # AI modeli başlat
            self._load_ai_model()
            
            if not self.cameras:
                logging.error("Stream Server: Hiçbir kamera başlatılamadı!")
            else:
                logging.info(f"Stream Server: {len(self.cameras)} kamera başlatıldı")
                
        except Exception as e:
            logging.error(f"Stream Server başlatılırken hata: {str(e)}")
    
    def _load_ai_model(self):
        """AI modelini yükle."""
        try:
            self.fall_detector = FallDetector.get_instance()
            self.health_status['ai_model'] = 'loaded'
            logging.info("Stream Server: AI Model yüklendi")
        except Exception as e:
            logging.warning(f"AI Model yüklenirken hata: {str(e)}")
            self.fall_detector = None
            self.health_status['ai_model'] = 'error'
    
    def _generate_error_frame(self, message):
        """Hata frame'i oluştur."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Hata mesajını çiz
        font = cv2.FONT_HERSHEY_SIMPLEX
        lines = message.split('\n')
        y_start = 200
        
        for i, line in enumerate(lines):
            y_pos = y_start + i * 40
            cv2.putText(frame, line, (50, y_pos), font, 0.8, (0, 0, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            return (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                   frame_bytes + b'\r\n')
        return b''
    
    def _add_stream_overlay(self, frame, camera_id, fps, pose_enabled, detection_enabled, quality):
        """Stream overlay ekle."""
        h, w = frame.shape[:2]
        
        # Header background
        cv2.rectangle(frame, (0, 0), (w, 35), (0, 0, 0), -1)
        
        # Camera info
        camera_name = camera_id.replace('_', ' ').title()
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, camera_name, (10, 25), font, 0.7, (255, 255, 255), 2)
        
        # AI status badges
        x_offset = 200
        if pose_enabled:
            cv2.rectangle(frame, (x_offset, 5), (x_offset + 60, 30), (0, 255, 255), -1)
            cv2.putText(frame, "POSE", (x_offset + 10, 22), font, 0.5, (0, 0, 0), 1)
            x_offset += 70
        
        if detection_enabled:
            cv2.rectangle(frame, (x_offset, 5), (x_offset + 80, 30), (0, 255, 0), -1)
            cv2.putText(frame, "DETECT", (x_offset + 10, 22), font, 0.5, (0, 0, 0), 1)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamp_size = cv2.getTextSize(timestamp, font, 0.5, 1)[0]
        cv2.putText(frame, timestamp, (w - timestamp_size[0] - 10, h - 10), 
                   font, 0.5, (255, 255, 255), 1)
    
    def generate_frames(self, camera_id, quality='medium', include_pose=True, 
                       include_detection=True, client_id=None):
        """
        Video akışı üretir.
        
        Args:
            camera_id (str): Kamera ID'si
            quality (str): Stream kalitesi
            include_pose (bool): Pose visualization dahil et
            include_detection (bool): Fall detection dahil et
            client_id (str): İstemci kimliği
        """
        if camera_id not in self.cameras:
            logging.error(f"Stream Server: Geçersiz kamera ID: {camera_id}")
            yield self._generate_error_frame(f"Kamera {camera_id} bulunamadı")
            return
        
        camera_info = self.cameras[camera_id]
        camera = camera_info['camera']
        
        # Kalite profili
        profile = self.quality_profiles.get(quality, self.quality_profiles['medium'])
        
        # Stream tracking
        camera_info['active_streams'] += 1
        self.analytics.record_event('stream_start', camera_id)
        
        # Kamerayı başlat
        if not camera.is_running:
            try:
                if not camera.start():
                    yield self._generate_error_frame(f"Kamera {camera_id} başlatılamadı")
                    return
            except Exception as e:
                yield self._generate_error_frame(f"Kamera başlatma hatası: {str(e)}")
                return
        
        logging.info(f"Stream başlatıldı: {camera_id} (Quality: {quality}, Client: {client_id})")
        
        try:
            frame_count = 0
            last_fps_time = time.time()
            fps = 0
            
            target_fps = profile['fps']
            frame_interval = 1.0 / target_fps
            
            while self.is_running:
                loop_start = time.time()
                
                try:
                    # Frame al
                    frame = camera.get_frame()
                    if frame is None:
                        yield self._generate_error_frame("Kamera bağlantısı yok")
                        time.sleep(0.1)
                        continue
                    
                    # AI işleme
                    processed_frame = frame.copy()
                    
                    if self.fall_detector and (include_pose or include_detection):
                        try:
                            # YOLOv11 işleme
                            annotated_frame, tracks = self.fall_detector.get_detection_visualization(frame)
                            
                            if include_pose:
                                processed_frame = annotated_frame
                            
                            # Fall detection
                            if include_detection:
                                is_fall, confidence, track_id = self.fall_detector.detect_fall(frame, tracks)
                                
                                if is_fall and confidence > 0.6:
                                    self._handle_fall_detection(camera_id, confidence, track_id)
                                    self._add_fall_alert_overlay(processed_frame, confidence, track_id)
                        
                        except Exception as e:
                            logging.error(f"AI işleme hatası: {str(e)}")
                            processed_frame = frame
                    
                    # Kalite ayarlarını uygula
                    if quality != 'ultra':
                        processed_frame = cv2.resize(processed_frame, 
                                                    (profile['width'], profile['height']), 
                                                    interpolation=cv2.INTER_LINEAR)
                    
                    # Stream overlay ekle
                    self._add_stream_overlay(processed_frame, camera_id, fps, 
                                           include_pose, include_detection, quality)
                    
                    # Encode
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, profile['quality']]
                    ret, buffer = cv2.imencode('.jpg', processed_frame, encode_params)
                    
                    if not ret:
                        yield self._generate_error_frame("Frame encode hatası")
                        continue
                    
                    frame_bytes = buffer.tobytes()
                    
                    # MJPEG stream formatı
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                           frame_bytes + b'\r\n')
                    
                    # İstatistikler
                    frame_count += 1
                    camera_info['total_frames'] += 1
                    camera_info['last_access'] = time.time()
                    self.analytics.record_event('frame_served', camera_id)
                    
                    # FPS hesaplama
                    if time.time() - last_fps_time >= 1.0:
                        fps = frame_count / (time.time() - last_fps_time)
                        frame_count = 0
                        last_fps_time = time.time()
                    
                    # Frame rate kontrolü
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, frame_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                except Exception as e:
                    logging.error(f"Frame işleme hatası: {str(e)}")
                    yield self._generate_error_frame("Frame işleme hatası")
                    time.sleep(0.1)
                    
        except GeneratorExit:
            pass
        except Exception as e:
            logging.error(f"Stream hatası: {str(e)}")
        finally:
            # Cleanup
            camera_info['active_streams'] -= 1
            self.analytics.record_event('stream_end', camera_id)
            logging.info(f"Stream sonlandı: {camera_id}")
    
    def _handle_fall_detection(self, camera_id, confidence, track_id):
        """Düşme algılama işleme."""
        event_data = {
            'camera_id': camera_id,
            'confidence': confidence,
            'track_id': track_id,
            'timestamp': time.time()
        }
        
        # Analytics kaydet
        self.analytics.record_event('fall_detected', camera_id)
        
        # WebSocket bildirimi (eğer mevcut ise)
        if socketio:
            socketio.emit('fall_alert', event_data, namespace='/alerts')
        
        logging.warning(f"DÜŞME ALGILANDI: {camera_id}, ID: {track_id}, Güven: {confidence:.3f}")
    
    def _add_fall_alert_overlay(self, frame, confidence, track_id):
        """Düşme uyarısı overlay ekle."""
        h, w = frame.shape[:2]
        
        # Kırmızı uyarı arka plan
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Uyarı metni
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "FALL DETECTED!", (w//2 - 150, 30), 
                   font, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, f"ID: {track_id} | Confidence: {confidence:.3f}", 
                   (w//2 - 120, 60), font, 0.7, (255, 255, 255), 2)


# Global server instance
stream_server = None

def get_stream_server():
    """Stream server instance'ını al."""
    global stream_server
    if stream_server is None:
        stream_server = EnhancedStreamServer()
    return stream_server

# Authentication decorator
def require_auth(f):
    """Authentication gerekli endpoint'ler için decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not JWT_AVAILABLE:
            return f(*args, **kwargs)
        
        server = get_stream_server()
        if not server.config['auth_required']:
            return f(*args, **kwargs)
        
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            return f(*args, **kwargs)
            
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated

# Rate limiting decorator
def rate_limit(limit_string):
    """Rate limiting decorator."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_string)(f)
        return f
    return decorator

# ================================ API ROUTES ================================

@app.route('/')
def index():
    """Ana sayfa."""
    server = get_stream_server()
    
    return jsonify({
        "service": "Guard AI Stream Server",
        "version": "1.0.0",
        "description": "YOLOv11 Pose Estimation Video Stream API",
        "author": "mehmetkaratslar",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "YOLOv11 Pose Estimation",
            "Real-time Fall Detection",
            "Multi-Quality Streaming",
            "Camera Management"
        ],
        "cameras": {
            "total": len(server.cameras),
            "available": list(server.cameras.keys())
        },
        "endpoints": {
            "cameras": "/api/cameras",
            "video_basic": "/video_feed/{camera_id}",
            "video_pose": "/video_feed/{camera_id}/pose",
            "video_detection": "/video_feed/{camera_id}/detection",
            "health": "/api/health"
        },
        "quality_profiles": server.quality_profiles
    })

@app.route('/api/cameras')
def get_cameras():
    """Kamera listesi."""
    server = get_stream_server()
    
    cameras = []
    for camera_id, camera_info in server.cameras.items():
        cameras.append({
            "id": camera_id,
            "name": camera_info['config']['name'],
            "index": camera_info['config']['index'],
            "status": camera_info['status'],
            "active_streams": camera_info['active_streams']
        })
    
    return jsonify({"cameras": cameras})

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    """Basit video feed."""
    server = get_stream_server()
    return Response(
        server.generate_frames(camera_id, quality='medium', 
                             include_pose=False, include_detection=False),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/video_feed/<camera_id>/pose')
def video_feed_pose(camera_id):
    """Pose video feed."""
    server = get_stream_server()
    return Response(
        server.generate_frames(camera_id, quality='medium', 
                             include_pose=True, include_detection=False),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/video_feed/<camera_id>/detection')
def video_feed_detection(camera_id):
    """Detection video feed."""
    server = get_stream_server()
    return Response(
        server.generate_frames(camera_id, quality='medium', 
                             include_pose=True, include_detection=True),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/health')
def health_check():
    """Sistem sağlık kontrolü."""
    server = get_stream_server()
    
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "cameras": {},
        "ai_model": server.health_status['ai_model'],
        "total_cameras": len(server.cameras),
        "active_cameras": 0
    }
    
    # Kamera durumları
    for camera_id, camera_info in server.cameras.items():
        camera = camera_info['camera']
        is_running = hasattr(camera, 'is_running') and camera.is_running
        
        health_data['cameras'][camera_id] = {
            'status': camera_info['status'],
            'is_running': is_running,
            'active_streams': camera_info['active_streams']
        }
        
        if is_running:
            health_data['active_cameras'] += 1
    
    return jsonify(health_data)

@app.route('/api/stats')
def get_stats():
    """İstatistikler."""
    server = get_stream_server()
    
    metrics = server.analytics.get_metrics()
    
    return jsonify({
        "metrics": metrics,
        "cache_stats": server.cache.cache_stats,
        "active_streams": {
            camera_id: info['active_streams'] 
            for camera_id, info in server.cameras.items()
        }
    })

# ================================ WEBSOCKET HANDLERS ================================

if SOCKETIO_AVAILABLE:
    @socketio.on('connect', namespace='/alerts')
    def handle_alerts_connect():
        """Alerts WebSocket bağlantısı."""
        client_id = request.sid
        join_room('alerts', namespace='/alerts')
        
        emit('connected', {
            'client_id': client_id,
            'timestamp': time.time(),
            'message': 'Connected to fall alerts'
        })
        
        logging.info(f"Alerts client connected: {client_id}")

# ================================ ERROR HANDLERS ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ================================ MAIN FUNCTIONS ================================

def run_stream_server(host='0.0.0.0', port=5000, debug=False):
    """Stream server'ı çalıştır."""
    try:
        global stream_server
        stream_server = EnhancedStreamServer()
        stream_server.is_running = True
        
        logging.info("=" * 60)
        logging.info("🚀 Guard AI Stream Server başlatılıyor...")
        logging.info(f"📡 Server URL: http://{host}:{port}")
        logging.info(f"📹 Kameralar: {len(stream_server.cameras)}")
        logging.info(f"🤖 AI Model: {'Yüklü' if stream_server.fall_detector else 'Yüklenmedi'}")
        logging.info("=" * 60)
        
        # Server'ı çalıştır
        if SOCKETIO_AVAILABLE:
            socketio.run(app, host=host, port=port, debug=debug, 
                        allow_unsafe_werkzeug=True, use_reloader=False)
        else:
            app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except Exception as e:
        logging.error(f"Stream Server başlatılamadı: {str(e)}")
        raise
    finally:
        # Cleanup
        if stream_server:
            stream_server.is_running = False
            for camera_info in stream_server.cameras.values():
                try:
                    if hasattr(camera_info['camera'], 'stop'):
                        camera_info['camera'].stop()
                except:
                    pass

def run_api_server_in_thread(host='0.0.0.0', port=5000):
    """API sunucusunu thread olarak çalıştır."""
    def run_server():
        run_stream_server(host, port, debug=False)
    
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    
    logging.info(f"🧵 Stream Server thread başlatıldı: http://{host}:{port}")
    return thread

if __name__ == "__main__":
    # Development/test çalıştırma
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    run_stream_server(debug=True)
    
    
# =======================================================================================

# MOBIL API ENDPOİNTLERİ
@app.route('/api/mobile/cameras')
def mobile_get_cameras():
    """Mobil için kamera listesi."""
    server = get_stream_server()
    
    cameras = []
    for camera_id, camera_info in server.cameras.items():
        # Kamera durumunu kontrol et
        is_available = camera_info['status'] == 'ready'
        
        cameras.append({
            "id": camera_id,
            "name": camera_info['config']['name'],
            "index": camera_info['config']['index'],
            "status": camera_info['status'],
            "available": is_available,
            "stream_url": f"/mobile/stream/{camera_id}",
            "pose_stream_url": f"/mobile/stream/{camera_id}/pose",
            "detection_stream_url": f"/mobile/stream/{camera_id}/detection"
        })
    
    return jsonify({
        "success": True,
        "cameras": cameras,
        "server_info": {
            "name": "Guard AI Stream Server",
            "version": "1.0.0",
            "total_cameras": len(cameras),
            "available_cameras": len([c for c in cameras if c['available']])
        }
    })

@app.route('/api/mobile/server/info')
def mobile_server_info():
    """Mobil için server bilgileri."""
    server = get_stream_server()
    
    return jsonify({
        "success": True,
        "server": {
            "name": "Guard AI Mobile Stream",
            "version": "1.0.0",
            "status": "online",
            "ai_model_loaded": server.health_status['ai_model'] == 'loaded',
            "features": [
                "Real-time Video Streaming",
                "YOLOv11 Pose Detection",
                "Fall Detection Alerts",
                "Multi-Camera Support"
            ]
        },
        "endpoints": {
            "cameras": "/api/mobile/cameras",
            "stream": "/mobile/stream/{camera_id}",
            "pose_stream": "/mobile/stream/{camera_id}/pose",
            "detection_stream": "/mobile/stream/{camera_id}/detection",
            "health": "/api/mobile/health"
        }
    })

@app.route('/api/mobile/health')
def mobile_health_check():
    """Mobil için sağlık kontrolü."""
    server = get_stream_server()
    
    total_cameras = len(server.cameras)
    active_cameras = 0
    ready_cameras = 0
    
    camera_status = {}
    for camera_id, camera_info in server.cameras.items():
        camera = camera_info['camera']
        is_running = hasattr(camera, 'is_running') and camera.is_running
        is_ready = camera_info['status'] == 'ready'
        
        if is_running:
            active_cameras += 1
        if is_ready:
            ready_cameras += 1
        
        camera_status[camera_id] = {
            'name': camera_info['config']['name'],
            'status': camera_info['status'],
            'running': is_running,
            'ready': is_ready,
            'active_streams': camera_info['active_streams']
        }
    
    overall_status = "healthy"
    if active_cameras == 0:
        overall_status = "no_cameras"
    elif active_cameras < ready_cameras:
        overall_status = "degraded"
    
    return jsonify({
        "success": True,
        "status": overall_status,
        "timestamp": time.time(),
        "cameras": {
            "total": total_cameras,
            "ready": ready_cameras,
            "active": active_cameras,
            "details": camera_status
        },
        "ai_model": {
            "status": server.health_status['ai_model'],
            "loaded": server.health_status['ai_model'] == 'loaded'
        }
    })

# MOBİL VİDEO STREAM ENDPOİNTLERİ
@app.route('/mobile/stream/<camera_id>')
def mobile_video_feed(camera_id):
    """Mobil için temel video stream."""
    server = get_stream_server()
    
    # CORS headers ekle
    def generate_with_cors():
        for chunk in server.generate_frames(camera_id, quality='medium', 
                                           include_pose=False, include_detection=False):
            yield chunk
    
    response = Response(generate_with_cors(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/mobile/stream/<camera_id>/pose')
def mobile_video_feed_pose(camera_id):
    """Mobil için pose detection stream."""
    server = get_stream_server()
    
    def generate_with_cors():
        for chunk in server.generate_frames(camera_id, quality='medium', 
                                           include_pose=True, include_detection=False):
            yield chunk
    
    response = Response(generate_with_cors(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/mobile/stream/<camera_id>/detection')
def mobile_video_feed_detection(camera_id):
    """Mobil için full detection stream."""
    server = get_stream_server()
    
    def generate_with_cors():
        for chunk in server.generate_frames(camera_id, quality='high', 
                                           include_pose=True, include_detection=True):
            yield chunk
    
    response = Response(generate_with_cors(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# MOBİL FALL ALERT ENDPOİNTLERİ
@app.route('/api/mobile/alerts/recent')
def mobile_recent_alerts():
    """Mobil için son uyarılar."""
    server = get_stream_server()
    
    # Son 24 saatteki uyarılar (örnek)
    alerts = []
    
    return jsonify({
        "success": True,
        "alerts": alerts,
        "count": len(alerts),
        "period": "24h"
    })

@app.route('/api/mobile/quality/<camera_id>')
def mobile_stream_quality_options(camera_id):
    """Mobil için kalite seçenekleri."""
    server = get_stream_server()
    
    if camera_id not in server.cameras:
        return jsonify({"success": False, "error": "Camera not found"}), 404
    
    return jsonify({
        "success": True,
        "camera_id": camera_id,
        "quality_options": {
            "low": {
                "name": "Düşük Kalite",
                "resolution": "320x240",
                "fps": 15,
                "url": f"/mobile/stream/{camera_id}?quality=low"
            },
            "medium": {
                "name": "Orta Kalite",
                "resolution": "640x480", 
                "fps": 25,
                "url": f"/mobile/stream/{camera_id}?quality=medium"
            },
            "high": {
                "name": "Yüksek Kalite",
                "resolution": "1280x720",
                "fps": 30,
                "url": f"/mobile/stream/{camera_id}?quality=high"
            }
        }
    })

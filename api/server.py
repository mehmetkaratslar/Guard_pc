# 📄 Dosya: api/server.py
# 📁 Konum: pc/api/
# 📌 Açıklama: Guard PC uygulaması için HTTP tabanlı API sunucusu.
# 🔗 Bağlantılı: core/camera.py, mobil istemci canlı görüntü, bildirim sistemi, olay gönderme
# 📡 Canlı kamera stream /api/stream endpoint'i üzerinden MJPEG olarak erişilebilir.

import threading
import time
import logging
import json
import socket
import cv2  # Canlı yayın için OpenCV kullanıyoruz
from http.server import HTTPServer, BaseHTTPRequestHandler


class GuardAPIHandler(BaseHTTPRequestHandler):
    """
    Guard API için HTTP isteklerini yöneten sınıf
    """

    def _set_headers(self, content_type="application/json"):
        """Genel header ayarları"""
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')  # CORS desteği
        self.end_headers()

    def do_GET(self):
        """GET istekleri"""
        if self.path == '/api/stream':
            self._handle_stream()
        elif self.path == '/api/status':
            self._set_headers()
            response = {
                'status': 'active',
                'version': '1.0.0',
                'timestamp': time.time()
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/api/info':
            self._set_headers()
            response = {
                'name': 'Guard API',
                'description': 'Guard düşme algılama sistemi API sunucusu',
                'endpoints': ['/api/status', '/api/info', '/api/stream']
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """POST istekleri"""
        if self.path == '/api/event':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            # TODO: Firestore'a veri gönderilebilir

            self._set_headers()
            response = {
                'success': True,
                'message': 'Event received'
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_stream(self):
        """Kamera görüntüsünü MJPEG olarak yayınlar"""
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                _, jpeg = cv2.imencode('.jpg', frame)
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(jpeg.tobytes())
                self.wfile.write(b"\r\n")
                time.sleep(0.03)  # Yaklaşık 30 FPS
        except BrokenPipeError:
            pass  # Tarayıcı bağlantıyı kesti
        finally:
            cap.release()

    def log_message(self, format, *args):
        """Sunucu loglarını bastırmak için override edildi"""
        logging.info(f"API Server: {self.address_string()} - {format % args}")


def run_api_server(port=5000):
    """
    API sunucusunu başlatır
    """
    try:
        server_address = ('', port)
        httpd = HTTPServer(server_address, GuardAPIHandler)
        logging.info(f"API sunucusu başlatıldı: http://localhost:{port}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"API sunucusu başlatılırken hata oluştu: {str(e)}")


def run_api_server_in_thread(port=5000):
    """
    API sunucusunu ayrı bir thread içinde çalıştırır
    """
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    api_thread = threading.Thread(
        target=run_api_server,
        args=(port,),
        daemon=True
    )
    api_thread.start()
    logging.info(f"API sunucusu thread olarak başlatıldı: http://{local_ip}:{port}")
    return api_thread

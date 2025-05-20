"""
api/utils.py modülü
Guard uygulaması API yardımcı fonksiyonlarını içerir
"""

import os
import socket
import logging

def get_api_url(default_port=5000):
    """
    API sunucusu için URL oluşturur.
    
    Args:
        default_port (int): API sunucusunun çalıştığı port (varsayılan: 5000)
    
    Returns:
        str: API URL'si (örn: "http://127.0.0.1:5000")
    """
    try:
        # Yerel IP adresini al
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Çevresel değişkenden port bilgisini al veya varsayılanı kullan
        port = os.environ.get('GUARD_API_PORT', default_port)
        
        # API URL'sini oluştur
        api_url = f"http://{local_ip}:{port}"
        logging.info(f"API URL oluşturuldu: {api_url}")
        
        return api_url
    except Exception as e:
        # Hata durumunda localhost kullan
        logging.warning(f"API URL oluşturulurken hata: {str(e)}. Localhost kullanılıyor.")
        return f"http://127.0.0.1:{default_port}"

def get_local_ip():
    """
    Makinenin yerel IP adresini döndürür
    
    Returns:
        str: Yerel IP adresi
    """
    try:
        # Yerel IP'yi almak için bir socket bağlantısı
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Google'ın DNS sunucusuna bağlanmaya çalış (gerçekten bağlanmaz)
        s.connect(("8.8.8.8", 80))
        # Bağlantı için kullanılan yerel IP'yi al
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        # Hata durumunda localhost döndür
        return "127.0.0.1"
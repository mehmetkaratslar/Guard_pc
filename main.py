# =======================================================================================
# Dosya Adı: main.py
# Konumu: guard_pc_app/main.py
# Açıklama: Guard düşme algılama sisteminin ana giriş noktası ve başlatıcısı
# 
# Bağlantılı Dosyalar:
# - splash.py         : Uygulama açılış ekranını yönetir
# - ui/app.py         : Ana uygulama arayüz sınıfını içerir
# - ui/login.py       : Kullanıcı giriş ekranını yönetir
# - ui/dashboard.py   : Ana kontrol panelini yönetir
# - ui/settings.py    : Ayarlar ekranını yönetir
# - ui/history.py     : Geçmiş olaylar ekranını yönetir
# - utils/logger.py   : Loglama sistemini yapılandırır
# - utils/auth.py     : Firebase kimlik doğrulama işlemlerini yönetir
# - config/firebase_config.py : Firebase yapılandırma ayarlarını içerir
# - core/stream_server.py     : MJPEG video akışı sağlayan Flask sunucusu
# =======================================================================================

import tkinter as tk               # GUI bileşenleri için temel kütüphane
import sys                         # Sistem işlemleri (çıkış, argüman işleme)
import os                          # Dosya/dizin işlemleri
import logging                     # Loglama işlemleri
import traceback                   # Hata izleme için
import threading                   # Thread işlemleri için

# Özel modüller
from utils.logger import setup_logger   # Loglama yapılandırma
from splash import SplashScreen          # Açılış ekranı
from ui.app import GuardApp              # Ana uygulama sınıfı
from core.stream_server import app as flask_app  # Flask sunucusu

def main():
    """
    Guard PC uygulamasını başlatır ve ana yaşam döngüsünü yönetir.
    
    İşlemler:
    1. Loglama sistemini başlatır
    2. Flask sunucusunu thread olarak başlatır
    3. Tkinter ana penceresini oluşturur
    4. Açılış ekranını gösterir
    5. Ana uygulamayı başlatır
    6. Yaşam döngüsünü başlatır
    7. Temiz kapatma işlemlerini gerçekleştirir
    """
    # Loglama sistemini başlat
    setup_logger()
    logging.info("[BASLA] Guard PC Uygulaması başlatılıyor...")

    try:
        # ===== FLASK SUNUCUSUNU BAŞLAT =====
        logging.info("[BASLA] Flask sunucusu thread olarak başlatılıyor...")
        flask_thread = threading.Thread(
            target=lambda: flask_app.run(host='0.0.0.0', port=5000, threaded=True)
        )
        flask_thread.daemon = True
        flask_thread.start()
        logging.info("[TAMAM] Flask sunucusu thread olarak başlatıldı: http://192.168.56.141:5000")

        # ===== ANA PENCERE OLUŞTURMA =====
        root = tk.Tk()
        root.title("Guard - Düşme Algılama Sistemi")
        root.configure(bg="#f5f5f5")  # Varsayılan açık gri arka plan
        
        # Tam ekran moduna geçiş
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Pencere boyutunu önce ekran boyutuna ayarla
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Minimum pencere boyutu (daha küçük ekranlar için)
        root.minsize(1000, 700)
        
        # Tam ekran modu etkinleştir
        # Windows'ta "zoomed" durumu kullan
        root.state('zoomed')
        
        # ===== UYGULAMA İKONU YÜKLEME =====
        try:
            # İkon dosyası yolunu oluştur
            icon_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "resources",
                "icons",
                "logo.png"
            )
            
            # İkon dosyasının varlığını kontrol et
            if os.path.exists(icon_path):
                # İkonu yükle ve pencereye uygula
                icon = tk.PhotoImage(file=icon_path)
                root.iconphoto(True, icon)
                logging.info("[TAMAM] Uygulama ikonu başarıyla yüklendi")
            else:
                # İkon dosyası bulunamadı
                logging.warning("[UYARI] Uygulama ikonu bulunamadı: " + icon_path)
        except Exception as e:
            # İkon yükleme hatası
            logging.warning("[UYARI] Uygulama ikonu yüklenirken hata: " + str(e))
        
        # ===== AÇILIŞ EKRANI BAŞLATMA =====
        logging.info("[BASLA] Açılış ekranı başlatılıyor...")
        # Şık açılış ekranını göster (duration = gösterim süresi saniye)
        splash = SplashScreen(root, duration=4.0)
        
        # ===== ANA UYGULAMA BAŞLATMA =====
        logging.info("[BASLA] Ana uygulama başlatılıyor...")
        # GuardApp sınıfından ana uygulama nesnesini oluştur
        app = GuardApp(root)
        
        # ===== TKINTER ANA DÖNGÜSÜ =====
        logging.info("[BASLA] Tkinter ana döngüsü başlatılıyor...")
        # Uygulama döngüsünü başlat (UI olaylarını işlemeye başla)
        root.mainloop()
        
    except Exception as e:
        # ===== KRİTİK HATA YÖNETİMİ =====
        # Beklenmeyen bir hata oluştuğunda tüm hata izini ve mesajını logla
        logging.error("[HATA!] KRITIK HATA: Uygulama çalışırken hata oluştu: " + str(e), exc_info=True)
        
        # Hata izini konsola yazdır (geliştiriciler için)
        print("\n\n" + "="*80)
        print("[HATA!] KRITIK HATA OLUSTU:")
        traceback.print_exc()
        print("="*80 + "\n")
        
        # Kullanıcıya hata mesajı göster
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Kritik Hata",
                f"Uygulama çalışırken beklenmeyen bir hata oluştu:\n\n{str(e)}\n\nUygulama kapatılacak."
            )
        except:
            pass
        
        # Uygulamadan çık
        sys.exit(1)
        
    finally:
        # ===== KAPATMA İŞLEMLERİ =====
        # Her durumda çalışacak temizlik işlemleri
        try:
            # Tkinter kaynaklarını temizle
            root.destroy()
            logging.info("[TAMAM] Tkinter kaynakları temizlendi")
        except:
            pass
        
        logging.info("[BITIS] Uygulama kapatılıyor...")

# Ana program başlangıç noktası
if __name__ == "__main__":
    # ===== ÇALIŞMA DİZİNİ AYARI =====
    # Proje kök dizinine git (göreceli dosya yolu sorunlarını önler)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    logging.info("[BILGI] Çalışma dizini: " + os.getcwd())
    
    # ===== BAĞIMLILIK KONTROLÜ =====
    # Kritik bağımlılıkların yüklü olup olmadığını kontrol et
    required_modules = [
        "PIL",      # Pillow - görüntü işleme
        "cv2",      # OpenCV - görüntü işleme ve bilgisayarlı görü
        "numpy",    # NumPy - sayısal hesaplamalar
        "pyrebase", # Pyrebase - Firebase bağlantısı
        "requests", # Requests - HTTP istekleri
        "firebase_admin", # Firebase Admin SDK
        "torch",    # PyTorch - derin öğrenme modeli
        "flask",    # Flask - web sunucusu
        "flask_cors"  # Flask-CORS - CORS desteği
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            # Modülü içe aktarmayı dene
            __import__(module)
        except ImportError as e:
            # Modül bulunamadıysa hatayı logla ve listele
            logging.error("[HATA!] Bağımlılık eksik: " + module + ". Hata: " + str(e))
            missing_modules.append(module)
    
    # Eksik modüller varsa kullanıcıyı bilgilendir ve çık
    if missing_modules:
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Eksik Bağımlılıklar",
                f"Aşağıdaki bağımlılıklar eksik:\n\n" + 
                "\n".join(missing_modules) + 
                "\n\nLütfen aşağıdaki komutu çalıştırın:\n" +
                f"pip install {' '.join(missing_modules)}"
            )
        except:
            print(f"[HATA!] Eksik bağımlılıklar: {', '.join(missing_modules)}")
            print(f"Lütfen şu komutu çalıştırın: pip install {' '.join(missing_modules)}")
        
        sys.exit(1)
    
    # ===== ANA UYGULAMAYI BAŞLAT =====
    # Tüm kontroller tamamlandı, uygulamayı başlat
    main()
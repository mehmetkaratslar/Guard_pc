# =======================================================================================
# 📄 Dosya Adı: main.py (ENHANCED VERSION)
# 📁 Konum: guard_pc_app/main.py
# 📌 Açıklama:
# Guard AI - YOLOv11 Pose Estimation düşme algılama sisteminin ana giriş noktası.
# Enhanced stream server, gelişmiş kamera yönetimi ve AI entegrasyonu.
#
# 🔗 Bağlantılı Dosyalar:
# - splash.py         : Uygulama açılış ekranını yönetir
# - ui/app.py         : Ana uygulama arayüz sınıfını içerir (Enhanced)
# - ui/login.py       : Kullanıcı giriş ekranını yönetir
# - ui/dashboard.py   : Ana kontrol panelini yönetir (Enhanced - YOLOv11 UI)
# - ui/settings.py    : Ayarlar ekranını yönetir
# - ui/history.py     : Geçmiş olaylar ekranını yönetir
# - utils/logger.py   : Loglama sistemini yapılandırır
# - utils/auth.py     : Firebase kimlik doğrulama işlemlerini yönetir
# - config/firebase_config.py : Firebase yapılandırma ayarlarını içerir
# - core/stream_server.py     : YOLOv11 Pose entegreli video stream server (Enhanced)
# - core/camera.py            : Gelişmiş kamera yönetimi (Enhanced)
# - core/fall_detection.py   : YOLOv11 Pose + DeepSORT düşme algılama (Enhanced)
# - config/settings.py       : Gelişmiş YOLOv11 ayarları (Enhanced)
# =======================================================================================

import tkinter as tk               # GUI bileşenleri için temel kütüphane
import sys                         # Sistem işlemleri (çıkış, argüman işleme)
import os                          # Dosya/dizin işlemleri
import logging                     # Loglama işlemleri
import traceback                   # Hata izleme için
import threading                   # Thread işlemleri için
import time                        # Zaman işlemleri
import platform                   # Platform bilgisi

# Özel modüller - Enhanced versiyonlar
from utils.logger import setup_logger       # Loglama yapılandırma
from splash import SplashScreen              # Açılış ekranı
from ui.app import GuardApp                  # Ana uygulama sınıfı (Enhanced)
from core.stream_server import run_api_server_in_thread  # Enhanced Stream Server
from config.settings import APP_NAME, APP_VERSION, MODEL_PATH, validate_config  # Enhanced settings

def check_system_requirements():
    """Sistem gereksinimlerini kontrol eder."""
    logging.info("🔍 Sistem gereksinimleri kontrol ediliyor...")
    
    # Platform bilgisi
    system_info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.architecture()[0],
        'processor': platform.processor(),
        'python_version': sys.version
    }
    
    logging.info(f"💻 Platform: {system_info['platform']} {system_info['architecture']}")
    logging.info(f"🐍 Python: {sys.version.split()[0]}")
    
    # Model dosyası kontrolü
    if not os.path.exists(MODEL_PATH):
        logging.error(f"❌ YOLOv11 model dosyası bulunamadı: {MODEL_PATH}")
        logging.info("📥 Model dosyasını indirmek için:")
        logging.info("   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11l-pose.pt")
        return False
    else:
        model_size = os.path.getsize(MODEL_PATH) / (1024 * 1024)  # MB
        logging.info(f"✅ YOLOv11 model dosyası bulundu: {model_size:.1f} MB")
    
    # Konfigürasyon doğrulama
    config_errors = validate_config()
    if config_errors:
        logging.error("❌ Konfigürasyon hataları:")
        for error in config_errors:
            logging.error(f"   - {error}")
        return False
    else:
        logging.info("✅ Konfigürasyon doğrulandı")
    
    return True

def check_gpu_availability():
    """GPU kullanılabilirliğini kontrol eder."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            logging.info(f"🚀 GPU algılama: {gpu_count} GPU bulundu")
            logging.info(f"   Birincil GPU: {gpu_name}")
            return True
        else:
            logging.info("💻 GPU bulunamadı, CPU kullanılacak")
            return False
    except Exception as e:
        logging.warning(f"⚠️ GPU kontrol hatası: {str(e)}")
        return False

def main():
    """
    Guard AI PC uygulamasını başlatır ve ana yaşam döngüsünü yönetir.
    
    Enhanced İşlemler:
    1. Sistem gereksinimlerini kontrol eder
    2. YOLOv11 model dosyasını doğrular
    3. Enhanced stream server'ı başlatır
    4. GPU kullanılabilirliğini kontrol eder
    5. Tkinter ana penceresini oluşturur
    6. Açılış ekranını gösterir
    7. Enhanced GuardApp'i başlatır
    8. Yaşam döngüsünü başlatır
    9. Temiz kapatma işlemlerini gerçekleştirir
    """
    # Loglama sistemini başlat
    setup_logger()
    logging.info("=" * 80)
    logging.info(f"🚀 {APP_NAME} v{APP_VERSION} başlatılıyor...")
    logging.info("=" * 80)

    try:
        # ===== SİSTEM GEREKSİNİMLERİ KONTROLÜ =====
        if not check_system_requirements():
            logging.error("❌ Sistem gereksinimleri karşılanmıyor!")
            return False
        
        # ===== GPU KULLANILABILIRLIK KONTROLÜ =====
        gpu_available = check_gpu_availability()
        
        # ===== ENHANCED STREAM SERVER'I BAŞLAT =====
        logging.info("🌐 Enhanced YOLOv11 Stream Server başlatılıyor...")
        
        try:
            # Enhanced stream server'ı thread olarak başlat
            flask_thread = run_api_server_in_thread(host='0.0.0.0', port=5000)
            
            # Thread kontrolü
            if flask_thread and flask_thread.is_alive():
                logging.info("✅ Enhanced Stream Server başarıyla başlatıldı!")
                logging.info("📡 Stream Endpoints:")
                logging.info("   🎥 Temel Video: http://localhost:5000/video_feed/camera_0")
                logging.info("   🤸 Pose Stream: http://localhost:5000/video_feed/camera_0/pose")
                logging.info("   🚨 AI Detection: http://localhost:5000/video_feed/camera_0/detection")
                logging.info("   📊 API Dokümantasyon: http://localhost:5000/")
                logging.info("   📈 İstatistikler: http://localhost:5000/api/stats")
                
                # Kısa bir bekleme - server'ın tamamen başlaması için
                time.sleep(2)
            else:
                logging.error("❌ Stream Server başlatılamadı!")
                
        except Exception as e:
            logging.error(f"❌ Stream Server başlatma hatası: {str(e)}")

        # ===== ANA PENCERE OLUŞTURMA =====
        logging.info("🖥️ Ana pencere oluşturuluyor...")
        root = tk.Tk()
        root.title(f"{APP_NAME} v{APP_VERSION}")
        root.configure(bg="#f5f5f5")  # Varsayılan açık gri arka plan
        
        # Tam ekran moduna geçiş
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        logging.info(f"🖥️ Ekran çözünürlüğü: {screen_width}x{screen_height}")
        
        # Pencere boyutunu önce ekran boyutuna ayarla
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Minimum pencere boyutu - Enhanced UI için artırıldı
        root.minsize(1200, 800)
        
        # Tam ekran modu etkinleştir
        try:
            if platform.system() == "Windows":
                root.state('zoomed')  # Windows tam ekran
            else:
                root.attributes('-zoomed', True)  # Linux tam ekran
            logging.info("✅ Tam ekran modu etkinleştirildi")
        except Exception as e:
            logging.warning(f"⚠️ Tam ekran modu ayarlanamadı: {str(e)}")
        
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
                logging.info("✅ Uygulama ikonu başarıyla yüklendi")
            else:
                # İkon dosyası bulunamadı
                logging.warning(f"⚠️ Uygulama ikonu bulunamadı: {icon_path}")
        except Exception as e:
            # İkon yükleme hatası
            logging.warning(f"⚠️ Uygulama ikonu yüklenirken hata: {str(e)}")
        
        # ===== AÇILIŞ EKRANI BAŞLATMA =====
        logging.info("🎬 Açılış ekranı gösteriliyor...")
        
        # Enhanced açılış ekranı - YOLOv11 bilgileri ile
        splash = SplashScreen(root, duration=5.0)  # 5 saniye göster
        
        # ===== ANA UYGULAMA BAŞLATMA =====
        logging.info("🚀 Enhanced GuardApp başlatılıyor...")
        
        # Enhanced GuardApp sınıfından ana uygulama nesnesini oluştur
        app = GuardApp(root)
        logging.info("✅ Enhanced GuardApp başarıyla başlatıldı")
        
        # Başlangıç istatistikleri
        logging.info("📊 Başlangıç İstatistikleri:")
        logging.info(f"   🎯 YOLOv11 Model: {'✅ Yüklü' if os.path.exists(MODEL_PATH) else '❌ Eksik'}")
        logging.info(f"   🚀 GPU Desteği: {'✅ Var' if gpu_available else '❌ Yok (CPU kullanılacak)'}")
        logging.info(f"   🌐 Stream Server: {'✅ Aktif' if flask_thread and flask_thread.is_alive() else '❌ Pasif'}")
        logging.info(f"   💻 Platform: {platform.system()} {platform.architecture()[0]}")
        
        # ===== TKINTER ANA DÖNGÜSÜ =====
        logging.info("🔄 Tkinter ana döngüsü başlatılıyor...")
        logging.info("=" * 80)
        logging.info("🎉 Guard AI sistemi hazır! Kullanıcı arayüzü aktif.")
        logging.info("=" * 80)
        
        # Uygulama döngüsünü başlat (UI olaylarını işlemeye başla)
        root.mainloop()
        
    except KeyboardInterrupt:
        # ===== KULLANICI İPTALİ =====
        logging.info("⚠️ Kullanıcı tarafından iptal edildi (Ctrl+C)")
        return True
        
    except Exception as e:
        # ===== KRİTİK HATA YÖNETİMİ =====
        # Beklenmeyen bir hata oluştuğunda tüm hata izini ve mesajını logla
        logging.error("💥 KRİTİK HATA: Uygulama çalışırken hata oluştu!", exc_info=True)
        logging.error(f"   Hata Türü: {type(e).__name__}")
        logging.error(f"   Hata Mesajı: {str(e)}")
        
        # Hata izini konsola yazdır (geliştiriciler için)
        print("\n\n" + "="*80)
        print("💥 KRİTİK HATA DETAYLARI:")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")
        
        # Kullanıcıya hata mesajı göster
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Kritik Hata - Guard AI",
                f"Uygulama çalışırken beklenmeyen bir hata oluştu:\n\n"
                f"Hata Türü: {type(e).__name__}\n"
                f"Hata Mesajı: {str(e)}\n\n"
                f"Detaylar log dosyasında bulunabilir.\n"
                f"Uygulama kapatılacak."
            )
        except:
            pass
        
        # Uygulamadan çık
        return False
        
    finally:
        # ===== KAPATMA İŞLEMLERİ =====
        logging.info("🧹 Temizlik işlemleri başlatılıyor...")
        
        try:
            # Tkinter kaynaklarını temizle
            if 'root' in locals():
                root.destroy()
                logging.info("✅ Tkinter kaynakları temizlendi")
        except Exception as e:
            logging.warning(f"⚠️ Tkinter temizleme hatası: {str(e)}")
        
        try:
            # Enhanced GuardApp cleanup
            if 'app' in locals() and hasattr(app, '_cleanup_resources'):
                app._cleanup_resources()
                logging.info("✅ GuardApp kaynakları temizlendi")
        except Exception as e:
            logging.warning(f"⚠️ GuardApp temizleme hatası: {str(e)}")
        
        logging.info("=" * 80)
        logging.info("👋 Guard AI uygulaması kapatıldı.")
        logging.info("=" * 80)
        
        return True

def check_dependencies():
    """Gelişmiş bağımlılık kontrolü."""
    logging.info("🔍 Bağımlılıklar kontrol ediliyor...")
    
    # Kritik bağımlılıkların enhanced listesi
    required_modules = {
        # Temel Python modülleri
        "sys": "Python sistem modülü",
        "os": "İşletim sistemi arayüzü",
        "threading": "Thread işlemleri",
        "logging": "Loglama sistemi",
        
        # Görüntü işleme ve AI
        "cv2": "OpenCV - Bilgisayarlı görü",
        "numpy": "NumPy - Sayısal hesaplamalar",
        "PIL": "Pillow - Görüntü işleme",
        
        # Deep Learning
        "torch": "PyTorch - Derin öğrenme framework",
        "ultralytics": "YOLOv11 - Nesne algılama",
        "deep_sort_realtime": "DeepSORT - Çoklu nesne takibi",
        
        # Firebase
        "firebase_admin": "Firebase Admin SDK",
        "pyrebase": "Pyrebase - Firebase Python client",
        
        # Web ve API
        "flask": "Flask - Web framework",
        "flask_cors": "Flask-CORS - CORS desteği",
        "requests": "HTTP istekleri",
        
        # Bildirim ve iletişim
        "telepot": "Telegram Bot API",
        
        # Diğer
        "dotenv": "Çevre değişkenleri yönetimi"
    }
    
    missing_modules = []
    optional_modules = []
    
    for module, description in required_modules.items():
        try:
            # Modülü içe aktarmayı dene
            __import__(module)
            logging.debug(f"✅ {module}: {description}")
        except ImportError as e:
            if module in ["telepot"]:  # Opsiyonel modüller
                optional_modules.append((module, description))
                logging.warning(f"⚠️ Opsiyonel modül eksik: {module} - {description}")
            else:
                missing_modules.append((module, description))
                logging.error(f"❌ Kritik modül eksik: {module} - {description}")
    
    # Sonuçları raporla
    if missing_modules:
        logging.error("❌ Eksik kritik bağımlılıklar:")
        for module, desc in missing_modules:
            logging.error(f"   - {module}: {desc}")
        
        # Kullanıcıya yükleme talimatları ver
        module_names = [module for module, _ in missing_modules]
        install_command = f"pip install {' '.join(module_names)}"
        
        logging.info("📥 Yükleme komutu:")
        logging.info(f"   {install_command}")
        
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Eksik Bağımlılıklar - Guard AI",
                f"Aşağıdaki kritik bağımlılıklar eksik:\n\n" + 
                "\n".join([f"• {module}: {desc}" for module, desc in missing_modules]) + 
                f"\n\nYükleme komutu:\n{install_command}"
            )
        except:
            print(f"❌ Eksik bağımlılıklar: {', '.join(module_names)}")
            print(f"Yükleme komutu: {install_command}")
        
        return False
    
    if optional_modules:
        logging.info("ℹ️ Opsiyonel bağımlılıklar:")
        for module, desc in optional_modules:
            logging.info(f"   ⚠️ {module}: {desc}")
    
    logging.info("✅ Tüm kritik bağımlılıklar mevcut!")
    return True

# Ana program başlangıç noktası
if __name__ == "__main__":
    # ===== ÇALIŞMA DİZİNİ AYARI =====
    # Proje kök dizinine git (göreceli dosya yolu sorunlarını önler)
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Basit loglama başlat (setup_logger'dan önce)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    logging.info(f"🗂️ Çalışma dizini: {os.getcwd()}")
    
    # ===== BAĞIMLILIK KONTROLÜ =====
    if not check_dependencies():
        sys.exit(1)
    
    # ===== ANA UYGULAMAYI BAŞLAT =====
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Kullanıcı tarafından iptal edildi.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)
# -*- coding: utf-8 -*-
# =======================================================================================
# === PROGRAM AÇIKLAMASI ===
# Dosya Adı: main.py 
# Konum: pc/main.py
# Açıklama:
# Guard AI Ultra - FallDetector ve UltraGuardApp ile tam entegre ana giriş noktası
# DÜZELTME: Kamera doğrulama süreci optimize edildi, sistem kapanma sorunu çözüldü
# =======================================================================================

import tkinter as tk               # GUI bileşenleri için temel kütüphane
import sys                         # Sistem işlemleri (çıkış, argüman işleme)
import os                          # Dosya/dizin işlemleri
import logging                     # Loglama işlemleri
import traceback                   # Hata izleme için
import threading                   # Thread işlemleri için
import time                        # Zaman işlemleri
import platform                   # Platform bilgisi
import json                        # JSON işlemleri
import subprocess                  # Alt süreç işlemleri
from datetime import datetime      # Tarih-zaman işlemleri
from pathlib import Path          # Modern dosya yolu işlemleri

# Enhanced modüller
from utils.logger import setup_logger       # Gelişmiş loglama yapılandırma
from splash import SplashScreen              # Enhanced açılış ekranı
from ui.app import GuardApp 
from core.stream_server import run_api_server_in_thread  # Enhanced Stream Server
from config.settings import APP_NAME, APP_VERSION, MODEL_PATH, validate_config  # Enhanced settings

# Windows kamera timeout sorunu için hızlı çözüm
import os
os.environ['OPENCV_CAMERA_TIMEOUT'] = '5000'  # 5 saniye timeout - iyileştirildi
os.environ['OPENCV_VIDEOIO_PRIORITY_DSHOW'] = '1'  # DirectShow öncelik
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'  # Hardware transforms devre dışı

# Uygulama meta verileri
APP_METADATA = {
    "name": "Guard AI Ultra",
    "version": "3.0.0",
    "build_date": "2025-06-06",
    "build_time": "15:38:40",
    "developer": "mehmetkarataslar",
    "description": "Ultra Enhanced AI Fall Detection System",
    "ai_engine": "FallDetector v3.0",
    "supported_models": ["yolo11n-pose", "yolo11s-pose", "yolo11m-pose", "yolo11l-pose", "yolo11x-pose"]
}

def print_startup_banner():
    """Ultra gelişmiş başlangıç banner'ını yazdır."""
    banner = f"""
{'='*100}
🚀 {APP_METADATA['name']} v{APP_METADATA['version']} - {APP_METADATA['description']}
{'='*100}
📅 Build: {APP_METADATA['build_date']} {APP_METADATA['build_time']}
👨‍💻 Developer: {APP_METADATA['developer']}
🤖 AI Engine: {APP_METADATA['ai_engine']}
🎯 Supported Models: {len(APP_METADATA['supported_models'])} YOLOv11 variants
💻 Platform: {platform.system()} {platform.architecture()[0]}
🐍 Python: {sys.version.split()[0]}
{'='*100}
"""
    print(banner)
    logging.info("🎉 Guard AI Ultra başlatılıyor...")

def check_enhanced_system_requirements():
    """Ultra gelişmiş sistem gereksinimlerini kontrol eder."""
    logging.info("🔍 Ultra Enhanced sistem gereksinimleri kontrol ediliyor...")
    
    # Platform bilgisi - Enhanced
    system_info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.architecture()[0],
        'processor': platform.processor(),
        'python_version': sys.version,
        'python_major': sys.version_info.major,
        'python_minor': sys.version_info.minor,
        'machine': platform.machine(),
        'node': platform.node()
    }
    
    logging.info(f"💻 Sistem: {system_info['platform']} {system_info['architecture']}")
    logging.info(f"🖥️ İşlemci: {system_info['processor']}")
    logging.info(f"🐍 Python: {sys.version.split()[0]} ({system_info['python_major']}.{system_info['python_minor']})")
    logging.info(f"🏷️ Makine: {system_info['machine']}")
    
    # Python versiyon kontrolü - Enhanced
    if system_info['python_major'] < 3 or (system_info['python_major'] == 3 and system_info['python_minor'] < 8):
        logging.error(f"❌ Python 3.8+ gerekli, mevcut: {system_info['python_major']}.{system_info['python_minor']}")
        return False, "Python versiyon uyumsuzluğu"
    
    # Bellek kontrolü
    try:
        import psutil
        memory_gb = psutil.virtual_memory().total / (1024**3)
        logging.info(f"💾 Toplam RAM: {memory_gb:.1f} GB")
        
        if memory_gb < 4.0:
            logging.warning(f"⚠️ Düşük RAM: {memory_gb:.1f} GB (Önerilen: 8GB+)")
        else:
            logging.info(f"✅ RAM yeterli: {memory_gb:.1f} GB")
    except ImportError:
        logging.warning("⚠️ psutil bulunamadı, bellek kontrolü atlandı")
    
    # Enhanced AI model dosyası kontrolü
    model_status = check_ai_models()
    if not model_status['has_any_model']:
        logging.error("❌ Hiçbir YOLOv11 pose model dosyası bulunamadı!")
        return False, "AI model dosyaları eksik"
    
    # Konfigürasyon doğrulama - Enhanced
    try:
        config_errors = validate_config()
        if config_errors:
            logging.error("❌ Enhanced konfigürasyon hataları:")
            for error in config_errors:
                logging.error(f"   - {error}")
            return False, f"Konfigürasyon hataları: {len(config_errors)} adet"
        else:
            logging.info("✅ Enhanced konfigürasyon doğrulandı")
    except Exception as e:
        logging.warning(f"⚠️ Konfigürasyon kontrolü atlandı: {e}")
    
    # Dosya sistemi kontrolü
    current_dir = Path.cwd()
    required_dirs = ['ui', 'core', 'config', 'utils', 'data']
    
    for dir_name in required_dirs:
        dir_path = current_dir / dir_name
        if not dir_path.exists():
            logging.error(f"❌ Gerekli dizin bulunamadı: {dir_name}")
            return False, f"Eksik dizin: {dir_name}"
    
    logging.info(f"✅ Proje yapısı doğrulandı: {len(required_dirs)} dizin")
    
    return True, "Sistem gereksinimleri karşılandı"

def check_ai_models():
    """AI model dosyalarını kontrol eder."""
    logging.info("🤖 AI model dosyaları kontrol ediliyor...")
    
    model_status = {
        'has_any_model': False,
        'available_models': [],
        'primary_model': None,
        'total_size_mb': 0
    }
    
    # Model dizini
    model_dir = Path(MODEL_PATH).parent
    
    # Desteklenen model dosyaları
    supported_models = APP_METADATA['supported_models']
    
    for model_name in supported_models:
        model_file = f"{model_name}.pt"
        model_path = model_dir / model_file
        
        if model_path.exists():
            model_size = model_path.stat().st_size / (1024 * 1024)  # MB
            model_status['available_models'].append({
                'name': model_name,
                'path': str(model_path),
                'size_mb': model_size,
                'is_primary': str(model_path) == MODEL_PATH
            })
            model_status['total_size_mb'] += model_size
            model_status['has_any_model'] = True
            
            if str(model_path) == MODEL_PATH:
                model_status['primary_model'] = model_name
                
            logging.info(f"✅ Model bulundu: {model_name} ({model_size:.1f} MB)")
        else:
            logging.debug(f"⚠️ Model bulunamadı: {model_name}")
    
    # Ana model kontrolü
    if not Path(MODEL_PATH).exists():
        if model_status['available_models']:
            # Alternatif model kullan
            alt_model = model_status['available_models'][0]
            logging.warning(f"⚠️ Ana model bulunamadı, alternatif kullanılacak: {alt_model['name']}")
            model_status['primary_model'] = alt_model['name']
        else:
            logging.error("❌ Hiçbir YOLOv11 pose model dosyası bulunamadı!")
            logging.info("📥 Model indirme önerileri:")
            for model in supported_models[:3]:  # İlk 3 model
                logging.info(f"   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/{model}.pt")
    else:
        primary_size = Path(MODEL_PATH).stat().st_size / (1024 * 1024)
        logging.info(f"✅ Ana model OK: {model_status['primary_model']} ({primary_size:.1f} MB)")
    
    logging.info(f"🎯 Mevcut modeller: {len(model_status['available_models'])}/{len(supported_models)}")
    logging.info(f"💾 Toplam model boyutu: {model_status['total_size_mb']:.1f} MB")
    
    return model_status

def check_enhanced_gpu_availability():
    """Gelişmiş GPU kullanılabilirlik kontrolü."""
    gpu_info = {
        'available': False,
        'device_count': 0,
        'devices': [],
        'cuda_version': None,
        'recommended_for_ai': False,
        'memory_total_gb': 0
    }
    
    try:
        import torch
        
        # CUDA kullanılabilirlik
        if torch.cuda.is_available():
            gpu_info['available'] = True
            gpu_info['device_count'] = torch.cuda.device_count()
            gpu_info['cuda_version'] = torch.version.cuda
            
            logging.info(f"🚀 CUDA GPU algılandı: {gpu_info['device_count']} adet")
            logging.info(f"🔧 CUDA Versiyon: {gpu_info['cuda_version']}")
            
            total_memory = 0
            for i in range(gpu_info['device_count']):
                device_name = torch.cuda.get_device_name(i)
                device_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)  # GB
                device_capability = torch.cuda.get_device_properties(i).major
                
                device_info = {
                    'index': i,
                    'name': device_name,
                    'memory_gb': device_memory,
                    'compute_capability': device_capability,
                    'is_recommended': device_memory >= 4.0 and device_capability >= 6
                }
                
                gpu_info['devices'].append(device_info)
                total_memory += device_memory
                
                logging.info(f"   GPU {i}: {device_name}")
                logging.info(f"     💾 VRAM: {device_memory:.1f} GB")
                logging.info(f"     🎯 Compute: {device_capability}.x")
                logging.info(f"     ✅ AI Uygun: {'Evet' if device_info['is_recommended'] else 'Hayır'}")
                
                if device_info['is_recommended']:
                    gpu_info['recommended_for_ai'] = True
            
            gpu_info['memory_total_gb'] = total_memory
            
            if gpu_info['recommended_for_ai']:
                logging.info(f"✅ AI için uygun GPU mevcut: {total_memory:.1f} GB toplam VRAM")
            else:
                logging.warning(f"⚠️ AI için önerilen GPU yok (4GB+ VRAM gerekli)")
                
        else:
            logging.info("💻 CUDA GPU bulunamadı, CPU kullanılacak")
            
    except ImportError:
        logging.warning("⚠️ PyTorch bulunamadı, GPU kontrolü atlandı")
    except Exception as e:
        logging.error(f"❌ GPU kontrol hatası: {str(e)}")
    
    return gpu_info


def check_enhanced_dependencies():
    """Ultra gelişmiş bağımlılık kontrolü."""
    logging.info("🔍 Enhanced bağımlılıklar kontrol ediliyor...")
    
    # Kritik bağımlılıkların ultra enhanced listesi
    critical_modules = {
        # Core Python
        "sys": {"desc": "Python sistem modülü", "min_version": None},
        "os": {"desc": "İşletim sistemi arayüzü", "min_version": None},
        "threading": {"desc": "Thread işlemleri", "min_version": None},
        "logging": {"desc": "Loglama sistemi", "min_version": None},
        "json": {"desc": "JSON işleme", "min_version": None},
        "pathlib": {"desc": "Modern dosya yolları", "min_version": None},
        
        # GUI
        "tkinter": {"desc": "GUI framework", "min_version": None},
        
        # Computer Vision & AI
        "cv2": {"desc": "OpenCV - Bilgisayarlı görü", "min_version": "4.5.0"},
        "numpy": {"desc": "NumPy - Sayısal hesaplamalar", "min_version": "1.20.0"},
        "PIL": {"desc": "Pillow - Görüntü işleme", "min_version": "8.0.0"},
        
        # Deep Learning & AI
        "torch": {"desc": "PyTorch - Derin öğrenme", "min_version": "1.12.0"},
        "ultralytics": {"desc": "YOLOv11 - Nesne algılama", "min_version": "8.0.0"},
        
        # Firebase & Database
        "firebase_admin": {"desc": "Firebase Admin SDK", "min_version": "6.0.0"},
        
        # Web & API
        "flask": {"desc": "Flask - Web framework", "min_version": "2.0.0"},
        "flask_cors": {"desc": "Flask-CORS - CORS desteği", "min_version": "3.0.0"},
        "requests": {"desc": "HTTP istekleri", "min_version": "2.25.0"},
        
        # Performance & Monitoring
        "psutil": {"desc": "Sistem izleme", "min_version": "5.8.0"},
        "time": {"desc": "Zaman işlemleri", "min_version": None},
        "datetime": {"desc": "Tarih-zaman işlemleri", "min_version": None}
    }
    
    # Opsiyonel bağımlılıklar
    optional_modules = {
        "telepot": {"desc": "Telegram Bot API", "min_version": "12.0"},
        "python-dotenv": {"desc": "Çevre değişkenleri", "min_version": "0.19.0"},
        "pyrebase": {"desc": "Pyrebase - Firebase client", "min_version": "4.0.0"},
        "winsound": {"desc": "Windows ses sistemi", "min_version": None},
        "platform": {"desc": "Platform bilgisi", "min_version": None}
    }
    
    # Test sonuçları
    results = {
        'critical_missing': [],
        'critical_version_mismatch': [],
        'optional_missing': [],
        'all_available': [],
        'total_checked': 0,
        'success_rate': 0.0
    }
    
    def check_module_version(module_name, module_obj, min_version):
        """Modül versiyonunu kontrol et."""
        if min_version is None:
            return True, "N/A"
        
        try:
            # Farklı versiyon attribute'ları dene
            version_attrs = ['__version__', 'version', 'VERSION', '__VERSION__']
            version = None
            
            for attr in version_attrs:
                if hasattr(module_obj, attr):
                    version = getattr(module_obj, attr)
                    break
            
            if version is None:
                return True, "Unknown"
            
            # Basit versiyon karşılaştırması
            try:
                from packaging import version as pkg_version
                return pkg_version.parse(str(version)) >= pkg_version.parse(min_version), str(version)
            except ImportError:
                # packaging yoksa basit string karşılaştırması
                return str(version) >= min_version, str(version)
                
        except Exception:
            return True, "Check Failed"
    
    # Kritik modülleri kontrol et
    logging.info("🔍 Kritik bağımlılıklar kontrol ediliyor...")
    for module_name, info in critical_modules.items():
        results['total_checked'] += 1
        try:
            module_obj = __import__(module_name)
            
            # Versiyon kontrolü
            version_ok, current_version = check_module_version(module_name, module_obj, info.get('min_version'))
            
            if version_ok:
                results['all_available'].append((module_name, info['desc'], current_version))
                logging.debug(f"✅ {module_name}: {info['desc']} (v{current_version})")
            else:
                results['critical_version_mismatch'].append((module_name, info['desc'], current_version, info['min_version']))
                logging.error(f"❌ {module_name}: Versiyon uyumsuz (v{current_version} < v{info['min_version']})")
                
        except ImportError as e:
            results['critical_missing'].append((module_name, info['desc']))
            logging.error(f"❌ Kritik modül eksik: {module_name} - {info['desc']}")
    
    # Opsiyonel modülleri kontrol et
    logging.info("🔍 Opsiyonel bağımlılıklar kontrol ediliyor...")
    for module_name, info in optional_modules.items():
        results['total_checked'] += 1
        try:
            module_obj = __import__(module_name)
            version_ok, current_version = check_module_version(module_obj, module_obj, info.get('min_version'))
            
            if version_ok:
                results['all_available'].append((module_name, info['desc'], current_version))
                logging.debug(f"✅ {module_name}: {info['desc']} (v{current_version})")
            else:
                logging.warning(f"⚠️ {module_name}: Versiyon uyumsuz (v{current_version} < v{info['min_version']})")
                
        except ImportError:
            results['optional_missing'].append((module_name, info['desc']))
            logging.warning(f"⚠️ Opsiyonel modül eksik: {module_name} - {info['desc']}")
    
    # Sonuçları hesapla
    available_count = len(results['all_available'])
    results['success_rate'] = (available_count / results['total_checked']) * 100
    
    # Rapor
    logging.info(f"📊 Bağımlılık Kontrolü Özeti:")
    logging.info(f"   ✅ Mevcut: {available_count}/{results['total_checked']} (%{results['success_rate']:.1f})")
    logging.info(f"   ❌ Kritik eksik: {len(results['critical_missing'])}")
    logging.info(f"   ⚠️ Versiyon uyumsuz: {len(results['critical_version_mismatch'])}")
    logging.info(f"   📦 Opsiyonel eksik: {len(results['optional_missing'])}")
    
    # Kritik sorunlar varsa çözüm öner
    if results['critical_missing'] or results['critical_version_mismatch']:
        logging.error("❌ Kritik bağımlılık sorunları tespit edildi!")
        
        # Yükleme komutları oluştur
        install_commands = []
        
        if results['critical_missing']:
            missing_modules = [module for module, _ in results['critical_missing']]
            install_commands.append(f"pip install {' '.join(missing_modules)}")
        
        if results['critical_version_mismatch']:
            upgrade_modules = [f"{module}>={min_ver}" for module, _, _, min_ver in results['critical_version_mismatch']]
            install_commands.append(f"pip install --upgrade {' '.join(upgrade_modules)}")
        
        logging.info("📥 Önerilen çözümler:")
        for cmd in install_commands:
            logging.info(f"   {cmd}")
        
        # GUI uyarısı - DÜZELTME: Opsiyonel yap
        try:
            import tkinter.messagebox as messagebox
            error_msg = "Kritik bağımlılıklar eksik veya eski versiyonda:\n\n"
            
            if results['critical_missing']:
                error_msg += "Eksik modüller:\n"
                for module, desc in results['critical_missing'][:5]:  # İlk 5'i göster
                    error_msg += f"• {module}: {desc}\n"
            
            if results['critical_version_mismatch']:
                error_msg += "\nEski versiyonlar:\n"
                for module, desc, current, required in results['critical_version_mismatch'][:3]:
                    error_msg += f"• {module}: v{current} → v{required} gerekli\n"
            
            error_msg += f"\nÇözüm komutları:\n"
            for cmd in install_commands:
                error_msg += f"{cmd}\n"
            
            messagebox.showerror("Bağımlılık Hatası - Guard AI Ultra", error_msg)
            
        except:
            print("❌ Kritik bağımlılık sorunları tespit edildi!")
            for cmd in install_commands:
                print(f"Çözüm: {cmd}")
        
        return False, results
    
    # Opsiyonel eksiklikler için bilgi ver
    if results['optional_missing']:
        logging.info("ℹ️ Opsiyonel özellikler için eksik modüller:")
        for module, desc in results['optional_missing']:
            logging.info(f"   📦 {module}: {desc}")
        logging.info("   💡 Bu modüller olmadan da çalışabilir, ancak bazı özellikler devre dışı olacak.")
    
    logging.info("✅ Kritik bağımlılık kontrolü başarılı!")
    return True, results



def safe_camera_validation():
    """DÜZELTME: Windows uyumlu güvenli kamera doğrulama - SIGALRM sorunu çözüldü"""
    logging.info("📹 Windows uyumlu kamera doğrulaması başlatılıyor...")
    
    try:
        import cv2
        import threading
        from config.settings import CAMERA_CONFIGS
        
        validated_cameras = []
        
        def test_camera_with_timeout(camera_index, camera_name, result_dict, timeout=3):
            """Thread içinde kamera testi - Windows uyumlu timeout"""
            cap = None
            try:
                logging.info(f"🔍 Kamera {camera_index} ({camera_name}) test ediliyor...")
                
                # Kamerayı aç - Enhanced parametler ile
                cap = cv2.VideoCapture(camera_index)
                
                # YOLOv11 için ZORUNLU 640x640 kare format - mehrere denemeler
                for attempt in range(3):
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
                    cap.set(cv2.CAP_PROP_FPS, 30)  # Daha yüksek FPS
                    
                    # Doğrulama
                    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    if actual_w == 640 and actual_h == 640:
                        logging.info(f"✅ Kamera {camera_index} test: PERFECT 640x640")
                        break
                    else:
                        logging.warning(f"⚠️ Kamera {camera_index} test deneme {attempt+1}: {actual_w}x{actual_h}")
                        time.sleep(0.1)
                else:
                    logging.warning(f"⚠️ Kamera {camera_index} test: Native {actual_w}x{actual_h} kullanacak")
                
                if cap.isOpened():
                    # Frame test et - birkaç frame dene
                    for attempt in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.shape[0] > 0:
                            logging.info(f"✅ Kamera {camera_index} çalışıyor: {frame.shape}")
                            result_dict['success'] = True
                            result_dict['frame_shape'] = frame.shape
                            break
                        time.sleep(0.1)  # Kısa bekleme
                    else:
                        logging.warning(f"⚠️ Kamera {camera_index} açık ama frame alamadı")
                        result_dict['success'] = False
                        result_dict['error'] = "Frame alınamadı"
                else:
                    logging.warning(f"⚠️ Kamera {camera_index} açılamadı")
                    result_dict['success'] = False
                    result_dict['error'] = "Kamera açılamadı"
                
            except Exception as e:
                logging.warning(f"⚠️ Kamera {camera_index} test hatası: {e}")
                result_dict['success'] = False
                result_dict['error'] = str(e)
            finally:
                # Güvenli cleanup
                try:
                    if cap is not None:
                        cap.release()
                except:
                    pass
        
        # Her kamera için test
        for config in CAMERA_CONFIGS:
            camera_index = config['index']
            camera_name = config['name']
            
            # Windows uyumlu timeout sistemi
            result_dict = {'success': False, 'error': None}
            
            # Thread oluştur
            test_thread = threading.Thread(
                target=test_camera_with_timeout, 
                args=(camera_index, camera_name, result_dict, 3),
                daemon=True
            )
            
            # Thread'i başlat
            test_thread.start()
            
            # 3 saniye bekle
            test_thread.join(timeout=3.0)
            
            # Thread hala çalışıyorsa timeout olmuş demektir
            if test_thread.is_alive():
                logging.warning(f"⚠️ Kamera {camera_index} test timeout - atlandı")
                # Thread'i bırak, daemon olduğu için kendini temizler
            else:
                # Test tamamlandı, sonucu kontrol et
                if result_dict['success']:
                    validated_cameras.append(config)
                    logging.info(f"✅ Kamera {camera_index} validated")
        
        logging.info(f"📊 Kamera doğrulama sonucu: {len(validated_cameras)}/{len(CAMERA_CONFIGS)} başarılı")
        
        # En az bir kamera olmalı - ama zorlamıyoruz
        if not validated_cameras:
            logging.warning("⚠️ Hiçbir kamera doğrulanamadı, ancak sistem devam edecek")
        
        return True  # Her durumda sistem devam etsin
        
    except Exception as e:
        logging.error(f"❌ Güvenli kamera doğrulama hatası: {e}")
        return True  # Hata olsa da sistem çalışsın


def enhanced_main():
    """
    DÜZELTME: Ultra Enhanced Guard AI PC uygulamasını başlatır - Güvenli mod
    """
    
    # Enhanced loglama sistemini başlat
    setup_logger()
    print_startup_banner()

    try:
        # ===== ULTRA ENHANCED SİSTEM GEREKSİNİMLERİ KONTROLÜ =====
        logging.info("🔍 Phase 1: Ultra Enhanced sistem gereksinimleri kontrolü")
        system_ok, system_message = check_enhanced_system_requirements()
        
        if not system_ok:
            logging.error(f"❌ Sistem gereksinimleri karşılanmıyor: {system_message}")
            
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror(
                    "Sistem Gereksinimleri - Guard AI Ultra",
                    f"Sistem gereksinimleri karşılanmıyor:\n\n{system_message}\n\n"
                    "Lütfen sisteminizi güncelleyin ve tekrar deneyin."
                )
            except:
                print(f"❌ Sistem gereksinimleri: {system_message}")
            
            return False
        
        logging.info(f"✅ Sistem gereksinimleri: {system_message}")
        
        # ===== ULTRA ENHANCED GPU KONTROLÜ =====
        logging.info("🔍 Phase 2: Enhanced GPU capability detection")
        gpu_info = check_enhanced_gpu_availability()
        
        if gpu_info['available']:
            if gpu_info['recommended_for_ai']:
                logging.info(f"🚀 AI için optimize GPU: {gpu_info['memory_total_gb']:.1f} GB VRAM")
            else:
                logging.warning("⚠️ GPU mevcut ancak AI için optimize değil")
        else:
            logging.info("💻 CPU modunda çalışacak")
        
        # ===== ULTRA ENHANCED BAĞIMLILIK KONTROLÜ =====
        logging.info("🔍 Phase 3: Ultra Enhanced dependency validation")
        deps_ok, deps_results = check_enhanced_dependencies()
        
        if not deps_ok:
            logging.error("❌ Kritik bağımlılık sorunları tespit edildi!")
            return False
        
        logging.info(f"✅ Bağımlılıklar: %{deps_results['success_rate']:.1f} başarı oranı")
        
        # ===== DÜZELTME: GÜVENLİ KAMERA KONTROLÜ =====
        logging.info("🔍 Phase 4: Güvenli kamera doğrulaması")
        camera_ok = safe_camera_validation()
        
        if not camera_ok:
            logging.warning("⚠️ Kamera sorunları var, ancak sistem devam edecek")
        
        # ===== AI MODEL VE ENHANCED STREAM SERVER =====
        logging.info("🔍 Phase 5: AI model validation ve Enhanced Stream Server")
        
        # AI modelleri kontrol et
        model_status = check_ai_models()
        if not model_status['has_any_model']:
            logging.error("❌ AI modelleri bulunamadı!")
            
            try:
                import tkinter.messagebox as messagebox
                result = messagebox.askyesno(
                    "AI Model Hatası - Guard AI Ultra",
                    "YOLOv11 pose estimation modelleri bulunamadı!\n\n"
                    "En az bir model dosyası gerekli:\n"
                    "• yolo11n-pose.pt (hafif)\n"
                    "• yolo11s-pose.pt (küçük)\n"
                    "• yolo11l-pose.pt (büyük - önerilen)\n\n"
                    "Model olmadan da devam edilsin mi?\n"
                    "(AI özellikleri devre dışı olacak)"
                )
                
                if not result:
                    return False
            except:
                print("❌ AI modelleri bulunamadı!")
                return False
        
        logging.info(f"✅ AI Modelleri: {len(model_status['available_models'])} model, {model_status['total_size_mb']:.1f} MB")
        
        # DÜZELTME: Enhanced Stream Server'ı güvenli başlat
        flask_thread = None
        try:
            logging.info("🌐 Enhanced YOLOv11 Stream Server başlatılıyor...")
            
            flask_thread = run_api_server_in_thread(host='0.0.0.0', port=5000)
            
            if flask_thread and flask_thread.is_alive():
                logging.info("✅ Enhanced Stream Server başarıyla başlatıldı!")
                logging.info("📡 Enhanced Stream Endpoints:")
                logging.info("   🎥 Video Feed: http://localhost:5000/video_feed/camera_0")
                logging.info("   🤸 Pose Analysis: http://localhost:5000/video_feed/camera_0/pose")
                logging.info("   🚨 AI Detection: http://localhost:5000/video_feed/camera_0/detection")
                logging.info("   📊 Real-time Stats: http://localhost:5000/api/stats")
                logging.info("   🔧 API Documentation: http://localhost:5000/api/docs")
                
                # Server'ın tamamen başlaması için kısa bekleme
                time.sleep(1.5)  # 2 -> 1.5 saniye
            else:
                logging.warning("⚠️ Enhanced Stream Server başlatılamadı, ancak sistem devam edecek")
                
        except Exception as e:
            logging.warning(f"⚠️ Enhanced Stream Server başlatma hatası: {str(e)}")

        # ===== ULTRA ENHANCED ANA PENCERE OLUŞTURMA =====
        logging.info("🔍 Phase 6: Ultra Enhanced UI initialization")
        
        root = tk.Tk()
        root.title(f"{APP_METADATA['name']} v{APP_METADATA['version']}")
        root.configure(bg="#f8f9fa")  # Modern açık gri arka plan
        
        # Ekran bilgilerini al - Enhanced
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        screen_dpi = root.winfo_fpixels('1i')  # DPI
        
        logging.info(f"🖥️ Ekran: {screen_width}x{screen_height} @ {screen_dpi:.0f} DPI")
        
        # Ultra enhanced pencere boyutlandırma
        if screen_width >= 1920 and screen_height >= 1080:
            # 4K/1440p screens
            window_width = int(screen_width * 0.9)
            window_height = int(screen_height * 0.9)
            logging.info("🖥️ Yüksek çözünürlük ekran tespit edildi")
        else:
            # Standard HD screens
            window_width = min(1400, int(screen_width * 0.8))
            window_height = min(900, int(screen_height * 0.8))
            logging.info("🖥️ Standart çözünürlük ekran tespit edildi")
        
        # Pencereyi merkeze konumlandır
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.minsize(1200, 800)  # Ultra enhanced minimum boyut
        
        # Enhanced tam ekran desteği
        try:
            if platform.system() == "Windows":
                root.state('zoomed')
                logging.info("✅ Windows tam ekran modu etkinleştirildi")
            elif platform.system() == "Linux":
                root.attributes('-zoomed', True)
                logging.info("✅ Linux tam ekran modu etkinleştirildi")
            elif platform.system() == "Darwin":  # macOS
                root.attributes('-fullscreen', True)
                logging.info("✅ macOS tam ekran modu etkinleştirildi")
        except Exception as e:
            logging.warning(f"⚠️ Tam ekran modu ayarlanamadı: {str(e)}")
        
        # ===== ULTRA ENHANCED UYGULAMA İKONU =====
        try:
            icon_path = Path(__file__).parent / "resources" / "icons" / "logo.png"
            
            if icon_path.exists():
                icon = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, icon)
                logging.info("✅ Ultra enhanced uygulama ikonu yüklendi")
            else:
                logging.warning(f"⚠️ İkon dosyası bulunamadı: {icon_path}")
        except Exception as e:
            logging.warning(f"⚠️ İkon yükleme hatası: {str(e)}")
        
        # ===== ULTRA ENHANCED AÇILIŞ EKRANI =====
        logging.info("🔍 Phase 7: Ultra Enhanced splash screen")
        
        # Enhanced splash screen - AI model durumu ile
        splash_info = {
            'app_name': APP_METADATA['name'],
            'version': APP_METADATA['version'],
            'ai_engine': APP_METADATA['ai_engine'],
            'models_count': len(model_status['available_models']),
            'gpu_available': gpu_info['available'],
            'gpu_recommended': gpu_info['recommended_for_ai'],
            'developer': APP_METADATA['developer']
        }
        
        splash = SplashScreen(root, duration=8, app_info=splash_info)  # 10 -> 8 saniye
        logging.info("🎬 Enhanced splash screen gösteriliyor...")
        
        # ===== GUARDAPP BAŞLATMA =====
        logging.info("🔍 Phase 8: GuardApp initialization")
        
        try:
            # DÜZELTME: GuardApp sınıfından ultra enhanced uygulama nesnesini güvenli oluştur
            app = GuardApp(root)
            
            # Enhanced başlangıç verilerini aktar
            app.system_state.update({
                'gpu_info': gpu_info,
                'model_status': model_status,
                'dependency_results': deps_results,
                'screen_info': {
                    'width': screen_width,
                    'height': screen_height,
                    'dpi': screen_dpi
                }
            })
            
            logging.info("✅ GuardApp başarıyla başlatıldı")
            
        except Exception as e:
            logging.error(f"❌ GuardApp başlatma hatası: {str(e)}")
            
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror(
                    "Uygulama Başlatma Hatası - Guard AI Ultra",
                    f"Ana uygulama başlatılamadı:\n\n{str(e)}\n\n"
                    "Lütfen log dosyasını kontrol edin ve tekrar deneyin."
                )
            except:
                print(f"❌ GuardApp başlatma hatası: {str(e)}")
            
            return False
        
        # ===== ENHANCED BAŞLANGIÇ İSTATİSTİKLERİ =====
        logging.info("📊 Enhanced Başlangıç İstatistikleri:")
        logging.info(f"   🎯 AI Modelleri: {len(model_status['available_models'])}/{len(APP_METADATA['supported_models'])}")
        logging.info(f"   🚀 GPU Durumu: {'✅ Optimize' if gpu_info['recommended_for_ai'] else '⚠️ CPU/Basic GPU'}")
        logging.info(f"   🌐 Stream Server: {'✅ Aktif' if 'flask_thread' in locals() and flask_thread and flask_thread.is_alive() else '❌ Pasif'}")
        logging.info(f"   📦 Bağımlılık: %{deps_results['success_rate']:.1f} ({len(deps_results['all_available'])}/{deps_results['total_checked']})")
        logging.info(f"   💻 Platform: {platform.system()} {platform.architecture()[0]}")
        logging.info(f"   🖥️ Ekran: {screen_width}x{screen_height} @ {screen_dpi:.0f} DPI")
        logging.info(f"   💾 AI Models: {model_status['total_size_mb']:.1f} MB")
        
        # ===== ULTRA ENHANCED TKINTER ANA DÖNGÜSÜ =====
        logging.info("🔍 Phase 9: Ultra Enhanced main loop")
        logging.info("=" * 100)
        logging.info("🎉 Guard AI Ultra sistemi hazır! Ultra Enhanced UI aktif.")
        logging.info("=" * 100)
        
        # DÜZELTME: Error handling ile ana döngüyü başlat
        try:
            root.protocol("WM_DELETE_WINDOW", lambda: on_window_close(root, app if 'app' in locals() else None))
            root.mainloop()
        except KeyboardInterrupt:
            logging.info("⚠️ Kullanıcı tarafından durduruldu (Ctrl+C)")
        except Exception as e:
            logging.error(f"❌ Ana döngü hatası: {str(e)}")
            traceback.print_exc()
        
        return True
        
    except KeyboardInterrupt:
        # ===== KULLANICI İPTALİ =====
        logging.info("⚠️ Kullanıcı tarafından iptal edildi (Ctrl+C)")
        return True
        
    except Exception as e:
        # ===== ULTRA ENHANCED KRİTİK HATA YÖNETİMİ =====
        logging.error("💥 ULTRA KRİTİK HATA: Uygulama çalışırken beklenmeyen hata!", exc_info=True)
        logging.error(f"   🔥 Hata Türü: {type(e).__name__}")
        logging.error(f"   📝 Hata Mesajı: {str(e)}")
        logging.error(f"   📍 Konum: {traceback.format_exc().splitlines()[-2] if len(traceback.format_exc().splitlines()) > 1 else 'Unknown'}")
        
        # Enhanced hata raporu
        error_report = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(e).__name__,
            'error_message': str(e),
            'app_version': APP_METADATA['version'],
            'platform': platform.system(),
            'python_version': sys.version.split()[0],
            'traceback': traceback.format_exc()
        }
        
        # Hata raporunu dosyaya kaydet
        try:
            error_file = Path('guard_ai_ultra_error_report.json')
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_report, f, indent=2, ensure_ascii=False)
            logging.info(f"📄 Hata raporu kaydedildi: {error_file}")
        except:
            pass
        
        # Enhanced hata izini
        print("\n\n" + "="*100)
        print("💥 ULTRA ENHANCED KRİTİK HATA DETAYLARI:")
        print("="*100)
        print(f"🕐 Zaman: {error_report['timestamp']}")
        print(f"🎯 Uygulama: {APP_METADATA['name']} v{APP_METADATA['version']}")
        print(f"🔥 Hata Türü: {error_report['error_type']}")
        print(f"📝 Hata Mesajı: {error_report['error_message']}")
        print(f"💻 Platform: {error_report['platform']}")
        print(f"🐍 Python: {error_report['python_version']}")
        print("="*100)
        traceback.print_exc()
        print("="*100 + "\n")
        
        # Enhanced kullanıcı bilgilendirmesi
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Kritik Hata - Guard AI Ultra",
                f"Guard AI Ultra çalışırken beklenmeyen bir hata oluştu:\n\n"
                f"🔥 Hata Türü: {type(e).__name__}\n"
                f"📝 Hata Mesajı: {str(e)}\n"
                f"🕐 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"📄 Detaylı hata raporu 'guard_ai_ultra_error_report.json' dosyasına kaydedildi.\n\n"
                f"🔧 Önerilen Çözümler:\n"
                f"• Uygulamayı yeniden başlatın\n"
                f"• Sistem gereksinimlerini kontrol edin\n"
                f"• AI model dosyalarını doğrulayın\n"
                f"• Bağımlılıkları güncelleyin\n\n"
                f"Uygulama kapatılacak."
            )
        except:
            pass
        
        return False
        
    finally:
        # ===== ULTRA ENHANCED KAPATMA İŞLEMLERİ =====
        logging.info("🧹 Ultra Enhanced temizlik işlemleri başlatılıyor...")
        
        cleanup_tasks = []
        
        try:
            # Tkinter kaynakları
            if 'root' in locals():
                root.destroy()
                cleanup_tasks.append("✅ Tkinter UI")
        except Exception as e:
            cleanup_tasks.append(f"⚠️ Tkinter UI: {str(e)[:50]}")
        
        try:
            # GuardApp cleanup
            if 'app' in locals() and app and hasattr(app, '_on_enhanced_close'):
                app._on_enhanced_close()
                cleanup_tasks.append("✅ GuardApp")
        except Exception as e:
            cleanup_tasks.append(f"⚠️ GuardApp: {str(e)[:50]}")
        
        try:
            # Flask server cleanup
            if 'flask_thread' in locals() and flask_thread and flask_thread.is_alive():
                # Flask server'ı kapatmak için signal gönder
                logging.info("🌐 Enhanced Stream Server kapatılıyor...")
                # Thread daemon olarak ayarlandığı için otomatik kapanacak
                cleanup_tasks.append("✅ Flask Server")
        except Exception as e:
            cleanup_tasks.append(f"⚠️ Flask Server: {str(e)[:50]}")
        
        try:
            # Thread cleanup
            active_threads = threading.active_count()
            if active_threads > 1:
                logging.info(f"🧵 {active_threads-1} aktif thread temizleniyor...")
                time.sleep(0.5)  # Thread'lerin temizlenmesi için kısa bekle
            cleanup_tasks.append("✅ Threading")
        except Exception as e:
            cleanup_tasks.append(f"⚠️ Threading: {str(e)[:50]}")
        
        # Final rapor
        logging.info("🧹 Temizlik Raporu:")
        for task in cleanup_tasks:
            logging.info(f"   {task}")
        
        # Session süresi hesaplama - DÜZELTME
        session_duration = time.time() - start_time if 'start_time' in locals() else 0
        
        logging.info("=" * 100)
        logging.info("👋 Guard AI Ultra uygulaması güvenli şekilde kapatıldı.")
        logging.info(f"🕐 Session sürdü: {session_duration:.1f}s")
        logging.info("=" * 100)
        
        return True

def on_window_close(root, app=None):
    """Enhanced pencere kapatma işleyicisi"""
    try:
        logging.info("🚪 Pencere kapatma işlemi başlatıldı")
        
        # Uygulama varsa önce onu kapat
        if app and hasattr(app, '_on_enhanced_close'):
            app._on_enhanced_close()
        
        # Root pencereyi kapat
        if root:
            root.quit()
            root.destroy()
            
    except Exception as e:
        logging.warning(f"⚠️ Pencere kapatma hatası: {e}")
        # Zorla çık
        try:
            root.quit()
        except:
            pass

# ===== ULTRA ENHANCED PROGRAM BAŞLANGIÇ NOKTASI =====
if __name__ == "__main__":
    # Başlangıç zamanı
    start_time = time.time()
    
    # ===== ÇALIŞMA DİZİNİ AYARI =====
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)
    
    # Basit loglama başlat (enhanced setup_logger'dan önce)
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(project_root / 'guard_ai_ultra_safe.log', encoding='utf-8')
        ]
    )
    
    logging.info(f"🗂️ Proje kök dizini: {project_root}")
    logging.info(f"🕐 Başlangıç zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ===== ULTRA ENHANCED ANA UYGULAMAYI BAŞLAT =====
    try:
        success = enhanced_main()
        
        # Başarı durumu
        end_time = time.time()
        total_time = end_time - start_time
        
        if success:
            logging.info(f"✅ Guard AI Ultra başarıyla tamamlandı ({total_time:.1f}s)")
            sys.exit(0)
        else:
            logging.error(f"❌ Guard AI Ultra hata ile sonlandı ({total_time:.1f}s)")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Kullanıcı tarafından iptal edildi.")
        logging.info("⚠️ Kullanıcı iptal etti")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        logging.error(f"💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)
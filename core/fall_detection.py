# File: guard_pc_app/core/fall_detection.py
# Açıklama: Düşme algılama için derin öğrenme modelini kullanan modül

import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
import numpy as np
import logging
import os
import time
from config.settings import MODEL_PATH, CONFIDENCE_THRESHOLD
from torchvision import transforms


class FallDetectionModel(nn.Module):
    """PyTorch ile düşme algılama modeli."""
    
    def __init__(self):
        """Model mimarisini başlatır."""
        super(FallDetectionModel, self).__init__()
        
        # Özellik çıkarma katmanları
        self.features = nn.Sequential(
            # İlk konvolüsyon bloğu
            nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # İkinci konvolüsyon bloğu
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Üçüncü konvolüsyon bloğu
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Dördüncü konvolüsyon bloğu
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2)
        )
        
        # Sınıflandırıcı katmanları
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 40 * 30, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 2)  # 2 sınıf: [normal, düşme]
        )
    
    def forward(self, x):
        """İleri yayılım."""
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return F.softmax(x, dim=1)


class FallDetector:
    """Düşme algılama işlemlerini yöneten sınıf."""
    
    def __init__(self):
        """
        Düşme algılama sınıfını başlatır.
        
        Modeli yükler ve çalışmaya hazır hale getirir.
        """
        # Singleton örneği
        if hasattr(FallDetector, '_instance'):
            raise RuntimeError("FallDetector zaten başlatılmış. get_instance() kullanın.")
            
        # Cihazı belirle (CUDA GPU veya CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info(f"Model şu cihazda çalışacak: {self.device}")
        
        # Model oluşturma ve yükleme işlemi
        self.model = None
        self.is_model_loaded = False
        self._load_model()
        
        # Görüntü işleme için transform
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((480, 640)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # İstatistikler ve performans
        self.total_detections = 0
        self.total_inference_time = 0
        self.max_inference_time = 0
        self.min_inference_time = float('inf')
        self.last_log_time = time.time()
        
        # FallDetector sınıfı artık bir singleton
        FallDetector._instance = self
    
    @classmethod
    def get_instance(cls):
        """Singleton örneği döndürür."""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance
    
    def _load_model(self):
        """Model dosyasını yükler."""
        try:
            logging.info(f"Model dosyası yükleniyor: {MODEL_PATH}")
            
            # Model dosyasını kontrol et
            if not os.path.exists(MODEL_PATH):
                logging.error(f"Model dosyası bulunamadı: {MODEL_PATH}")
                return
            
            file_size = os.path.getsize(MODEL_PATH)
            if file_size < 1024:  # 1KB'den küçükse muhtemelen bozuk
                logging.error(f"Model dosyası çok küçük, muhtemelen bozuk: {file_size} bytes")
                return
            
            # Model sınıfını oluştur
            self.model = FallDetectionModel().to(self.device)
            
            # Model dosyasını yükle
            checkpoint = torch.load(MODEL_PATH, map_location=self.device)
            
            # Farklı model formatlarını kontrol et ve yükle
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
                accuracy = checkpoint.get('accuracy', 'Bilinmiyor')
                logging.info(f"Model başarıyla yüklendi. Doğruluk: {accuracy}")
            elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['state_dict'])
                logging.info(f"Model başarıyla yüklendi (state_dict formatı).")
            else:
                self.model.load_state_dict(checkpoint)
                logging.info(f"Model başarıyla yüklendi (tam model formatı).")
            
            # Modeli değerlendirme moduna al
            self.model.eval()
            self.is_model_loaded = True
            logging.info(f"Model başarıyla yüklendi: {MODEL_PATH} (Boyut: {file_size} bytes)")
            
        except Exception as e:
            logging.error(f"Model yüklenirken hata oluştu: {str(e)}", exc_info=True)
            logging.warning("Model yüklenemedi! Düşme algılama devre dışı.")
            self.model = None
            self.is_model_loaded = False
    
    def reload_model(self):
        """Modeli yeniden yükler."""
        logging.info("Model yeniden yükleniyor...")
        self.model = None
        self.is_model_loaded = False
        self._load_model()
        return self.is_model_loaded
    
    def preprocess_frame(self, frame):
        """
        Kamera karesini model için ön işler.
        
        Args:
            frame (numpy.ndarray): OpenCV formatında BGR kare

        Returns:
            torch.Tensor: İşlenmiş tensor veya hata durumunda None
        """
        try:
            # Frame boyutu kontrol
            if frame is None or frame.size == 0:
                logging.warning("Geçersiz kare")
                return None
            
            # Transform nesnesi yoksa oluştur
            if not hasattr(self, 'transform'):
                self.transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Resize((480, 640)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
                
            # Dönüşümleri uygula
            frame_tensor = self.transform(frame).unsqueeze(0).to(self.device)
            return frame_tensor
            
        except Exception as e:
            logging.error(f"Kare ön işleme sırasında hata: {str(e)}")
            return None
    
    def detect_fall(self, frame):
        """
        Düşme algılama işlemini gerçekleştirir.
        
        Args:
            frame (numpy.ndarray): OpenCV formatında BGR kare

        Returns:
            tuple: (is_fall, confidence) - Düşme algılandı mı ve olasılığı
        """
        # Model yüklü değilse çıkış
        if not self.is_model_loaded or self.model is None:
            logging.warning("Model yüklü değil, düşme algılama devre dışı.")
            return False, 0.0
        
        # İstatistikler için düzenli loglama
        now = time.time()
        if now - self.last_log_time > 3600:  # Saatte bir loglama
            if self.total_detections > 0:
                avg_time = self.total_inference_time / self.total_detections
                logging.info(f"Performans istatistikleri: Toplam: {self.total_detections} algılama, "
                           f"Ortalama: {avg_time*1000:.2f}ms, "
                           f"Min: {self.min_inference_time*1000:.2f}ms, "
                           f"Max: {self.max_inference_time*1000:.2f}ms")
                self.total_detections = 0
                self.total_inference_time = 0
                self.max_inference_time = 0
                self.min_inference_time = float('inf')
            self.last_log_time = now
        
        try:
            # Kareyi ön işle
            start_time = time.time()
            frame_tensor = self.preprocess_frame(frame)
            if frame_tensor is None:
                return False, 0.0
            
            # Tahmini yap (gradient hesaplaması olmadan)
            with torch.no_grad():
                output = self.model(frame_tensor)
            
            # Olasılıkları al
            probabilities = output[0].cpu().numpy()
            
            # Düşme olasılığı (ikinci sınıf)
            fall_probability = probabilities[1]
            
            # Eşik değeriyle karşılaştır
            is_fall = fall_probability >= CONFIDENCE_THRESHOLD
            
            # İstatistikleri güncelle
            inference_time = time.time() - start_time
            self.total_detections += 1
            self.total_inference_time += inference_time
            self.max_inference_time = max(self.max_inference_time, inference_time)
            self.min_inference_time = min(self.min_inference_time, inference_time)
            
            return is_fall, fall_probability
            
        except Exception as e:
            logging.error(f"Düşme algılanırken hata oluştu: {str(e)}")
            return False, 0.0
            
    def get_heatmap(self, frame):
        """
        Aktivasyon ısı haritasını oluşturur (sağlık kontrolü için).
        
        Args:
            frame (numpy.ndarray): OpenCV formatında BGR kare

        Returns:
            numpy.ndarray: Isı haritası görüntüsü veya hata durumunda None
        """
        if not self.is_model_loaded or self.model is None:
            return None
            
        try:
            # Kareyi ön işle
            frame_tensor = self.preprocess_frame(frame)
            if frame_tensor is None:
                return None
                
            # İlk konvolüsyon katmanının aktivasyonlarını al
            activations = None
            def hook_fn(module, input, output):
                nonlocal activations
                activations = output.detach()
            
            # Hook ekle
            hook = self.model.features[0].register_forward_hook(hook_fn)
            
            # İleri yayılım
            with torch.no_grad():
                _ = self.model(frame_tensor)
                
            # Hook'u kaldır
            hook.remove()
            
            # Aktivasyonlar yoksa çık
            if activations is None:
                return None
                
            # Aktivasyonları işle
            act = activations.cpu().numpy()[0]
            act = np.mean(act, axis=0)  # Kanal boyunca ortalama al
            
            # Min-max normalizasyonu
            act = (act - act.min()) / (act.max() - act.min() + 1e-8)
            
            # Isı haritasını yeniden boyutlandır
            heatmap = cv2.resize(act, (frame.shape[1], frame.shape[0]))
            
            # Görselleştirme için 0-255 aralığına ölçeklendir ve uint8'e dönüştür
            heatmap = (heatmap * 255).astype(np.uint8)
            
            # Isı haritasını renklendir
            heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
            
            # Orijinal görüntü ile karıştır
            overlaid = cv2.addWeighted(frame, 0.7, heatmap, 0.3, 0)
            
            return overlaid
            
        except Exception as e:
            logging.error(f"Isı haritası oluşturulurken hata: {str(e)}")
            return None
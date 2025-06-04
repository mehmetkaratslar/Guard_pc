import cv2
import numpy as np
import time
import logging
from core.fall_detection import FallDetector
from core.camera import Camera
import matplotlib.pyplot as plt
from collections import deque

class ModelCalibrator:
    """Model kalibrasyon ve test aracı."""
    
    def __init__(self):
        self.detector = FallDetector.get_instance()
        self.camera = Camera.get_instance()
        self.test_results = []
        self.confidence_history = deque(maxlen=100)
        
    def calibrate_threshold(self, duration=60):
        """Optimal güven eşiğini bulmak için kalibrasyon yapar."""
        logging.info(f"{duration} saniyelik kalibrasyon başlatılıyor...")
        
        if not self.camera.start():
            logging.error("Kamera başlatılamadı")
            return
        
        start_time = time.time()
        detections = []
        
        print("\nKalibrasyon başladı!")
        print("Lütfen normal aktivitelerinizi yapın (oturma, ayağa kalkma, yürüme)")
        print("Gerçek düşme simülasyonu YAPMAYIN!\n")
        
        while time.time() - start_time < duration:
            frame = self.camera.get_frame()
            if frame is None:
                continue
            
            # Düşme algılama (tek kare)
            results = self.detector.model.predict(frame, conf=0.3, verbose=False)
            
            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls = int(box.cls.item())
                        conf = float(box.conf.item())
                        
                        if cls == 1:  # Düşme sınıfı
                            detections.append(conf)
                            self.confidence_history.append(conf)
                            print(f"Algılama: Güven={conf:.3f}")
            
            # İlerleme göstergesi
            elapsed = time.time() - start_time
            progress = int((elapsed / duration) * 50)
            print(f"\rİlerleme: [{'=' * progress}{' ' * (50 - progress)}] {elapsed:.1f}/{duration}s", end='')
            
            time.sleep(0.1)
        
        self.camera.stop()
        print("\n\nKalibrasyon tamamlandı!")
        
        # Analiz
        if detections:
            detections = np.array(detections)
            
            # İstatistikler
            mean_conf = np.mean(detections)
            std_conf = np.std(detections)
            percentiles = np.percentile(detections, [50, 75, 90, 95, 99])
            
            print(f"\n--- Kalibrasyon Sonuçları ---")
            print(f"Toplam algılama sayısı: {len(detections)}")
            print(f"Ortalama güven: {mean_conf:.3f}")
            print(f"Standart sapma: {std_conf:.3f}")
            print(f"Medyan: {percentiles[0]:.3f}")
            print(f"75. percentil: {percentiles[1]:.3f}")
            print(f"90. percentil: {percentiles[2]:.3f}")
            print(f"95. percentil: {percentiles[3]:.3f}")
            print(f"99. percentil: {percentiles[4]:.3f}")
            
            # Önerilen eşik: 95. veya 99. percentil
            suggested_threshold = percentiles[3]  # 95. percentil
            
            print(f"\n--- Öneriler ---")
            print(f"Önerilen güven eşiği: {suggested_threshold:.3f}")
            print(f"Güvenli eşik (daha az yanlış pozitif): {percentiles[4]:.3f}")
            print(f"Hassas eşik (daha fazla algılama): {percentiles[2]:.3f}")
            
            # Grafik çiz
            self._plot_calibration_results(detections, suggested_threshold)
            
            return suggested_threshold
        else:
            print("\nKalibrasyon sırasında hiç algılama yapılmadı!")
            print("Model düzgün yüklenmemiş olabilir veya eşik çok yüksek.")
            return None
    
    def _plot_calibration_results(self, detections, suggested_threshold):
        """Kalibrasyon sonuçlarını görselleştirir."""
        plt.figure(figsize=(12, 6))
        
        # Histogram
        plt.subplot(1, 2, 1)
        plt.hist(detections, bins=30, alpha=0.7, color='blue', edgecolor='black')
        plt.axvline(suggested_threshold, color='red', linestyle='--', linewidth=2, label=f'Önerilen Eşik: {suggested_threshold:.3f}')
        plt.xlabel('Güven Değeri')
        plt.ylabel('Frekans')
        plt.title('Güven Değeri Dağılımı')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Zaman serisi
        plt.subplot(1, 2, 2)
        if len(self.confidence_history) > 0:
            plt.plot(list(self.confidence_history), 'b-', alpha=0.7)
            plt.axhline(suggested_threshold, color='red', linestyle='--', linewidth=2, label=f'Önerilen Eşik: {suggested_threshold:.3f}')
            plt.xlabel('Zaman (frame)')
            plt.ylabel('Güven Değeri')
            plt.title('Güven Değeri Zaman Serisi')
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('calibration_results.png')
        plt.show()
        print("\nGrafik 'calibration_results.png' olarak kaydedildi.")
    
    def test_with_video(self, video_path, ground_truth_falls=None):
        """Video üzerinde model performansını test eder."""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logging.error(f"Video açılamadı: {video_path}")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"\nVideo testi başlatılıyor...")
        print(f"FPS: {fps}, Toplam kare: {total_frames}")
        
        detections = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Düşme algılama
            is_fall, confidence = self.detector.detect_fall(frame)
            
            if is_fall:
                timestamp = frame_count / fps
                detections.append({
                    'frame': frame_count,
                    'timestamp': timestamp,
                    'confidence': confidence
                })
                print(f"Düşme algılandı! Kare: {frame_count}, Zaman: {timestamp:.2f}s, Güven: {confidence:.3f}")
            
            # İlerleme
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"\rİlerleme: {progress:.1f}%", end='')
        
        cap.release()
        print("\n\nTest tamamlandı!")
        
        # Sonuçları analiz et
        if ground_truth_falls:
            self._evaluate_performance(detections, ground_truth_falls)
        
        return detections
    
    def _evaluate_performance(self, detections, ground_truth):
        """Model performansını değerlendirir."""
        # Basit bir değerlendirme örneği
        # ground_truth: [(start_time, end_time), ...] formatında
        
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        # Her algılama için kontrol et
        for det in detections:
            det_time = det['timestamp']
            is_correct = False
            
            for gt_start, gt_end in ground_truth:
                if gt_start <= det_time <= gt_end:
                    is_correct = True
                    break
            
            if is_correct:
                true_positives += 1
            else:
                false_positives += 1
        
        # Kaçırılan düşmeleri hesapla
        for gt_start, gt_end in ground_truth:
            detected = False
            for det in detections:
                if gt_start <= det['timestamp'] <= gt_end:
                    detected = True
                    break
            if not detected:
                false_negatives += 1
        
        # Metrikleri hesapla
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\n--- Performans Metrikleri ---")
        print(f"Doğru Pozitif: {true_positives}")
        print(f"Yanlış Pozitif: {false_positives}")
        print(f"Yanlış Negatif: {false_negatives}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"F1 Score: {f1_score:.3f}")
        
        return {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score
        }

# Kullanım örneği
if __name__ == "__main__":
    calibrator = ModelCalibrator()
    
    # Kalibrasyon yap
    suggested_threshold = calibrator.calibrate_threshold(duration=60)
    
    if suggested_threshold:
        print(f"\nconfig/settings.py dosyasında CONFIDENCE_THRESHOLD değerini {suggested_threshold:.3f} olarak güncelleyin.")
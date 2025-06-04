# test_model.py
import cv2
from ultralytics import YOLO
import numpy as np
import os

# Model yükle
model_path = "resources/models/S.pt"
print(f"Model yükleniyor: {model_path}")
print(f"Model boyutu: {os.path.getsize(model_path) / (1024*1024):.2f} MB")

model = YOLO(model_path)

# Model bilgilerini göster
print(f"\nModel Sınıfları:")
if hasattr(model, 'names'):
    for idx, name in model.names.items():
        print(f"  {idx}: {name}")
else:
    print("  Model sınıf isimleri bulunamadı!")

# Kamera aç
print("\nKamera açılıyor...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Kamera açılamadı!")
    exit()

print("Düşme tespiti başladı. Çıkmak için 'q' tuşuna basın.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame alınamadı!")
        break
    
    # Tespit yap
    results = model(frame, conf=0.3)  # Düşük confidence ile test
    
    # Sonuçları işle
    fall_detected = False
    max_confidence = 0.0
    
    for r in results:
        if r.boxes is not None:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names[cls]
                
                if 'fall' in class_name.lower():
                    fall_detected = True
                    max_confidence = max(max_confidence, conf)
                    
                    # Koordinatları al
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    print(f"✅ DÜŞME TESPİTİ: {class_name} - Güven: {conf:.3f} - Konum: ({int(x1)},{int(y1)})")
    
    # Görselleştir
    annotated = results[0].plot()
    
    # Durum bilgisi ekle
    status_color = (0, 0, 255) if fall_detected else (0, 255, 0)
    status_text = f"DUSME ALGILANDI! ({max_confidence:.2f})" if fall_detected else "Normal"
    cv2.putText(annotated, status_text, (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    
    cv2.imshow("YOLOv11 Dusme Tespiti", annotated)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\nTest tamamlandı!")
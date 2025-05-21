import os
import shutil
from ultralytics import YOLO

# 1) Dizinleri tanımla
PROJECT_DIR = os.getcwd()  # Ana proje dizinin
DATASET_YAML = os.path.join(PROJECT_DIR, "data", "Fall_Detection.v4i.yolov11", "data.yaml")
MODEL_OUTPUT_DIR = os.path.join(PROJECT_DIR, "runs", "detect", "train", "weights")
MODEL_OUTPUT_FILE = os.path.join(MODEL_OUTPUT_DIR, "best.pt")
TARGET_MODEL_PATH = os.path.join(PROJECT_DIR, "resources", "models", "fall_model.pt")

# 2) YOLOv11 Large modeliyle eğitimi başlat
print(f"YOLO eğitim başlıyor: {DATASET_YAML}")
model = YOLO("yolo11l.pt")  # Veya daha hafif bir model istiyorsan: yolo11n.pt, yolo11s.pt

model.train(
    data=DATASET_YAML,  # data.yaml yolun
    epochs=25,          # Kaç epoch istiyorsan artırabilirsin
    imgsz=640,          # Görüntü boyutu
    project="runs",     # Çıktı klasörü
    name="detect/train",# Alt klasör
    plots=True          # Eğitim grafikleri oluşturulsun mu
)

# 3) Eğitilen modeli hedef klasöre taşı
if os.path.exists(MODEL_OUTPUT_FILE):
    shutil.copy(MODEL_OUTPUT_FILE, TARGET_MODEL_PATH)
    print(f"Eğitilen model {TARGET_MODEL_PATH} dosyasına başarıyla kaydedildi.")
else:
    print("HATA: Eğitim sonrası model bulunamadı!")

# 4) (İsteğe bağlı) Model ile bir test resmi üzerinde inference yapabilirsin
"""
from PIL import Image
test_image_path = os.path.join(PROJECT_DIR, "data", "Fall_Detection.v4i.yolov11", "test", "images", os.listdir(os.path.join(PROJECT_DIR, "data", "Fall_Detection.v4i.yolov11", "test", "images"))[0])
image = Image.open(test_image_path)
results = model.predict(image)
results[0].show()  # Sonucu gösterir
"""

# 5) (İsteğe bağlı) Eğitimi tamamlayan grafikleri görmek istersen:
RESULTS_PNG = os.path.join(PROJECT_DIR, "runs", "detect", "train", "results.png")
if os.path.exists(RESULTS_PNG):
    print("Eğitim sonucu grafik kaydedildi:", RESULTS_PNG)
else:
    print("Eğitim sonucu grafik bulunamadı.")

# Dockerfile for Guard PC App
FROM python:3.10-slim

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini oluştur
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Gerekli dizinleri oluştur
RUN mkdir -p logs resources/models resources/icons

# Portları expose et
EXPOSE 5000

# Çevre değişkenleri
ENV PYTHONPATH=/app
ENV DISPLAY=:99

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1

# Uygulama başlatma komutu
CMD ["python", "main.py"]
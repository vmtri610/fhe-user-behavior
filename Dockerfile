# 1. Sử dụng image Python chính thức (3.10+ để tương thích với FastAPI mới)
FROM python:3.10-slim

# 2. Thiết lập thư mục làm việc
WORKDIR /app

# 3. Cài đặt các thư viện hệ thống cần thiết (nếu có)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libprotobuf-dev protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy và cài đặt requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code vào /backend
# Theo cấu trúc của bạn: /backend/app/main.py, ...
COPY . .

# 6. (Bỏ qua - Models sẽ được Job lấy trực tiếp từ GCS)

# 7. Expose cổng 30000 (khớp với service.yaml của bạn)
EXPOSE 30000

# 8. Lệnh chạy ứng dụng (giả sử dùng uvicorn)
CMD ["uvicorn", "backend.app.server.main:app", "--host", "0.0.0.0", "--port", "30000"]
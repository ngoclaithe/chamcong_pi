# 📋 IMPLEMENTATION PLAN - Face Recognition Attendance System
# Raspberry Pi 5 | Flask Monolith

---

## 1. Tổng quan kiến trúc

Sử dụng **Flask monolith** (backend + frontend trong 1 process) thay vì tách riêng FastAPI + Next.js để **tiết kiệm RAM** cho Raspberry Pi 5.

```
Raspberry Pi 5
 ├── Camera Module (USB/CSI)
 ├── Flask Server (Backend + Jinja2 Templates)
 │    ├── Routes (API + Pages)
 │    ├── AI Model (MobileFaceNet + Classifier)
 │    ├── Services (Face Detection, Embedding, Training, Attendance)
 │    └── SQLite DB
 └── Static Assets (CSS, JS)
```

---

## 2. Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Web Framework | Flask + Jinja2 |
| Frontend | Jinja2 Templates + Vanilla JS + Vanilla CSS |
| AI/CV | PyTorch (MobileFaceNet), OpenCV |
| Database | SQLite (via Flask-SQLAlchemy) |
| Camera | OpenCV VideoCapture |
| Task Queue | Threading (built-in Python) |

---

## 3. Cấu trúc thư mục

```
chamcong_pi/
├── app.py                     # Flask app entry point
├── config.py                  # Cấu hình (DB, camera, model paths)
├── requirements.txt
│
├── models/                    # Database models
│   ├── __init__.py
│   ├── user.py                # User model
│   ├── embedding.py           # Embedding model
│   └── attendance.py          # Attendance model
│
├── services/                  # Business logic
│   ├── __init__.py
│   ├── camera_service.py      # Camera capture + streaming
│   ├── face_detection.py      # Detect faces (OpenCV DNN / Haar)
│   ├── face_embedding.py      # MobileFaceNet embedding (128-dim)
│   ├── classifier.py          # Linear classifier (128 → num_users)
│   ├── training_service.py    # Train classifier on Pi
│   ├── recognition_service.py # Nhận diện khuôn mặt
│   └── attendance_service.py  # Ghi log chấm công
│
├── routes/                    # Flask routes
│   ├── __init__.py
│   ├── main_routes.py         # Dashboard, pages
│   ├── user_routes.py         # CRUD users
│   ├── training_routes.py     # Train model
│   ├── recognition_routes.py  # Recognition API
│   └── attendance_routes.py   # Attendance logs
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Layout chung (navbar, footer)
│   ├── dashboard.html         # Trang chính
│   ├── users.html             # Quản lý user
│   ├── user_register.html     # Đăng ký user + capture face
│   ├── training.html          # Panel training
│   ├── attendance.html        # Bảng chấm công
│   └── recognition.html       # Trang nhận diện live
│
├── static/                    # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── camera.js          # Camera capture logic
│   │   ├── training.js        # Training progress polling
│   │   └── recognition.js     # Live recognition
│   └── img/
│
└── data/                      # Runtime data
    ├── faces/                 # Ảnh khuôn mặt đã capture
    ├── classifier.pth         # Trained classifier weights
    └── mobilefacenet.pth      # Pretrained embedding model
```

---

## 4. Database Schema (SQLite)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    employee_code TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    embedding BLOB NOT NULL,          -- 128-dim vector (numpy tobytes)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 5. Triển khai chi tiết từng module

### 5.1 `app.py` - Entry Point

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)

    from routes.main_routes import main_bp
    from routes.user_routes import user_bp
    from routes.training_routes import training_bp
    from routes.recognition_routes import recognition_bp
    from routes.attendance_routes import attendance_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(training_bp, url_prefix='/training')
    app.register_blueprint(recognition_bp, url_prefix='/recognition')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
```

### 5.2 Camera Service

- **OpenCV VideoCapture** với thread riêng
- **MJPEG streaming** qua Flask route `/video_feed`
- Resolution: **640x480**

```python
def generate_frames():
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while True:
        success, frame = camera.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
               + buffer.tobytes() + b'\r\n')

@main_bp.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
```

### 5.3 Face Detection
- **OpenCV DNN** (SSD MobileNet) hoặc **Haar Cascade**
- Input: frame BGR → Output: list bounding boxes

### 5.4 Face Embedding (MobileFaceNet)
- Pretrained model → output **128-dim vector** (normalized)
- Convert sang **TorchScript** để tối ưu inference

### 5.5 Classifier
- **Linear(128 → num_users)** — rất nhẹ, train nhanh
- Weights tại `data/classifier.pth`

### 5.6 Training Service
- Chạy trong **background thread** (không block Flask)
- Progress qua global dict → frontend poll AJAX
- Config: **3-5 epochs, batch 16, Adam, CrossEntropy**
- Thời gian: ~1-2 phút trên Pi 5

### 5.7 Recognition Service
- Pipeline: **Detect → Crop → Embed → Classify → Threshold**
- Confidence threshold: **0.7** (configurable)
- Anti-duplicate: không log cùng user trong **5 phút**

### 5.8 Attendance Service
- Log: `user_id + timestamp + confidence`
- Filter theo ngày/tuần/tháng + Export CSV

---

## 6. Routes & Pages

| Route | Method | Mô tả |
|-------|--------|--------|
| `/` | GET | Dashboard |
| `/video_feed` | GET | MJPEG camera stream |
| `/users` | GET | Danh sách users |
| `/users/register` | GET/POST | Đăng ký nhân viên + capture face |
| `/users/<id>/delete` | POST | Xóa user |
| `/training` | GET | Training panel |
| `/training/start` | POST | Bắt đầu train (AJAX) |
| `/training/status` | GET | Training progress (JSON) |
| `/recognition` | GET | Nhận diện live |
| `/recognition/detect` | POST | Nhận diện 1 frame (AJAX) |
| `/attendance` | GET | Bảng chấm công |
| `/attendance/export` | GET | Export CSV |

---

## 7. UI Flow

### Đăng ký User
```
/users/register → Nhập tên + mã NV → Camera capture 10-20 ảnh
→ Server: detect → crop → embed → save DB → (Optional) auto train
```

### Training
```
/training → Click "Start" → Background thread train
→ Frontend poll /training/status mỗi 2s → Progress bar → Done
```

### Nhận diện & Chấm công
```
/recognition → Live camera feed → Mỗi frame: detect → embed → classify
→ confidence > 0.7 → log attendance → UI hiện tên + box
```

---

## 8. Tối ưu RAM cho Pi 5

| Kỹ thuật | Chi tiết |
|----------|----------|
| Flask monolith | 1 process (~150-200MB RAM) |
| TorchScript | Model compile sẵn, inference nhanh |
| Camera threading | Thread riêng, không block server |
| Resolution 640x480 | Giảm tải xử lý |
| SQLite | Không cần DB server riêng |
| Lazy model loading | Load model khi cần |

### RAM Estimate

| Component | RAM |
|-----------|-----|
| Flask + Python | ~80 MB |
| MobileFaceNet | ~5 MB |
| Classifier | < 1 MB |
| OpenCV + Camera | ~50 MB |
| SQLite | ~10 MB |
| **Tổng** | **~150-200 MB** |

> Pi 5 (4-8GB) → dư sức. So với Next.js + FastAPI riêng: ~500-800MB.

---

## 9. Dependencies (`requirements.txt`)

```
flask==3.1.0
flask-sqlalchemy==3.1.1
torch==2.1.0
torchvision==0.16.0
opencv-python-headless==4.9.0.80
numpy==1.26.4
Pillow==10.2.0
```

> Cài PyTorch ARM64 cho Pi 5 từ wheel riêng hoặc build từ source.

---

## 10. Thứ tự triển khai

### Phase 1: Foundation (Steps 1-4)
1. Flask app + config + SQLite setup
2. Database models (User, Embedding, Attendance)
3. `base.html` template + CSS dark theme
4. Camera service (MJPEG streaming)

### Phase 2: User Management (Steps 5-9)
5. CRUD Users (routes + templates)
6. Camera capture trên browser (JS)
7. Face detection service (OpenCV)
8. Face embedding service (MobileFaceNet)
9. Trang đăng ký user + face capture flow

### Phase 3: Training & Recognition (Steps 10-14)
10. Classifier module (Linear layer)
11. Training service (background thread + progress)
12. Training page + progress bar
13. Recognition service (full pipeline)
14. Recognition page (live feed + nhận diện)

### Phase 4: Attendance & Polish (Steps 15-20)
15. Attendance logging service
16. Attendance page (table + filter + export)
17. Dashboard page (stats + live feed)
18. UI polish, responsive, animations
19. Testing trên Raspberry Pi 5
20. Performance tuning

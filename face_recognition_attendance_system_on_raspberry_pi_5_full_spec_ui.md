# 🎯 FACE RECOGNITION ATTENDANCE SYSTEM (Raspberry Pi 5)

---

# 1. Overview

## Goal
Build a real-time face recognition attendance system that:
- Runs on Raspberry Pi 5
- Supports adding new users
- Supports fast training (~1–2 minutes)
- Includes full UI for management and monitoring

---

# 2. System Architecture

```
Camera → Face Detection → Embedding Model → Classifier (FC)
→ Recognition → Attendance Logging → UI Dashboard
```

---

# 3. Tech Stack

## AI / CV
- PyTorch
- MobileFaceNet (or MobileNetV2)
- OpenCV

## Backend
- FastAPI

## Frontend
- Next.js (or React)
- TailwindCSS

## Database
- SQLite (on Raspberry Pi)

---

# 4. Core Modules

## 4.1 Face Detection
- Input: camera frame
- Output: face bounding box

## 4.2 Face Embedding
- Output: 128-dim vector

## 4.3 Classifier (Trainable on Pi)
- Linear Layer: 128 → num_users

## 4.4 Attendance Service
- Logs user_id + timestamp

---

# 5. Data Flow

## Register User
```
Capture Images → Extract Embedding → Save → Train Classifier
```

## Recognition
```
Camera → Detect → Embedding → Classifier → User ID → Log
```

---

# 6. Database Design

## users
- id
- name
- student_code

## embeddings
- user_id
- embedding (vector)

## attendance
- id
- user_id
- timestamp

---

# 7. API Specification

## POST /register
- Upload images
- Save user + embeddings

## POST /train
- Train classifier (~1–2 minutes)

## POST /recognize
- Return user_id

## GET /attendance
- Get logs

---

# 8. Training Specification (Fast Training)

## Input
- X: embeddings (N x 128)
- y: labels

## Model
```
Linear(128 → num_classes)
```

## Config
- Epochs: 3–5
- Batch size: 16
- Optimizer: Adam
- Loss: CrossEntropy

## Time
- ~1–2 minutes on Raspberry Pi

---

# 9. UI Design

## 9.1 Dashboard
- Total users
- Attendance today
- Live camera feed

## 9.2 User Management
- Add user
- Capture face
- View user list

## 9.3 Training Panel
- Train button
- Training status (progress bar)

## 9.4 Attendance Table
- User name
- Time
- Date

---

# 10. UI Flow

## Add User
```
Click Add → Open Camera → Capture 10–20 images → Submit
→ Extract Embedding → Save → Train Model
```

## Attendance
```
Open Camera → Detect → Recognize → Log → Update UI
```

---

# 11. Performance Optimization

- Use lightweight model
- Reduce camera resolution (640x480)
- Precompute embeddings
- Use threading for camera + inference

---

# 12. Deployment Architecture

```
Raspberry Pi 5
 ├── Camera Module
 ├── AI Model (TorchScript)
 ├── FastAPI Server
 ├── SQLite DB
 └── Frontend UI (Next.js)
```

---

# 13. Project Structure

```
project/
 ├── backend/
 │    ├── main.py
 │    ├── model/
 │    ├── services/
 │    └── training/
 ├── frontend/
 │    ├── pages/
 │    ├── components/
 │    └── services/
 └── data/
```

---

# 14. Features

## Core
- Face recognition
- Attendance logging
- Add new user
- Train on device

## Advanced
- Real-time UI
- Training progress
- Duplicate detection

---

# 15. Evaluation Criteria

- Accuracy
- Training speed
- Real-time performance
- UI usability

---

# 16. Conclusion

System ensures:
- Fast training (~1–2 min)
- Real-time recognition
- Full-stack implementation
- Suitable for Raspberry Pi deployment


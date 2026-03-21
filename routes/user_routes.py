import os
import uuid
import shutil
import cv2
import numpy as np
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from extensions import db
from models.user import User
from models.embedding import Embedding
from services.face_detection import face_detector
from services.face_embedding import get_embedding_service
from services.camera_service import camera_service

user_bp = Blueprint('users', __name__)


@user_bp.route('/')
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if camera_service.is_running:
            camera_service.stop()
        session_id = str(uuid.uuid4())
        next_code = User.generate_employee_code()
        return render_template('user_register.html', session_id=session_id, employee_code=next_code)

    name = request.form.get('name', '').strip()
    session_id = request.form.get('session_id', '').strip()
    employee_code = User.generate_employee_code()

    if not name:
        flash('Vui long nhap ho ten nhan vien.', 'error')
        return redirect(url_for('users.register'))

    temp_dir = os.path.join(current_app.config['DATA_DIR'], 'temp', session_id)
    if not os.path.exists(temp_dir):
        flash('Chua chup anh nao.', 'error')
        return redirect(url_for('users.register'))

    image_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
    if len(image_files) < 1:
        flash('Can it nhat 1 anh khuon mat.', 'error')
        return render_template('user_register.html', session_id=session_id)

    user = User(name=name, employee_code=employee_code)
    db.session.add(user)
    db.session.flush()

    embedding_service = get_embedding_service()
    faces_dir = os.path.join(current_app.config['FACES_DIR'], str(user.id))
    os.makedirs(faces_dir, exist_ok=True)

    embedding_count = 0
    for i, img_file in enumerate(image_files):
        try:
            frame = cv2.imread(os.path.join(temp_dir, img_file))
            if frame is None:
                continue
            faces = face_detector.detect(frame)
            if not faces:
                continue

            largest = max(faces, key=lambda f: f['bbox'][2] * f['bbox'][3])
            face_img = face_detector.crop_face(frame, largest['bbox'])
            if face_img is None:
                continue

            cv2.imwrite(os.path.join(faces_dir, f'face_{i}.jpg'), face_img)

            landmarks = largest.get('landmarks')
            if landmarks is not None:
                vector = embedding_service.get_embedding(face_img=None, landmarks=landmarks, frame=frame)
            else:
                vector = embedding_service.get_embedding(face_img)

            emb = Embedding(user_id=user.id)
            emb.set_vector(vector)
            db.session.add(emb)
            embedding_count += 1
        except Exception as e:
            print(f"Error processing {img_file}: {e}")
            continue

    shutil.rmtree(temp_dir, ignore_errors=True)

    if embedding_count == 0:
        db.session.rollback()
        flash('Khong phat hien duoc khuon mat. Vui long thu lai.', 'error')
        return redirect(url_for('users.register'))

    db.session.commit()

    from services.recognition_service import get_recognition_service
    recognition = get_recognition_service()
    if recognition:
        recognition.reload_embeddings()

    flash(f'Da dang ky {name} voi {embedding_count} anh khuon mat!', 'success')
    return redirect(url_for('users.user_list'))


@user_bp.route('/upload_face', methods=['POST'])
def upload_face():
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'message': 'Missing session_id'}), 400
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file'}), 400

    file = request.files['image']
    temp_dir = os.path.join(current_app.config['DATA_DIR'], 'temp', session_id)
    os.makedirs(temp_dir, exist_ok=True)

    existing = len([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
    filepath = os.path.join(temp_dir, f'face_{existing:03d}.jpg')
    file.save(filepath)

    frame = cv2.imread(filepath)
    if frame is None:
        os.remove(filepath)
        return jsonify({'success': False, 'message': 'Invalid image', 'count': existing})

    faces = face_detector.detect(frame)
    if not faces:
        os.remove(filepath)
        return jsonify({'success': False, 'message': 'Khong phat hien khuon mat', 'count': existing})

    return jsonify({'success': True, 'count': existing + 1, 'message': 'OK'})


@user_bp.route('/delete_face', methods=['POST'])
def delete_face():
    session_id = request.form.get('session_id')
    index = request.form.get('index', type=int)
    if not session_id or index is None:
        return jsonify({'success': False, 'message': 'Missing params'}), 400

    temp_dir = os.path.join(current_app.config['DATA_DIR'], 'temp', session_id)
    filepath = os.path.join(temp_dir, f'face_{index:03d}.jpg')
    if os.path.exists(filepath):
        os.remove(filepath)

    remaining = sorted([f for f in os.listdir(temp_dir) if f.endswith('.jpg')])
    for i, fname in enumerate(remaining):
        old_path = os.path.join(temp_dir, fname)
        new_path = os.path.join(temp_dir, f'face_{i:03d}.jpg')
        if old_path != new_path:
            os.rename(old_path, new_path)

    return jsonify({'success': True, 'count': len(remaining)})


@user_bp.route('/<int:user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_detail.html', user=user)


@user_bp.route('/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    faces_dir = os.path.join(current_app.config['FACES_DIR'], str(user.id))
    if os.path.exists(faces_dir):
        shutil.rmtree(faces_dir)

    db.session.delete(user)
    db.session.commit()

    from services.recognition_service import get_recognition_service
    recognition = get_recognition_service()
    if recognition:
        recognition.reload_embeddings()

    flash(f'Da xoa nhan vien {user.name}.', 'success')
    return redirect(url_for('users.user_list'))


@user_bp.route('/<int:user_id>/update', methods=['POST'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.is_json:
        data = request.get_json()
        new_name = data.get('name', '').strip()
    else:
        new_name = request.form.get('name', '').strip()

    if not new_name:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Ten khong duoc de trong.'}), 400
        flash('Ten khong duoc de trong.', 'error')
        return redirect(url_for('users.user_list'))

    user.name = new_name
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'message': f'Da cap nhat ten thanh {new_name}.'})

    flash(f'Da cap nhat thong tin {new_name}.', 'success')
    return redirect(url_for('users.user_list'))

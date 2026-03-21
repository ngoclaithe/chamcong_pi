import os
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, Response, jsonify, redirect, url_for, flash, current_app
from services.attendance_service import attendance_service

attendance_bp = Blueprint('attendance', __name__)

PER_PAGE = 20


@attendance_bp.route('/')
def attendance_page():
    filter_date = request.args.get('date')
    filter_from = request.args.get('from')
    filter_to = request.args.get('to')
    page = request.args.get('page', 1, type=int)

    if filter_from and filter_to:
        start = datetime.strptime(filter_from, '%Y-%m-%d').date()
        end = datetime.strptime(filter_to, '%Y-%m-%d').date()
        all_records = attendance_service.get_by_range(start, end)
        title = f"Cham cong tu {filter_from} den {filter_to}"
    elif filter_date:
        target = datetime.strptime(filter_date, '%Y-%m-%d').date()
        all_records = attendance_service.get_by_date(target)
        title = f"Cham cong ngay {filter_date}"
    else:
        all_records = attendance_service.get_today()
        title = f"Cham cong hom nay ({date.today().strftime('%d/%m/%Y')})"

    total = len(all_records)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    records = all_records[(page - 1) * PER_PAGE : page * PER_PAGE]
    start_index = (page - 1) * PER_PAGE

    return render_template('attendance.html',
                           records=records, title=title, today=date.today().isoformat(),
                           page=page, total_pages=total_pages, total=total, start_index=start_index)


@attendance_bp.route('/export')
def export():
    filter_date = request.args.get('date')
    filter_from = request.args.get('from')
    filter_to = request.args.get('to')

    if filter_from and filter_to:
        start = datetime.strptime(filter_from, '%Y-%m-%d').date()
        end = datetime.strptime(filter_to, '%Y-%m-%d').date()
        records = attendance_service.get_by_range(start, end)
    elif filter_date:
        target = datetime.strptime(filter_date, '%Y-%m-%d').date()
        records = attendance_service.get_by_date(target)
    else:
        records = attendance_service.get_today()

    csv_content = attendance_service.export_csv(records)
    return Response(csv_content, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=attendance_{date.today()}.csv'})


@attendance_bp.route('/<int:record_id>/delete', methods=['POST'])
def delete_record(record_id):
    data_dir = current_app.config.get('DATA_DIR')
    success, msg = attendance_service.delete_record(record_id, data_dir)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': msg})
    flash('Da xoa ban ghi cham cong.' if success else msg, 'success' if success else 'error')
    return redirect(url_for('attendance.attendance_page'))


@attendance_bp.route('/delete_all', methods=['POST'])
def delete_all():
    data_dir = current_app.config.get('DATA_DIR')
    success, count = attendance_service.delete_all(data_dir)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': f'Da xoa {count} ban ghi.'})
    flash(f'Da xoa {count} ban ghi cham cong.', 'success')
    return redirect(url_for('attendance.attendance_page'))

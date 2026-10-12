from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from app.blueprints.schedule import schedule_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, role_required, get_current_user

DAYS_OF_WEEK = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
}

@schedule_bp.route('/availability', methods=['GET', 'POST'])
@role_required('MENTOR')
def manage_availability():
    """Mentor manages weekly recurring availability blocks (Member 4 table)."""
    user = get_current_user()
    mentor_id = user['id']

    if request.method == 'POST':
        day_of_week = request.form.get('day_of_week', type=int)
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if day_of_week is None or not start_time or not end_time:
            flash("All fields are required.", "danger")
        elif end_time <= start_time:
            flash("End time must be after start time.", "warning")
        else:
            insert_sql = """
                INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
            """
            execute_query(insert_sql, (mentor_id, day_of_week, start_time, end_time))
            flash("Availability slot added successfully!", "success")
            return redirect(url_for('schedule.manage_availability'))

    # Fetch existing availability
    avail_sql = """
        SELECT id, day_of_week, start_time, end_time, is_active
        FROM mentor_availability
        WHERE mentor_id = %s
        ORDER BY day_of_week, start_time
    """
    slots = fetch_all(avail_sql, (mentor_id,))
    return render_template('schedule/availability.html', slots=slots, days=DAYS_OF_WEEK)

@schedule_bp.route('/availability/delete/<int:slot_id>', methods=['POST'])
@role_required('MENTOR')
def delete_availability(slot_id):
    user = get_current_user()
    execute_query("DELETE FROM mentor_availability WHERE id = %s AND mentor_id = %s", (slot_id, user['id']))
    flash("Availability slot removed.", "info")
    return redirect(url_for('schedule.manage_availability'))

@schedule_bp.route('/relations/<int:relation_id>/meetings/book', methods=['GET', 'POST'])
@login_required
def book_meeting(relation_id):
    """Book a new session under an active relationship (Member 5 table: meetings)."""
    user = get_current_user()
    user_id = user['id']

    # Fetch relation
    rel_sql = """
        SELECT mr.id, mr.mentee_id, mr.mentor_id, mr.status,
               mentor.first_name AS mentor_first, mentor.last_name AS mentor_last,
               mentee.first_name AS mentee_first, mentee.last_name AS mentee_last
        FROM mentorship_relations mr
        JOIN users mentor ON mr.mentor_id = mentor.id
        JOIN users mentee ON mr.mentee_id = mentee.id
        WHERE mr.id = %s
    """
    rel = fetch_one(rel_sql, (relation_id,))
    if not rel or rel['status'] != 'ACTIVE':
        flash("Can only book meetings for active mentorships.", "warning")
        return redirect(url_for('relations.list_relations'))

    if user['role'] != 'ADMIN' and user_id not in (rel['mentee_id'], rel['mentor_id']):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    if request.method == 'POST':
        start_str = request.form.get('scheduled_start')
        end_str = request.form.get('scheduled_end')
        agenda = request.form.get('agenda', '').strip()
        meeting_link = request.form.get('meeting_link', '').strip() or 'https://meet.jit.si/mentor-session'

        try:
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
        except (ValueError, TypeError):
            flash("Invalid date and time format.", "danger")
            return redirect(url_for('schedule.book_meeting', relation_id=relation_id))

        if end_dt <= start_dt:
            flash("Meeting end time must be after start time.", "warning")
            return redirect(url_for('schedule.book_meeting', relation_id=relation_id))

        # Check for overlapping meetings for this mentor
        overlap_sql = """
            SELECT m.id 
            FROM meetings m
            JOIN mentorship_relations mr ON m.relation_id = mr.id
            WHERE mr.mentor_id = %s AND m.status = 'SCHEDULED'
              AND (
                  (m.scheduled_start < %s AND m.scheduled_end > %s)
              )
        """
        overlap = fetch_one(overlap_sql, (rel['mentor_id'], end_dt, start_dt))
        if overlap:
            flash("The mentor already has a scheduled meeting during this exact time slot. Please pick another time.", "warning")
            return redirect(url_for('schedule.book_meeting', relation_id=relation_id))

        # Insert meeting using raw SQL
        insert_meeting_sql = """
            INSERT INTO meetings (relation_id, scheduled_start, scheduled_end, meeting_link, agenda, status)
            VALUES (%s, %s, %s, %s, %s, 'SCHEDULED')
        """
        execute_query(insert_meeting_sql, (relation_id, start_dt, end_dt, meeting_link, agenda))

        # Notify the other party
        target_notify_id = rel['mentee_id'] if user_id == rel['mentor_id'] else rel['mentor_id']
        notif_msg = f"A new mentorship session has been scheduled for {start_dt.strftime('%B %d, %Y at %H:%M')}."
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)", (target_notify_id, "Meeting Scheduled", notif_msg))

        flash("Meeting successfully scheduled!", "success")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    # Fetch mentor's active availability windows to display as reference
    avail_sql = "SELECT day_of_week, start_time, end_time FROM mentor_availability WHERE mentor_id = %s AND is_active = TRUE ORDER BY day_of_week"
    avail = fetch_all(avail_sql, (rel['mentor_id'],))

    return render_template('schedule/book.html', rel=rel, availability=avail, days=DAYS_OF_WEEK)

@schedule_bp.route('/meetings/<int:meeting_id>/status', methods=['POST'])
@login_required
def update_meeting_status(meeting_id):
    """Mark a meeting as COMPLETED, CANCELLED, or NO_SHOW."""
    user = get_current_user()
    user_id = user['id']
    new_status = request.form.get('status')
    cancellation_reason = request.form.get('cancellation_reason', '').strip()

    if new_status not in ('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW'):
        flash("Invalid status.", "danger")
        return redirect(url_for('relations.list_relations'))

    # Verify authorization
    sql = """
        SELECT m.id, m.relation_id, mr.mentee_id, mr.mentor_id
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE m.id = %s
    """
    m = fetch_one(sql, (meeting_id,))
    if not m or (user['role'] != 'ADMIN' and user_id not in (m['mentee_id'], m['mentor_id'])):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    update_sql = """
        UPDATE meetings 
        SET status = %s, cancellation_reason = %s
        WHERE id = %s
    """
    execute_query(update_sql, (new_status, cancellation_reason if new_status == 'CANCELLED' else None, meeting_id))
    flash(f"Meeting status updated to {new_status}.", "info")
    return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

@schedule_bp.route('/meetings/<int:meeting_id>/notes', methods=['POST'])
@login_required
def add_meeting_notes(meeting_id):
    """Add discussion summary and action items to a completed meeting (Member 5 aux table: meeting_notes)."""
    user = get_current_user()
    user_id = user['id']
    summary = request.form.get('summary', '').strip()
    action_items = request.form.get('action_items', '').strip()

    if not summary:
        flash("Summary is required.", "danger")
        return redirect(url_for('relations.list_relations'))

    # Verify participation
    sql = """
        SELECT m.id, m.relation_id, mr.mentee_id, mr.mentor_id
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE m.id = %s
    """
    m = fetch_one(sql, (meeting_id,))
    if not m or (user['role'] != 'ADMIN' and user_id not in (m['mentee_id'], m['mentor_id'])):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    insert_note_sql = """
        INSERT INTO meeting_notes (meeting_id, author_id, summary, action_items)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(insert_note_sql, (meeting_id, user_id, summary, action_items))
    flash("Meeting notes and action items saved!", "success")
    return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

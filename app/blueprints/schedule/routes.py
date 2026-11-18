from datetime import datetime, date, time, timedelta
from flask import render_template, request, redirect, url_for, flash
from app.blueprints.schedule import schedule_bp
from app.db import fetch_one, fetch_all, execute_query, get_db
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

# CQ-04: weekly utilization of each mentor (Member 4).
# Compares the hours a mentor publishes every week with the hours already
# booked in the next 7 days. Two derived tables keep one row per mentor, so the
# availability and meeting rows never multiply each other.
# Parameters: (mentor_id, mentor_id) for one mentor, (None, None) for all mentors.
CQ04_UTILIZATION_SQL = """
    SELECT
        u.id AS mentor_id,
        CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
        u.current_title,
        COALESCE(avail.active_windows, 0) AS active_windows,
        COALESCE(avail.total_available_hours_weekly, 0.0) AS weekly_available_hours,
        COALESCE(scheduled.total_scheduled_hours, 0.0) AS upcoming_scheduled_hours,
        CASE
            WHEN COALESCE(avail.total_available_hours_weekly, 0.0) > COALESCE(scheduled.total_scheduled_hours, 0.0)
            THEN COALESCE(avail.total_available_hours_weekly, 0.0) - COALESCE(scheduled.total_scheduled_hours, 0.0)
            ELSE 0.0
        END AS free_hours,
        ROUND(
            (COALESCE(scheduled.total_scheduled_hours, 0.0) / NULLIF(avail.total_available_hours_weekly, 0)) * 100,
            1
        ) AS utilization_rate_pct
    FROM users u
    LEFT JOIN (
        SELECT
            mentor_id,
            COUNT(*) AS active_windows,
            ROUND(SUM(TIME_TO_SEC(TIMEDIFF(end_time, start_time)) / 3600), 2) AS total_available_hours_weekly
        FROM mentor_availability
        WHERE is_active = TRUE
        GROUP BY mentor_id
    ) avail ON u.id = avail.mentor_id
    LEFT JOIN (
        SELECT
            mr.mentor_id,
            ROUND(SUM(TIMESTAMPDIFF(MINUTE, m.scheduled_start, m.scheduled_end) / 60.0), 2) AS total_scheduled_hours
        FROM mentorship_relations mr
        JOIN meetings m ON mr.id = m.relation_id
        WHERE m.status = 'SCHEDULED'
          AND m.scheduled_start >= NOW()
          AND m.scheduled_start < DATE_ADD(NOW(), INTERVAL 7 DAY)
        GROUP BY mr.mentor_id
    ) scheduled ON u.id = scheduled.mentor_id
    WHERE u.role = 'MENTOR'
      AND (%s IS NULL OR u.id = %s)
    ORDER BY utilization_rate_pct DESC, mentor_name
"""


@schedule_bp.route('/availability/utilization')
@role_required('ADMIN')
def mentor_utilization():
    """CQ-04 for admins: every mentor's weekly utilization, busiest mentors first."""
    mentors = fetch_all(CQ04_UTILIZATION_SQL, (None, None))
    return render_template('schedule/utilization.html', mentors=mentors)


def _parse_window_form(form):
    """
    Reads and validates the day/start/end fields of an availability form.
    Returns (day, start_str, end_str, error). Times come back as 'HH:MM:SS'.
    """
    day = form.get('day_of_week', type=int)
    if day is None or day not in DAYS_OF_WEEK:
        return None, None, None, "Please choose a valid day of the week."
    try:
        start = time.fromisoformat(form.get('start_time', '').strip())
        end = time.fromisoformat(form.get('end_time', '').strip())
    except ValueError:
        return None, None, None, "Please enter valid start and end times."
    if end <= start:
        return None, None, None, "End time must be after start time."
    return day, start.strftime('%H:%M:%S'), end.strftime('%H:%M:%S'), None


def _window_overlaps(mentor_id, day, start, end, ignore_id=0):
    """True if the mentor already has a window on this day that overlaps [start, end)."""
    row = fetch_one(
        """
        SELECT id FROM mentor_availability
        WHERE mentor_id = %s AND day_of_week = %s AND id <> %s
          AND start_time < %s AND end_time > %s
        """,
        (mentor_id, day, ignore_id, end, start)
    )
    return row is not None


@schedule_bp.route('/availability', methods=['GET', 'POST'])
@role_required('MENTOR')
def manage_availability():
    """Mentor manages weekly recurring availability windows (FR-11: create + read)."""
    user = get_current_user()
    mentor_id = user['id']

    if request.method == 'POST':
        day, start, end, error = _parse_window_form(request.form)
        if error:
            flash(error, "danger")
        elif _window_overlaps(mentor_id, day, start, end):
            flash("This window overlaps with another window on the same day.", "warning")
        else:
            execute_query(
                """
                INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                """,
                (mentor_id, day, start, end)
            )
            flash("Availability window added.", "success")
            return redirect(url_for('schedule.manage_availability'))

    slots = fetch_all(
        """
        SELECT id, day_of_week, start_time, end_time, is_active
        FROM mentor_availability
        WHERE mentor_id = %s
        ORDER BY day_of_week, start_time
        """,
        (mentor_id,)
    )
    usage = fetch_all(CQ04_UTILIZATION_SQL, (mentor_id, mentor_id))
    return render_template('schedule/availability.html', slots=slots, days=DAYS_OF_WEEK,
                           usage=usage[0] if usage else None)


@schedule_bp.route('/availability/<int:slot_id>/edit', methods=['POST'])
@role_required('MENTOR')
def edit_availability(slot_id):
    """FR-11 update: change the day or the times of one of the mentor's own windows."""
    user = get_current_user()
    back = redirect(url_for('schedule.manage_availability'))

    slot = fetch_one("SELECT id FROM mentor_availability WHERE id = %s AND mentor_id = %s", (slot_id, user['id']))
    if not slot:
        flash("Availability window not found.", "danger")
        return back

    day, start, end, error = _parse_window_form(request.form)
    if error:
        flash(error, "danger")
    elif _window_overlaps(user['id'], day, start, end, ignore_id=slot_id):
        flash("This window overlaps with another window on the same day.", "warning")
    else:
        execute_query(
            "UPDATE mentor_availability SET day_of_week = %s, start_time = %s, end_time = %s WHERE id = %s AND mentor_id = %s",
            (day, start, end, slot_id, user['id'])
        )
        flash("Availability window updated.", "success")
    return back


@schedule_bp.route('/availability/<int:slot_id>/toggle', methods=['POST'])
@role_required('MENTOR')
def toggle_availability(slot_id):
    """FR-11 update: switch a window on or off without deleting it."""
    user = get_current_user()
    _, changed = execute_query(
        "UPDATE mentor_availability SET is_active = NOT is_active WHERE id = %s AND mentor_id = %s",
        (slot_id, user['id'])
    )
    flash("Availability window updated." if changed else "Availability window not found.",
          "success" if changed else "danger")
    return redirect(url_for('schedule.manage_availability'))


@schedule_bp.route('/availability/delete/<int:slot_id>', methods=['POST'])
@role_required('MENTOR')
def delete_availability(slot_id):
    user = get_current_user()
    execute_query("DELETE FROM mentor_availability WHERE id = %s AND mentor_id = %s", (slot_id, user['id']))
    flash("Availability window removed.", "info")
    return redirect(url_for('schedule.manage_availability'))


BOOKING_WEEKS_AHEAD = 6  # how many upcoming weeks a mentee can book into


def _to_time(value):
    """MySQL returns TIME columns as timedelta, the demo DB as 'HH:MM' or 'HH:MM:SS' strings."""
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        return (datetime.min + value).time()
    return time.fromisoformat(str(value))


def _to_datetime(value):
    """MySQL returns DATETIME as datetime objects, the demo DB as strings."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _active_windows(mentor_id):
    return fetch_all(
        """
        SELECT id, day_of_week, start_time, end_time
        FROM mentor_availability
        WHERE mentor_id = %s AND is_active = TRUE
        ORDER BY day_of_week, start_time
        """,
        (mentor_id,)
    )


def _mentor_has_overlap(mentor_id, start_dt, end_dt):
    """True if the mentor already has a SCHEDULED meeting overlapping [start_dt, end_dt)."""
    overlap_sql = """
        SELECT m.id
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE mr.mentor_id = %s
          AND m.status = 'SCHEDULED'
          AND m.scheduled_start < %s
          AND m.scheduled_end > %s
    """
    return fetch_one(overlap_sql, (mentor_id, end_dt, start_dt)) is not None


def _upcoming_slots(mentor_id, windows):
    """
    Turns the mentor's recurring weekly windows into concrete bookable slots
    for the next BOOKING_WEEKS_AHEAD weeks, grouped by week.
    Slots already taken by another meeting are marked unavailable; past slots are skipped.
    """
    now = datetime.now()
    this_monday = now.date() - timedelta(days=now.weekday())

    booked_rows = fetch_all(
        """
        SELECT m.scheduled_start, m.scheduled_end
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE mr.mentor_id = %s AND m.status = 'SCHEDULED' AND m.scheduled_end > %s
        """,
        (mentor_id, now)
    )
    booked = [(_to_datetime(r['scheduled_start']), _to_datetime(r['scheduled_end'])) for r in booked_rows]

    weeks = []
    for w in range(BOOKING_WEEKS_AHEAD):
        week_start = this_monday + timedelta(weeks=w)
        slots = []
        for win in windows:
            day = week_start + timedelta(days=win['day_of_week'])
            start_dt = datetime.combine(day, _to_time(win['start_time']))
            end_dt = datetime.combine(day, _to_time(win['end_time']))
            if start_dt <= now:
                continue
            taken = any(b_start < end_dt and b_end > start_dt for b_start, b_end in booked)
            slots.append({
                'value': f"{win['id']}|{day.isoformat()}",
                'label': f"{DAYS_OF_WEEK[win['day_of_week']]} {day.strftime('%d %b')}, "
                         f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}",
                'taken': taken,
            })
        if slots:
            weeks.append({'label': f"Week of {week_start.strftime('%d %b %Y')}", 'slots': slots})
    return weeks


@schedule_bp.route('/relations/<int:relation_id>/meetings/book', methods=['GET', 'POST'])
@login_required
def book_meeting(relation_id):
    """
    CREATE a meeting under an active relationship (FR-12).
    The user picks a week and one of the mentor's availability windows;
    day and time always come from the mentor's window, never typed by hand.
    """
    user = get_current_user()
    user_id = user['id']

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

    windows = _active_windows(rel['mentor_id'])

    if request.method == 'POST':
        slot = request.form.get('slot', '')
        agenda = request.form.get('agenda', '').strip()
        meeting_link = request.form.get('meeting_link', '').strip() or 'https://meet.jit.si/mentor-session'
        back = redirect(url_for('schedule.book_meeting', relation_id=relation_id))

        if not agenda:
            flash("Please enter an agenda for the session.", "warning")
            return back

        # slot looks like "<window_id>|<YYYY-MM-DD>"
        try:
            window_id_str, day_str = slot.split('|')
            window_id = int(window_id_str)
            day = date.fromisoformat(day_str)
        except ValueError:
            flash("Please choose one of the mentor's available slots.", "danger")
            return back

        # FR-12: the window must be an ACTIVE window of THIS mentor, on the right weekday
        window = next((w for w in windows if w['id'] == window_id), None)
        if window is None:
            flash("That availability window does not exist or is no longer active.", "danger")
            return back
        if day.weekday() != window['day_of_week']:
            flash("The chosen date does not fall on the mentor's available day.", "danger")
            return back

        start_dt = datetime.combine(day, _to_time(window['start_time']))
        end_dt = datetime.combine(day, _to_time(window['end_time']))
        last_bookable_day = date.today() + timedelta(weeks=BOOKING_WEEKS_AHEAD)
        if start_dt <= datetime.now() or day > last_bookable_day:
            flash("That slot is not bookable (in the past or too far ahead).", "warning")
            return back

        # NFR-05: two people must not book the same mentor slot at the same time.
        # 1) end the read transaction, so the next reads see the newest committed data
        # 2) lock the mentor's row; a second booking for this mentor waits here
        # 3) check for a conflict, insert the meeting and the notification, then commit
        #    (the commit releases the lock)
        conn = get_db()
        conn.commit()
        fetch_one("SELECT id FROM users WHERE id = %s FOR UPDATE", (rel['mentor_id'],))

        # Conflict detection: the mentor cannot have two meetings at the same time
        if _mentor_has_overlap(rel['mentor_id'], start_dt, end_dt):
            conn.rollback()
            flash("That slot is already booked. Please pick another one.", "warning")
            return back

        execute_query(
            """
            INSERT INTO meetings (relation_id, scheduled_start, scheduled_end, meeting_link, agenda, status)
            VALUES (%s, %s, %s, %s, %s, 'SCHEDULED')
            """,
            (relation_id, start_dt, end_dt, meeting_link, agenda),
            commit=False
        )

        target_notify_id = rel['mentee_id'] if user_id == rel['mentor_id'] else rel['mentor_id']
        notif_msg = f"A new mentorship session has been scheduled for {start_dt.strftime('%B %d, %Y at %H:%M')}."
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                      (target_notify_id, "Meeting Scheduled", notif_msg), commit=False)
        conn.commit()

        flash("Meeting successfully scheduled!", "success")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    weeks = _upcoming_slots(rel['mentor_id'], windows)
    return render_template('schedule/book.html', rel=rel, availability=windows, weeks=weeks, days=DAYS_OF_WEEK)


@schedule_bp.route('/meetings/<int:meeting_id>/status', methods=['POST'])
@login_required
def update_meeting_status(meeting_id):
    """Mark a meeting as COMPLETED, CANCELLED, or NO_SHOW."""
    user = get_current_user()
    user_id = user['id']
    new_status = request.form.get('status')
    cancellation_reason = request.form.get('cancellation_reason', '').strip()

    if new_status not in ('COMPLETED', 'CANCELLED', 'NO_SHOW'):
        flash("Invalid status.", "danger")
        return redirect(url_for('relations.list_relations'))

    # Verify authorization
    sql = """
        SELECT m.id, m.relation_id, m.status, m.scheduled_start, mr.mentee_id, mr.mentor_id
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE m.id = %s
    """
    m = fetch_one(sql, (meeting_id,))
    if not m or (user['role'] != 'ADMIN' and user_id not in (m['mentee_id'], m['mentor_id'])):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    # Only a SCHEDULED meeting can move to a final state (COMPLETED / CANCELLED / NO_SHOW)
    if m['status'] != 'SCHEDULED':
        flash(f"This meeting is already {m['status']} and can no longer be changed.", "warning")
        return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

    # A meeting can only be COMPLETED / NO_SHOW once it has actually started
    if new_status in ('COMPLETED', 'NO_SHOW') and _to_datetime(m['scheduled_start']) > datetime.now():
        flash("This meeting has not started yet, so it cannot be marked as completed or no-show.", "warning")
        return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

    # FR-13: a cancellation must always carry a reason
    if new_status == 'CANCELLED' and not cancellation_reason:
        flash("Please provide a reason for cancelling the meeting.", "danger")
        return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

    update_sql = """
        UPDATE meetings 
        SET status = %s, cancellation_reason = %s
        WHERE id = %s
    """
    execute_query(update_sql, (new_status, cancellation_reason if new_status == 'CANCELLED' else None, meeting_id))
    flash(f"Meeting status updated to {new_status}.", "info")
    return redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))

# ---------------------------------------------------------------------
# Meeting notes CRUD (FR-14, auxiliary table meeting_notes)
# ---------------------------------------------------------------------

def _meeting_with_participants(meeting_id):
    return fetch_one(
        """
        SELECT m.id, m.relation_id, m.status, mr.mentee_id, mr.mentor_id
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE m.id = %s
        """,
        (meeting_id,)
    )


def _note_with_meeting(note_id):
    return fetch_one(
        """
        SELECT mn.id, mn.author_id, m.relation_id
        FROM meeting_notes mn
        JOIN meetings m ON mn.meeting_id = m.id
        WHERE mn.id = %s
        """,
        (note_id,)
    )


@schedule_bp.app_template_global()
def notes_by_meeting(relation_id):
    """
    READ: all notes of one mentorship in a single query, returned as
    {meeting_id: [note, ...]} so the mentorship page can show them under each meeting.
    """
    rows = fetch_all(
        """
        SELECT mn.id, mn.meeting_id, mn.author_id, mn.summary, mn.action_items, mn.created_at,
               u.first_name, u.last_name
        FROM meeting_notes mn
        JOIN meetings m ON mn.meeting_id = m.id
        JOIN users u ON mn.author_id = u.id
        WHERE m.relation_id = %s
        ORDER BY mn.created_at, mn.id
        """,
        (relation_id,)
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row['meeting_id'], []).append(row)
    return grouped


@schedule_bp.route('/meetings/<int:meeting_id>/notes', methods=['POST'])
@login_required
def add_meeting_notes(meeting_id):
    """CREATE: a participant records the summary and action items of a completed meeting."""
    user = get_current_user()
    user_id = user['id']
    summary = request.form.get('summary', '').strip()
    action_items = request.form.get('action_items', '').strip()

    m = _meeting_with_participants(meeting_id)
    if not m or (user['role'] != 'ADMIN' and user_id not in (m['mentee_id'], m['mentor_id'])):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    back = redirect(url_for('relations.relation_detail', relation_id=m['relation_id']))
    if m['status'] != 'COMPLETED':
        flash("Notes can only be added to completed meetings.", "warning")
        return back
    if not summary:
        flash("Summary is required.", "danger")
        return back

    execute_query(
        """
        INSERT INTO meeting_notes (meeting_id, author_id, summary, action_items)
        VALUES (%s, %s, %s, %s)
        """,
        (meeting_id, user_id, summary, action_items)
    )
    flash("Meeting notes and action items saved!", "success")
    return back


@schedule_bp.route('/notes/<int:note_id>/edit', methods=['POST'])
@login_required
def edit_meeting_note(note_id):
    """UPDATE: only the author of a note can change it."""
    user = get_current_user()
    note = _note_with_meeting(note_id)
    if not note or note['author_id'] != user['id']:
        flash("You can only edit your own notes.", "danger")
        return redirect(url_for('relations.list_relations'))

    summary = request.form.get('summary', '').strip()
    action_items = request.form.get('action_items', '').strip()
    back = redirect(url_for('relations.relation_detail', relation_id=note['relation_id']))
    if not summary:
        flash("Summary is required.", "danger")
        return back

    execute_query(
        "UPDATE meeting_notes SET summary = %s, action_items = %s WHERE id = %s AND author_id = %s",
        (summary, action_items, note_id, user['id'])
    )
    flash("Meeting notes updated.", "success")
    return back


@schedule_bp.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_meeting_note(note_id):
    """DELETE: the author (or an admin) removes a note."""
    user = get_current_user()
    note = _note_with_meeting(note_id)
    if not note or (note['author_id'] != user['id'] and user['role'] != 'ADMIN'):
        flash("You can only delete your own notes.", "danger")
        return redirect(url_for('relations.list_relations'))

    execute_query("DELETE FROM meeting_notes WHERE id = %s", (note_id,))
    flash("Meeting notes deleted.", "info")
    return redirect(url_for('relations.relation_detail', relation_id=note['relation_id']))

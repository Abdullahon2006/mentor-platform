from datetime import date, datetime
from flask import render_template, request, redirect, url_for, flash
from app.blueprints.relations import relations_bp
from app.db import fetch_one, fetch_all, execute_query, get_db
from app.auth_util import login_required, role_required, get_current_user

MENTOR_CAPACITY = 5  # same limit CQ-02 uses: a mentor can have at most 5 ACTIVE mentees

# FR-10 lifecycle: which status can follow which. COMPLETED and TERMINATED are final.
ALLOWED_TRANSITIONS = {
    'ACTIVE': {'PAUSED', 'COMPLETED', 'TERMINATED'},
    'PAUSED': {'ACTIVE', 'COMPLETED', 'TERMINATED'},
    'COMPLETED': set(),
    'TERMINATED': set(),
}
STATUS_WORDS = {'ACTIVE': 'resumed', 'PAUSED': 'paused', 'COMPLETED': 'completed', 'TERMINATED': 'terminated'}

@relations_bp.route('/')
@login_required
def list_relations():
    """Lists mentorship relationships for the logged in user."""
    user = get_current_user()
    user_id = user['id']
    role = user['role']

    if role == 'MENTEE':
        sql = """
            SELECT mr.id, mr.start_date, mr.end_date, mr.status, mr.notes,
                   m.id AS partner_id, m.first_name, m.last_name, m.current_title, m.organization,
                   COUNT(DISTINCT mt.id) AS meeting_count
            FROM mentorship_relations mr
            JOIN users m ON mr.mentor_id = m.id
            LEFT JOIN meetings mt ON mr.id = mt.relation_id
            WHERE mr.mentee_id = %s
            GROUP BY mr.id, mr.start_date, mr.end_date, mr.status, mr.notes, m.id, m.first_name, m.last_name, m.current_title, m.organization
            ORDER BY (mr.status = 'ACTIVE') DESC, mr.start_date DESC
        """
        relations = fetch_all(sql, (user_id,))
    elif role == 'MENTOR':
        sql = """
            SELECT mr.id, mr.start_date, mr.end_date, mr.status, mr.notes,
                   m.id AS partner_id, m.first_name, m.last_name, m.current_title, m.organization,
                   COUNT(DISTINCT mt.id) AS meeting_count
            FROM mentorship_relations mr
            JOIN users m ON mr.mentee_id = m.id
            LEFT JOIN meetings mt ON mr.id = mt.relation_id
            WHERE mr.mentor_id = %s
            GROUP BY mr.id, mr.start_date, mr.end_date, mr.status, mr.notes, m.id, m.first_name, m.last_name, m.current_title, m.organization
            ORDER BY (mr.status = 'ACTIVE') DESC, mr.start_date DESC
        """
        relations = fetch_all(sql, (user_id,))
    else:
        # Admin view
        sql = """
            SELECT mr.id, mr.start_date, mr.end_date, mr.status,
                   mentee.first_name AS mentee_first, mentee.last_name AS mentee_last,
                   mentor.first_name AS mentor_first, mentor.last_name AS mentor_last,
                   COUNT(DISTINCT mt.id) AS meeting_count
            FROM mentorship_relations mr
            JOIN users mentee ON mr.mentee_id = mentee.id
            JOIN users mentor ON mr.mentor_id = mentor.id
            LEFT JOIN meetings mt ON mr.id = mt.relation_id
            GROUP BY mr.id, mr.start_date, mr.end_date, mr.status, mentee.first_name, mentee.last_name, mentor.first_name, mentor.last_name
            ORDER BY mr.start_date DESC
        """
        relations = fetch_all(sql)

    return render_template('relations/index.html', relations=relations, user=user)

@relations_bp.route('/<int:relation_id>')
@login_required
def relation_detail(relation_id):
    """Detailed view of an individual mentorship partnership."""
    user = get_current_user()
    user_id = user['id']

    sql = """
        SELECT mr.id, mr.mentee_id, mr.mentor_id, mr.start_date, mr.end_date, mr.status, mr.notes,
               mentee.first_name AS mentee_first, mentee.last_name AS mentee_last, mentee.email AS mentee_email,
               mentor.first_name AS mentor_first, mentor.last_name AS mentor_last, mentor.email AS mentor_email,
               mg.title AS goal_title, mg.description AS goal_desc, mg.status AS goal_status
        FROM mentorship_relations mr
        JOIN users mentee ON mr.mentee_id = mentee.id
        JOIN users mentor ON mr.mentor_id = mentor.id
        JOIN mentorship_applications ma ON mr.application_id = ma.id
        LEFT JOIN mentorship_goals mg ON ma.goal_id = mg.id
        WHERE mr.id = %s
    """
    rel = fetch_one(sql, (relation_id,))
    if not rel:
        flash("Mentorship relationship not found.", "warning")
        return redirect(url_for('relations.list_relations'))

    # Security check: ensure user is a participant or admin
    if user['role'] != 'ADMIN' and user_id not in (rel['mentee_id'], rel['mentor_id']):
        flash("Access unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    # Fetch meetings under this relationship (notes are loaded per meeting by the
    # schedule blueprint's notes_by_meeting() template helper, so a meeting with
    # several notes is not listed several times)
    meetings_sql = """
        SELECT m.id, m.scheduled_start, m.scheduled_end, m.meeting_link, m.agenda, m.status, m.cancellation_reason
        FROM meetings m
        WHERE m.relation_id = %s
        ORDER BY m.scheduled_start DESC
    """
    meetings = fetch_all(meetings_sql, (relation_id,))

    # Check reviews submitted
    reviews_sql = """
        SELECT rr.id, rr.reviewer_id, rr.reviewee_id, rr.rating, rr.review_text, rr.created_at,
               u.first_name, u.last_name
        FROM reviews_and_ratings rr
        JOIN users u ON rr.reviewer_id = u.id
        WHERE rr.relation_id = %s
    """
    reviews = fetch_all(reviews_sql, (relation_id,))

    # Check if logged in user has already reviewed
    has_reviewed = any(r['reviewer_id'] == user_id for r in reviews)

    return render_template(
        'relations/detail.html',
        rel=rel,
        meetings=meetings,
        reviews=reviews,
        has_reviewed=has_reviewed,
        user=user
    )

@relations_bp.route('/<int:relation_id>/status', methods=['POST'])
@login_required
def update_relation_status(relation_id):
    """
    FR-10 update: move a mentorship to the next status (pause, resume, complete, terminate).
    The status change, the cancellation of upcoming meetings and the notifications
    are saved together in one transaction.
    """
    user = get_current_user()
    user_id = user['id']
    new_status = request.form.get('status')
    notes = request.form.get('notes', '').strip()
    back = redirect(url_for('relations.relation_detail', relation_id=relation_id))

    if new_status not in ALLOWED_TRANSITIONS:
        flash("Invalid status.", "danger")
        return back

    rel = fetch_one(
        """
        SELECT mr.id, mr.mentee_id, mr.mentor_id, mr.status,
               mentee.first_name AS mentee_first, mentee.last_name AS mentee_last,
               mentor.first_name AS mentor_first, mentor.last_name AS mentor_last
        FROM mentorship_relations mr
        JOIN users mentee ON mr.mentee_id = mentee.id
        JOIN users mentor ON mr.mentor_id = mentor.id
        WHERE mr.id = %s
        """,
        (relation_id,)
    )
    if not rel or (user['role'] != 'ADMIN' and user_id not in (rel['mentee_id'], rel['mentor_id'])):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('relations.list_relations'))

    if new_status not in ALLOWED_TRANSITIONS[rel['status']]:
        flash(f"A {rel['status']} mentorship cannot be changed to {new_status}.", "warning")
        return back

    if new_status == 'ACTIVE':
        active = fetch_one(
            "SELECT COUNT(*) AS cnt FROM mentorship_relations WHERE mentor_id = %s AND status = 'ACTIVE'",
            (rel['mentor_id'],)
        )['cnt']
        if active >= MENTOR_CAPACITY:
            flash(f"The mentor already has {MENTOR_CAPACITY} active mentees, so this mentorship cannot be resumed.", "warning")
            return back

    # COMPLETED and TERMINATED set the end date; the other statuses keep it as it is
    end_date_val = date.today() if new_status in ('COMPLETED', 'TERMINATED') else None

    # --- one transaction: status + meetings + notifications ---
    _, changed = execute_query(
        """
        UPDATE mentorship_relations
        SET status = %s, end_date = COALESCE(%s, end_date), notes = COALESCE(NULLIF(%s, ''), notes)
        WHERE id = %s AND status = %s
        """,
        (new_status, end_date_val, notes, relation_id, rel['status']),
        commit=False
    )
    if not changed:
        get_db().rollback()
        flash("The mentorship was changed by someone else. Please try again.", "warning")
        return back

    cancelled = 0
    if new_status != 'ACTIVE':
        _, cancelled = execute_query(
            """
            UPDATE meetings
            SET status = 'CANCELLED', cancellation_reason = %s
            WHERE relation_id = %s AND status = 'SCHEDULED' AND scheduled_start > %s
            """,
            (f"Mentorship was {STATUS_WORDS[new_status]}", relation_id, datetime.now()),
            commit=False
        )

    actor = f"{user['first_name']} {user['last_name']}"
    message = f"{actor} {STATUS_WORDS[new_status]} the mentorship between {rel['mentee_first']} {rel['mentee_last']} and {rel['mentor_first']} {rel['mentor_last']}."
    if cancelled:
        message += f" {cancelled} upcoming meeting(s) were cancelled."
    for target_id in (rel['mentee_id'], rel['mentor_id']):
        if target_id != user_id:
            execute_query(
                "INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                (target_id, "Mentorship Update", message),
                commit=False
            )
    get_db().commit()

    flash(f"Mentorship {STATUS_WORDS[new_status]}." + (f" {cancelled} upcoming meeting(s) cancelled." if cancelled else ""), "success")
    return back


@relations_bp.route('/<int:relation_id>/delete', methods=['POST'])
@role_required('ADMIN')
def delete_relation(relation_id):
    """
    FR-10 delete (admin only): removes a mentorship with its meetings and reviews (FK CASCADE).
    The accepted application is set back to WITHDRAWN so the mentee can apply again.
    """
    rel = fetch_one(
        "SELECT id, application_id, mentee_id, mentor_id FROM mentorship_relations WHERE id = %s",
        (relation_id,)
    )
    if not rel:
        flash("Mentorship relationship not found.", "warning")
        return redirect(url_for('relations.list_relations'))

    execute_query("DELETE FROM mentorship_relations WHERE id = %s", (relation_id,), commit=False)
    execute_query(
        "UPDATE mentorship_applications SET status = 'WITHDRAWN' WHERE id = %s AND status = 'ACCEPTED'",
        (rel['application_id'],),
        commit=False
    )
    for target_id in (rel['mentee_id'], rel['mentor_id']):
        execute_query(
            "INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
            (target_id, "Mentorship Removed", "An administrator removed one of your mentorships."),
            commit=False
        )
    get_db().commit()

    flash("Mentorship deleted.", "info")
    return redirect(url_for('relations.list_relations'))

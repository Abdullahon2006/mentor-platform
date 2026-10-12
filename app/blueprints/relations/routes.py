from datetime import date
from flask import render_template, request, redirect, url_for, flash
from app.blueprints.relations import relations_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, get_current_user

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

    # Fetch meetings under this relationship
    meetings_sql = """
        SELECT m.id, m.scheduled_start, m.scheduled_end, m.meeting_link, m.agenda, m.status, m.cancellation_reason,
               mn.summary AS note_summary, mn.action_items
        FROM meetings m
        LEFT JOIN meeting_notes mn ON m.id = mn.meeting_id
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
    """Update relationship state (ACTIVE, COMPLETED, PAUSED, TERMINATED)."""
    user = get_current_user()
    user_id = user['id']
    new_status = request.form.get('status')
    notes = request.form.get('notes', '').strip()

    if new_status not in ('ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED'):
        flash("Invalid status.", "danger")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    # Verify authorization
    rel = fetch_one("SELECT id, mentee_id, mentor_id FROM mentorship_relations WHERE id = %s", (relation_id,))
    if not rel or (user['role'] != 'ADMIN' and user_id not in (rel['mentee_id'], rel['mentor_id'])):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('relations.list_relations'))

    end_date_val = date.today() if new_status in ('COMPLETED', 'TERMINATED') else None

    update_sql = """
        UPDATE mentorship_relations 
        SET status = %s, end_date = %s, notes = COALESCE(NULLIF(%s, ''), notes)
        WHERE id = %s
    """
    execute_query(update_sql, (new_status, end_date_val, notes, relation_id))
    flash(f"Mentorship status updated to {new_status}.", "success")
    return redirect(url_for('relations.relation_detail', relation_id=relation_id))

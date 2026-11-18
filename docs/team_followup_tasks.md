# Team Follow-up Tasks

Found while finishing the relations and availability module (PR #5).
These tasks are in your files, so Gaffar did not change them.
Each task has the file, the steps, and a check to know it is done.

How to work:
- Make a branch `feature/<your-module>` from the latest `main`.
- Commit your own changes with short messages, then open a PR.
- Run `pytest` before the PR (it needs MySQL or the demo database).

| # | Owner | Task | Priority |
| :-: | :--- | :--- | :--- |
| 1 | Abdullokhon Valikhonov | Mentor capacity check when accepting an application | Must do |
| 2 | Abdullokhon Valikhonov | Make "accept application" one transaction | Must do |
| 3 | Raimbek Erik | Use the booking lock in every route that writes meetings | Rule |
| 4 | Raimbek Erik | Test: two bookings for the same slot make one meeting | Optional |
| 5 | Ravan Seyfullayev | Show the mentor's utilization on the mentor dashboard | Optional |

Denils Mahmuti: no tasks found.

---

## 1. Capacity check on accept (Abdullokhon)

**File:** `app/blueprints/applications/routes.py`, function `decide_application`

**Problem:** CQ-02 hides mentors that have 5 active mentees. But a mentor can still
accept a 6th application. The relation "resume" action already blocks this.

**Steps:**
1. Import the limit: `from app.blueprints.relations.routes import MENTOR_CAPACITY`
2. After the "already processed" check and before the `UPDATE`, when `decision == 'ACCEPTED'`, count the active relations:
   ```python
   active = fetch_one(
       "SELECT COUNT(*) AS cnt FROM mentorship_relations WHERE mentor_id = %s AND status = 'ACTIVE'",
       (mentor_id,)
   )['cnt']
   if active >= MENTOR_CAPACITY:
       flash(f"You already have {MENTOR_CAPACITY} active mentees.", "warning")
       return redirect(url_for('applications.list_applications'))
   ```

**Check:** A mentor with 5 ACTIVE relations cannot accept. The application stays PENDING.
A mentor with 4 can accept.

## 2. Accept in one transaction (Abdullokhon)

**File:** `app/blueprints/applications/routes.py`, function `decide_application`

**Problem:** The application `UPDATE`, the `mentorship_relations` `INSERT` and the
notification each commit alone. If the `INSERT` fails, the application is ACCEPTED
but there is no relation. Milestone 2 (section 5) says this must be an ACID transaction.

**Steps:**
1. Import `get_db`: `from app.db import fetch_one, fetch_all, execute_query, get_db`
2. Add `commit=False` to the `UPDATE`, the relation `INSERT` and the notification `INSERT`.
3. Call `get_db().commit()` once, after the last statement.
4. Make the `UPDATE` safe against double clicks: add `AND status = 'PENDING'` to its
   `WHERE`, and if the returned row count is 0, show "already processed" and stop.

```python
_, changed = execute_query(
    "UPDATE mentorship_applications SET status = %s, decided_at = NOW() WHERE id = %s AND status = 'PENDING'",
    (decision, app_id), commit=False
)
if not changed:
    get_db().rollback()
    flash("This application has already been processed.", "warning")
    return redirect(url_for('applications.list_applications'))
# ... INSERT relation (commit=False), INSERT notification (commit=False) ...
get_db().commit()
```

**Example:** `update_relation_status` in `app/blueprints/relations/routes.py` uses the same pattern.

**Check:** Accept an application: the status, the relation and the notification all exist.
Click "Accept" twice quickly: only one relation is created (`application_id` is UNIQUE).

## 3. Booking lock rule (Raimbek)

**File:** `app/blueprints/schedule/routes.py`, function `book_meeting` (see the `NFR-05` comment)

**Problem:** Without a lock, two requests can book the same mentor slot at the same time.
`book_meeting` now locks the mentor row. This is not a change for you now.
It is a rule for new code.

**Rule:** Any route that creates or moves a meeting (for example "reschedule") must do:
1. `conn = get_db(); conn.commit()`
2. `fetch_one("SELECT id FROM users WHERE id = %s FOR UPDATE", (mentor_id,))`
3. `_mentor_has_overlap(...)`. If true: `conn.rollback()` and stop.
4. Write with `execute_query(..., commit=False)`
5. `conn.commit()`

## 4. Test: no double booking (Raimbek, optional)

**File:** `tests/test_meetings.py`

**Idea:** Start two threads that wait on a `threading.Barrier`, then both `POST` to
`/relations/<id>/meetings/book` with the same `slot` and the same agenda
(include your `MARK` so the fixture cleans up). To make the race easy to see, wrap
`_mentor_has_overlap` so it sleeps 0.5 seconds after the check.

**Check:** After both requests, there is exactly 1 SCHEDULED meeting with that agenda.
Without the lock in `book_meeting`, the test finds 2.

## 5. Utilization on the mentor dashboard (Ravan, optional)

**Files:** `app/blueprints/profile/routes.py` (mentor branch of `dashboard`),
`app/templates/dashboard/mentor_dashboard.html`

**Idea:** Mentors can see their weekly numbers on the Availability page.
Show the same numbers on the dashboard.

**Steps:**
1. `from app.blueprints.schedule.routes import CQ04_UTILIZATION_SQL`
2. `rows = fetch_all(CQ04_UTILIZATION_SQL, (user['id'], user['id']))` and pass `usage=rows[0] if rows else None` to the template.
3. In the template, show `usage.weekly_available_hours`, `usage.upcoming_scheduled_hours`,
   `usage.free_hours` and `usage.utilization_rate_pct` (it is `None` when the mentor has no active windows).

**Example:** `app/templates/schedule/availability.html` (the card at the top).

**Check:** Log in as `dr.demir@techcorp.com`. The dashboard shows 4.0 weekly hours
with the seed data.

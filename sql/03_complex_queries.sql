-- =====================================================================
-- BBF 302E Database Systems - Complex SQL Queries
-- Topic: Mentor–Mentee Matching Platform
-- =====================================================================

USE mentor_platform;

-- =====================================================================
-- COMPLEX QUERY 1: Multi-Criteria Mentor Recommendation Engine
-- ---------------------------------------------------------------------
-- Purpose:
-- Given a mentee ID (e.g., Ali Yilmaz, id=6), recommend best-fit mentors
-- based on:
-- 1. Number of shared skills between mentee's interests and mentor's skills.
-- 2. Average mentor proficiency score in those matched skills.
-- 3. Overall average mentor rating from past evaluations.
-- 4. Filtering out mentors who have reached their maximum active capacity (e.g. 5 active relations).
--
-- Relational operations demonstrated:
-- - Multi-table INNER JOIN (`users`, `user_skills`)
-- - LEFT JOIN with nested aggregated derived table (`reviews_and_ratings`)
-- - LEFT JOIN with filtered relationship table (`mentorship_relations`)
-- - Correlated / Nested subquery in WHERE clause (`WHERE us.skill_id IN (SELECT ...)`)
-- - Nested subquery with HAVING clause to enforce capacity bounds
-- - CASE expression for categorical-to-numeric scale conversion
-- - Aggregation functions (`COUNT`, `ROUND`, `AVG`, `COALESCE`)
-- - `GROUP BY`, `HAVING`, and multi-column `ORDER BY`
-- =====================================================================

SET @target_mentee_id = 6;

SELECT 
    m.id AS mentor_id,
    CONCAT(m.first_name, ' ', m.last_name) AS mentor_name,
    m.current_title,
    m.organization,
    COUNT(DISTINCT us.skill_id) AS matched_skills_count,
    ROUND(AVG(CASE 
        WHEN us.proficiency = 'EXPERT' THEN 4
        WHEN us.proficiency = 'ADVANCED' THEN 3
        WHEN us.proficiency = 'INTERMEDIATE' THEN 2
        ELSE 1 
    END), 2) AS avg_skill_score,
    COALESCE(r.avg_rating, 0.0) AS mentor_rating,
    COUNT(DISTINCT rel.id) AS active_mentees_count
FROM users m
JOIN user_skills us ON m.id = us.user_id
LEFT JOIN (
    SELECT reviewee_id, ROUND(AVG(rating), 2) AS avg_rating
    FROM reviews_and_ratings
    GROUP BY reviewee_id
) r ON m.id = r.reviewee_id
LEFT JOIN mentorship_relations rel 
    ON m.id = rel.mentor_id AND rel.status = 'ACTIVE'
WHERE m.role = 'MENTOR'
  AND us.skill_id IN (
      SELECT skill_id 
      FROM user_skills 
      WHERE user_id = @target_mentee_id
  )
  AND m.id NOT IN (
      -- Subquery to exclude overloaded mentors
      SELECT mentor_id 
      FROM mentorship_relations 
      WHERE status = 'ACTIVE' 
      GROUP BY mentor_id 
      HAVING COUNT(*) >= 5
  )
GROUP BY 
    m.id, 
    m.first_name, 
    m.last_name, 
    m.current_title, 
    m.organization, 
    r.avg_rating
HAVING matched_skills_count >= 1
ORDER BY 
    matched_skills_count DESC, 
    avg_skill_score DESC, 
    mentor_rating DESC;


-- =====================================================================
-- COMPLEX QUERY 2: Mentor Leaderboard & Engagement Metrics
-- ---------------------------------------------------------------------
-- Purpose:
-- Computes the public mentor leaderboard showing mentors ranked by:
-- 1. Average review rating.
-- 2. Total completed meetings held.
-- 3. Total active and completed mentorship relations.
--
-- Relational operations demonstrated:
-- - INNER JOIN across core entities (`users`, `mentorship_relations`)
-- - Multiple conditional LEFT JOINs (`meetings`, `reviews_and_ratings`)
-- - Conditional aggregation using `SUM(CASE WHEN ...)`
-- - Aggregation functions (`COUNT(DISTINCT ...)`, `AVG(...)`, `COALESCE(...)`)
-- - `GROUP BY` with composite columns and `HAVING` clause
-- =====================================================================

SELECT 
    u.id AS mentor_id,
    CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
    u.current_title,
    u.organization,
    COUNT(DISTINCT mr.id) AS total_mentorships,
    SUM(CASE WHEN mr.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_mentorships,
    SUM(CASE WHEN mr.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_mentorships,
    COUNT(DISTINCT m.id) AS total_meetings_held,
    COALESCE(ROUND(AVG(rr.rating), 2), 0.0) AS avg_rating,
    COUNT(DISTINCT rr.id) AS total_reviews_received
FROM users u
JOIN mentorship_relations mr ON u.id = mr.mentor_id
LEFT JOIN meetings m ON mr.id = m.relation_id AND m.status = 'COMPLETED'
LEFT JOIN reviews_and_ratings rr ON mr.id = rr.relation_id AND rr.reviewee_id = u.id
WHERE u.role = 'MENTOR'
GROUP BY 
    u.id, 
    u.first_name, 
    u.last_name, 
    u.current_title, 
    u.organization
HAVING total_mentorships >= 1
ORDER BY 
    avg_rating DESC, 
    total_meetings_held DESC;


-- =====================================================================
-- COMPLEX QUERY 3: Mentee Goal Progress & Activity Correlation
-- ---------------------------------------------------------------------
-- Purpose:
-- For an individual mentee dashboard, displays each declared goal alongside:
-- 1. Whether a mentorship application targeting this goal was accepted.
-- 2. Number of completed mentorship sessions held under that relationship.
-- 3. The date of the most recent session.
--
-- Relational operations demonstrated:
-- - Outer join tree across 4 relational levels:
--   `mentorship_goals` -> `mentorship_applications` -> `mentorship_relations` -> `meetings`
-- - Aggregation functions (`COUNT(DISTINCT ...)`, `MAX(...)`)
-- - Filtering by parent user ID
-- - Temporal sorting by target date
-- =====================================================================

SET @target_mentee_id = 6;

SELECT 
    g.id AS goal_id,
    g.title AS goal_title,
    g.status AS goal_status,
    g.target_completion_date,
    COALESCE(CONCAT(mentor.first_name, ' ', mentor.last_name), 'No Mentor Yet') AS assigned_mentor,
    COUNT(DISTINCT mt.id) AS total_completed_sessions,
    MAX(mt.scheduled_start) AS latest_session_date
FROM mentorship_goals g
LEFT JOIN mentorship_applications ma 
    ON g.id = ma.goal_id AND ma.status = 'ACCEPTED'
LEFT JOIN mentorship_relations mr 
    ON ma.id = mr.application_id
LEFT JOIN users mentor 
    ON mr.mentor_id = mentor.id
LEFT JOIN meetings mt 
    ON mr.id = mt.relation_id AND mt.status = 'COMPLETED'
WHERE g.mentee_id = @target_mentee_id
GROUP BY 
    g.id, 
    g.title, 
    g.status, 
    g.target_completion_date, 
    mentor.first_name, 
    mentor.last_name
ORDER BY 
    g.target_completion_date ASC;


-- =====================================================================
-- COMPLEX QUERY 4: Mentor Weekly Utilization & Availability Analysis
-- ---------------------------------------------------------------------
-- Purpose:
-- Measures the workload utilization of mentors by contrasting their weekly
-- configured available hours against total hours scheduled for upcoming meetings.
--
-- Relational operations demonstrated:
-- - Two independent aggregated subqueries joined on mentor ID
-- - `TIMEDIFF` and `TIME_TO_SEC` date/time arithmetic calculations
-- - Subtraction and percentage ratio computation with `NULLIF`
-- =====================================================================

SELECT 
    u.id AS mentor_id,
    CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
    COALESCE(avail.total_available_hours_weekly, 0.0) AS weekly_available_hours,
    COALESCE(scheduled.total_scheduled_hours, 0.0) AS upcoming_scheduled_hours,
    ROUND(
        (COALESCE(scheduled.total_scheduled_hours, 0.0) / NULLIF(avail.total_available_hours_weekly, 0)) * 100, 
        1
    ) AS utilization_rate_pct
FROM users u
LEFT JOIN (
    SELECT 
        mentor_id,
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
    GROUP BY mr.mentor_id
) scheduled ON u.id = scheduled.mentor_id
WHERE u.role = 'MENTOR'
ORDER BY utilization_rate_pct DESC;

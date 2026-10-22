-- =====================================================================
-- BBF 302E Database Systems - Complex SQL Queries
-- Topic: Mentor–Mentee Matching Platform
-- Relational DBMS: MySQL 8.0+
-- Pure SQL queries with joins, aggregations, subqueries, and windowing
-- =====================================================================

USE mentor_platform;

-- =====================================================================
-- CQ-01: Personal Dashboard Summary & Activity Monitor
-- ---------------------------------------------------------------------
-- Responsible Member: Ravan Seyfullayev (150240928)
-- Tables Involved: users, notifications, mentorship_applications,
--                  mentorship_relations, meetings
--
-- Purpose:
-- For any authenticated user (mentor, mentee, or admin), computes an
-- aggregated executive snapshot in a single query:
-- 1. Total unread notifications awaiting acknowledgment.
-- 2. Pending applications involving the user (as applicant or recipient).
-- 3. Total active mentorship relationships.
-- 4. Number of upcoming confirmed sessions scheduled within the next 7 days.
--
-- Relational operations demonstrated:
-- - Correlated scalar subqueries referencing outer query entity
-- - Date/time arithmetic with interval filtering (`DATE_ADD`, `NOW()`)
-- - Multi-table INNER JOIN inside nested subquery
-- - Conditional aggregation and status filtering
-- =====================================================================

SET @target_user_id = 6;

SELECT 
    u.id AS user_id,
    CONCAT(u.first_name, ' ', u.last_name) AS full_name,
    u.email,
    u.role,
    (SELECT COUNT(*) 
     FROM notifications n 
     WHERE n.user_id = u.id AND n.is_read = FALSE) AS unread_notifications_count,
    (SELECT COUNT(*) 
     FROM mentorship_applications ma 
     WHERE (ma.mentee_id = u.id OR ma.mentor_id = u.id) 
       AND ma.status = 'PENDING') AS pending_applications_count,
    (SELECT COUNT(*) 
     FROM mentorship_relations mr 
     WHERE (mr.mentee_id = u.id OR mr.mentor_id = u.id) 
       AND mr.status = 'ACTIVE') AS active_mentorships_count,
    (SELECT COUNT(*) 
     FROM meetings m 
     JOIN mentorship_relations rel ON m.relation_id = rel.id 
     WHERE (rel.mentee_id = u.id OR rel.mentor_id = u.id)
       AND m.status = 'SCHEDULED'
       AND m.scheduled_start >= NOW()
       AND m.scheduled_start <= DATE_ADD(NOW(), INTERVAL 7 DAY)
    ) AS upcoming_meetings_next_7_days
FROM users u
WHERE u.id = @target_user_id;


-- =====================================================================
-- CQ-02: Multi-Criteria Mentor Recommendation Engine
-- ---------------------------------------------------------------------
-- Responsible Member: Denils Mahmuti (150230984)
-- Tables Involved: users, user_skills, skills, reviews_and_ratings,
--                  mentorship_relations
--
-- Purpose:
-- Given a mentee ID, rank suitable mentors matching mentee's skill targets:
-- 1. Count of overlapping skills between mentee's profile and mentor's skills.
-- 2. Weighted average proficiency score across matched skills (EXPERT=4 .. BEGINNER=1).
-- 3. Overall historical average rating of the mentor.
-- 4. Exclusion of mentors who have reached maximum active capacity (e.g. >= 5 active mentees).
--
-- Relational operations demonstrated:
-- - Multi-table INNER JOIN (`users`, `user_skills`)
-- - LEFT JOIN with pre-aggregated derived table (`reviews_and_ratings`)
-- - LEFT JOIN with filtered active relationship set (`mentorship_relations`)
-- - Correlated / Nested subquery in WHERE clause (`WHERE us.skill_id IN (SELECT ...)`)
-- - Subquery with HAVING clause to filter out overloaded mentors
-- - CASE expression for categorical-to-numeric scale conversion
-- - Aggregations (`COUNT(DISTINCT ...)`, `AVG(...)`, `COALESCE(...)`, `ROUND(...)`)
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
      -- Exclude mentors at or above capacity
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
-- CQ-03: Mentee Goal Progress & Activity Correlation
-- ---------------------------------------------------------------------
-- Responsible Member: Abdullokhon Valikhonov (150240942)
-- Tables Involved: mentorship_goals, mentorship_applications,
--                  mentorship_relations, users, meetings
--
-- Purpose:
-- For a mentee's personalized goal tracker, displays every declared learning
-- goal alongside:
-- 1. Assigned mentor name (if an application was accepted into a relationship).
-- 2. Total completed sessions held under that active or completed relationship.
-- 3. Date of the most recent completed mentoring session.
-- 4. Current goal status and days remaining until target completion date.
--
-- Relational operations demonstrated:
-- - Multi-tier outer join tree across 5 tables:
--   `mentorship_goals` -> `mentorship_applications` -> `mentorship_relations` -> `users` -> `meetings`
-- - Aggregation functions (`COUNT(DISTINCT ...)`, `MAX(...)`)
-- - Date calculation (`DATEDIFF`)
-- - Multi-column `GROUP BY` and temporal ordering
-- =====================================================================

SET @target_mentee_id = 6;

SELECT 
    g.id AS goal_id,
    g.title AS goal_title,
    g.status AS goal_status,
    g.target_completion_date,
    DATEDIFF(g.target_completion_date, CURRENT_DATE) AS days_until_target,
    COALESCE(CONCAT(mentor.first_name, ' ', mentor.last_name), 'No Mentor Assigned') AS assigned_mentor,
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
-- CQ-04: Mentor Weekly Utilization & Availability Analysis
-- ---------------------------------------------------------------------
-- Responsible Member: Gaffar Dulkadir (150210306)
-- Tables Involved: users, mentor_availability, mentorship_relations, meetings
--
-- Purpose:
-- Computes the scheduling load factor and availability utilization for each
-- mentor, contrasting weekly published availability hours against upcoming
-- scheduled meeting hours.
--
-- Relational operations demonstrated:
-- - Independent aggregated subqueries joined to the base mentor record
-- - Date/time arithmetic functions (`TIMEDIFF`, `TIME_TO_SEC`, `TIMESTAMPDIFF`)
-- - Safe division using `NULLIF` to guard against zero-division errors
-- - Sorting by highest utilization rate to identify mentor bottlenecks
-- =====================================================================

SELECT 
    u.id AS mentor_id,
    CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
    u.current_title,
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


-- =====================================================================
-- CQ-05: Mentor Leaderboard & Multi-Dimensional Performance Analytics
-- ---------------------------------------------------------------------
-- Responsible Member: Raimbek Erik (150230932)
-- Tables Involved: users, mentorship_relations, meetings, reviews_and_ratings
--
-- Purpose:
-- Drives the platform-wide public mentor leaderboard, ranking mentors based
-- on multidimensional performance metrics:
-- 1. Average review rating from post-session feedback.
-- 2. Total completed mentoring sessions held.
-- 3. Total active and completed mentorship relations.
-- 4. Count of unique reviews received.
--
-- Relational operations demonstrated:
-- - INNER JOIN to active or historic mentorship relations
-- - Multiple conditional LEFT JOINs for meetings and reviews
-- - Conditional aggregation via `SUM(CASE WHEN ...)`
-- - Aggregation functions (`COUNT(DISTINCT ...)`, `AVG(...)`, `COALESCE(...)`)
-- - `GROUP BY` with composite columns and `HAVING` threshold
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

# BBF 302E Database Systems — Fall 2026
## Term Project Proposal: Milestone 1

---

### Project Topic
**Mentor–Mentee Matching Platform**  
*A web-based database system connecting mentees seeking academic, career, and technical guidance with experienced mentors, featuring skill matching, goal tracking, availability-based scheduling, meeting logging, and bidirectional reviews.*

---

### 1. Group Formation & Roles

The project team consists of 5 members. Each member is assigned a dedicated functional domain and is individually responsible for the design, implementation, and maintenance of **two database tables**, including their associated CRUD operations, SQL queries, Flask routes, and Jinja2 views.

| Member | Name & Student ID | Project Role | Assigned Database Tables |
| :--- | :--- | :--- | :--- |
| **Member 1 (Team Leader)** | `[Student Name 1]`<br>`[Student ID 1]` | System Architect & Authentication Lead | `users`<br>`notifications` |
| **Member 2** | `[Student Name 2]`<br>`[Student ID 2]` | Taxonomy & Matching Lead | `skills`<br>`user_skills` |
| **Member 3** | `[Student Name 3]`<br>`[Student ID 3]` | Applications & Goals Lead | `mentorship_goals`<br>`mentorship_applications` |
| **Member 4** | `[Student Name 4]`<br>`[Student ID 4]` | Relations & Scheduling Lead | `mentorship_relations`<br>`mentor_availability` |
| **Member 5** | `[Student Name 5]`<br>`[Student ID 5]` | Sessions, Reviews & Analytics Lead | `meetings`<br>`reviews_and_ratings`<br>*(aux: `meeting_notes`)* |

---

### 2. Project Rationale & Data Overview

#### 2.1 Why a Relational Database is Necessary
A modern mentorship platform cannot be effectively implemented using simple flat files or unstructured document stores due to the deeply interconnected nature of mentorship relationships:
1. **Relational Integrity and Foreign Key Constraints**: An application links a mentee, mentor, and specific goal. A relationship links an accepted application. A meeting links an active relationship. A review links participants of a completed relationship. A relational DBMS guarantees referential integrity so that child records are never orphaned and state inconsistencies are prevented.
2. **ACID Transaction Guarantees**: Scheduling a meeting requires checking availability windows and preventing duplicate bookings for the same mentor time slot concurrently. Relational database transactions guarantee isolation and atomicity.
3. **No ORM Requirement & Query Optimization**: To adhere to the course requirement prohibiting ORMs, our architecture utilizes parameterized raw SQL. Relational indexes (on `users.email`, `user_skills.skill_id`, `mentorship_relations.status`, etc.) guarantee efficient join resolution.
4. **Complex Aggregations & Analytics**: Calculating mentor ratings (`AVG(rating)`), skill match percentages, meeting hours, and platform activity metrics requires multi-table relational joins and grouping operations.

#### 2.2 Overview of Stored Data
The platform manages and persists:
- **User Accounts & Authentication**: Credentials (bcrypt hashes), role designations (`MENTEE`, `MENTOR`, `ADMIN`), biographies, titles, and institutions.
- **Skills Directory & Expertise**: Standardized taxonomy of technical and professional skills, mapped to users with discrete proficiency levels (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `EXPERT`) and years of experience.
- **Goals & Milestone Tracking**: Objectives formulated by mentees, target completion dates, and achievement statuses.
- **Applications & Decisions**: Formal mentee applications with motivation statements, submitted to specific mentors, tracking decision status (`PENDING`, `ACCEPTED`, `REJECTED`, `WITHDRAWN`).
- **Formal Mentorship Relationships**: Active or archived pairs with start/end dates, state flags, and supervision notes.
- **Availability Schedules**: Mentor-defined recurring weekly availability windows (day of week, start time, end time).
- **Meetings & Sessions**: Scheduled 1-on-1 sessions, virtual meeting links, agendas, completion statuses, and cancellations.
- **Meeting Notes**: Post-session minutes and shared actionable follow-up items.
- **Reviews & Ratings**: Quantitative 1–5 star ratings and qualitative feedback exchanged between parties.
- **Notifications**: Automated alerts triggered by application submissions, approvals, meeting reminders, and reviews.

---

### 3. Requirements Engineering

#### 3.1 Functional Requirements (FR)

| ID | Requirement Description | Responsible Member |
| :--- | :--- | :--- |
| **FR-01** | **User Registration & Role Selection**: The system must allow users to register with email, secure password, name, and role (`MENTEE`, `MENTOR`). | `[Student Name 1]` |
| **FR-02** | **Authentication & Session Management**: The system must verify credentials, manage secure sessions, and enforce role-based access control (RBAC). | `[Student Name 1]` |
| **FR-03** | **User Profile & Notifications**: Users can update bio, organization, and title. The system notifies users upon application decisions and upcoming meetings. | `[Student Name 1]` |
| **FR-04** | **Skill Catalog Management**: Admins can create and categorize skills. Users can browse available skills across categories. | `[Student Name 2]` |
| **FR-05** | **User Skill Endorsement & Proficiency**: Mentors and mentees can attach skills to their profile with proficiency level and experience years. | `[Student Name 2]` |
| **FR-06** | **Mentor Search & Multi-Skill Filtering**: Mentees can search and filter mentors by skill category, keyword, and minimum required proficiency. | `[Student Name 2]` |
| **FR-07** | **Mentorship Goal Formulation**: Mentees can define specific learning goals with descriptions, target dates, and statuses. | `[Student Name 3]` |
| **FR-08** | **Application Submission**: Mentees can submit formal applications to mentors, selecting a target goal and writing a statement of intent. | `[Student Name 3]` |
| **FR-09** | **Mentor Application Review**: Mentors can view received applications with mentee goals and skills, and accept or reject with optional remarks. | `[Student Name 3]` |
| **FR-10** | **Relationship Lifecycle Management**: Accepting an application automatically instantiates a formal relationship; users can pause, complete, or terminate it. | `[Student Name 4]` |
| **FR-11** | **Mentor Availability Slots**: Mentors can define recurring weekly availability windows (day of week, start/end time) and toggle active status. | `[Student Name 4]` |
| **FR-12** | **Meeting Scheduling & Slot Booking**: Mentees can book sessions with their active mentor matching the mentor's defined availability windows. | `[Student Name 5]` |
| **FR-13** | **Meeting Status & Cancellation**: Both parties can update meeting status (Completed, Cancelled with mandatory reason, No-show). | `[Student Name 5]` |
| **FR-14** | **Session Notes & Action Items**: Participants can record discussion summaries and actionable next steps linked to a specific meeting. | `[Student Name 5]` |
| **FR-15** | **Bidirectional Reviews & Mentor Leaderboard**: Both parties can submit 1–5 star reviews upon relationship or session completion; public leaderboard displays ranked mentors. | `[Student Name 5]` |

#### 3.2 Non-Functional Requirements (NFR)

| ID | Requirement Description | Metric / Standard | Responsible Member |
| :--- | :--- | :--- | :--- |
| **NFR-01** | **Security & Hashing** | Passwords stored with salted bcrypt/Argon2 hashes; session cookies protected with `HttpOnly` and `SameSite` flags. | `[Student Name 1]` |
| **NFR-02** | **SQL Injection Prevention** | 100% of database interactions execute strictly through parameterized SQL statements without string concatenation. | `[Student Name 1]` |
| **NFR-03** | **Query Response Performance** | Core search and listing queries execute under 100ms via indexed foreign keys and lookup columns. | `[Student Name 2]` |
| **NFR-04** | **Data Integrity & Constraints** | Strict relational foreign keys with `ON DELETE RESTRICT` or `CASCADE`, unique constraints on email and skill names, and enum domains. | `[Student Name 3]` |
| **NFR-05** | **Concurrent Booking Prevention** | Database transaction isolation prevents overlapping meetings for the same mentor within the same time slot. | `[Student Name 4]` |
| **NFR-06** | **Usability & Clean Interface** | Web application styled with clean, accessible Jinja2 templates and Bootstrap 5 without reliance on complex frontend build chains. | `[Student Name 5]` |

---

### 4. Data Requirements & Schema Structure (11 Tables)

Each student is responsible for 2 primary tables:

#### Member 1 Tables:
1. `users`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `email` (VARCHAR(150), UNIQUE, NOT NULL)
   - `password_hash` (VARCHAR(255), NOT NULL)
   - `first_name` (VARCHAR(60), NOT NULL)
   - `last_name` (VARCHAR(60), NOT NULL)
   - `role` (ENUM('MENTEE', 'MENTOR', 'ADMIN'), NOT NULL)
   - `bio` (TEXT)
   - `current_title` (VARCHAR(100))
   - `organization` (VARCHAR(100))
   - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
2. `notifications`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `user_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `title` (VARCHAR(150), NOT NULL)
   - `message` (TEXT, NOT NULL)
   - `is_read` (BOOLEAN, DEFAULT FALSE)
   - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)

#### Member 2 Tables:
3. `skills`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `name` (VARCHAR(80), UNIQUE, NOT NULL)
   - `category` (VARCHAR(60), NOT NULL) — e.g. Programming, Career, Data, Cloud
   - `description` (TEXT)
4. `user_skills`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `user_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `skill_id` (INT, FK -> `skills.id`, ON DELETE CASCADE)
   - `proficiency` (ENUM('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'), NOT NULL)
   - `years_of_experience` (INT, DEFAULT 0)
   - UNIQUE KEY (`user_id`, `skill_id`)

#### Member 3 Tables:
5. `mentorship_goals`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `mentee_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `title` (VARCHAR(150), NOT NULL)
   - `description` (TEXT)
   - `target_completion_date` (DATE)
   - `status` (ENUM('ACTIVE', 'ACHIEVED', 'ABANDONED'), DEFAULT 'ACTIVE')
   - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
6. `mentorship_applications`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `mentee_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `mentor_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `goal_id` (INT, FK -> `mentorship_goals.id`, ON DELETE SET NULL)
   - `message` (TEXT, NOT NULL)
   - `status` (ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN'), DEFAULT 'PENDING')
   - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
   - `decided_at` (DATETIME, NULL)

#### Member 4 Tables:
7. `mentorship_relations`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `application_id` (INT, FK -> `mentorship_applications.id`, UNIQUE)
   - `mentee_id` (INT, FK -> `users.id`, ON DELETE RESTRICT)
   - `mentor_id` (INT, FK -> `users.id`, ON DELETE RESTRICT)
   - `start_date` (DATE, NOT NULL)
   - `end_date` (DATE, NULL)
   - `status` (ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED'), DEFAULT 'ACTIVE')
   - `notes` (TEXT)
8. `mentor_availability`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `mentor_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
   - `day_of_week` (TINYINT NOT NULL) — 0 = Monday, ..., 6 = Sunday
   - `start_time` (TIME, NOT NULL)
   - `end_time` (TIME, NOT NULL)
   - `is_active` (BOOLEAN, DEFAULT TRUE)

#### Member 5 Tables:
9. `meetings`
   - `id` (INT, PK, AUTO_INCREMENT)
   - `relation_id` (INT, FK -> `mentorship_relations.id`, ON DELETE CASCADE)
   - `scheduled_start` (DATETIME, NOT NULL)
   - `scheduled_end` (DATETIME, NOT NULL)
   - `meeting_link` (VARCHAR(255))
   - `agenda` (TEXT)
   - `status` (ENUM('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW'), DEFAULT 'SCHEDULED')
   - `cancellation_reason` (VARCHAR(255))
10. `reviews_and_ratings`
    - `id` (INT, PK, AUTO_INCREMENT)
    - `relation_id` (INT, FK -> `mentorship_relations.id`, ON DELETE CASCADE)
    - `reviewer_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
    - `reviewee_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
    - `rating` (TINYINT NOT NULL) — CHECK (rating BETWEEN 1 AND 5)
    - `review_text` (TEXT)
    - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
    - UNIQUE KEY (`relation_id`, `reviewer_id`, `reviewee_id`)
11. `meeting_notes` *(Auxiliary Table)*
    - `id` (INT, PK, AUTO_INCREMENT)
    - `meeting_id` (INT, FK -> `meetings.id`, ON DELETE CASCADE)
    - `author_id` (INT, FK -> `users.id`, ON DELETE CASCADE)
    - `summary` (TEXT NOT NULL)
    - `action_items` (TEXT)
    - `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)

---

### 5. CRUD Operations & Query Specifications

Every member implements complete CRUD operations for their assigned tables:

#### Member 1 (`users`, `notifications`)
- **Create**: Register new user; generate system notifications.
- **Read**: Fetch profile details by ID; list user's unread notifications.
- **Update**: Edit bio, current role/title, and organization; mark notifications as read.
- **Delete**: Delete user profile (triggering cascading rules); dismiss individual notifications.

#### Member 2 (`skills`, `user_skills`)
- **Create**: Add new skill to taxonomy; associate skill to user with proficiency.
- **Read**: List all categorized skills; search mentors by multiple skill IDs.
- **Update**: Modify skill definition; update proficiency and years of experience.
- **Delete**: Remove skill from taxonomy (admin); remove skill from user profile.

#### Member 3 (`mentorship_goals`, `mentorship_applications`)
- **Create**: Define new mentee goal; submit application from mentee to mentor.
- **Read**: List mentee's active goals; view received/sent applications filtered by status.
- **Update**: Update goal progress/target date; update application status (`ACCEPTED`/`REJECTED`).
- **Delete**: Delete goal; withdraw pending application.

#### Member 4 (`mentorship_relations`, `mentor_availability`)
- **Create**: Instantiate relationship upon application acceptance; add weekly availability window.
- **Read**: View active mentorship pairs; fetch available weekly slots for a mentor.
- **Update**: Transition relationship status (`ACTIVE` -> `COMPLETED`/`TERMINATED`); edit availability hours.
- **Delete**: End/archive relationship; delete unused availability window.

#### Member 5 (`meetings`, `reviews_and_ratings`, `meeting_notes`)
- **Create**: Schedule new meeting session; submit post-meeting review; write meeting notes.
- **Read**: List upcoming/past meetings; view mentor reviews; read meeting notes.
- **Update**: Reschedule meeting; record cancellation reason; edit draft meeting notes.
- **Delete**: Cancel meeting; remove meeting note.

---

### 6. Complex SQL Queries Planned

#### Query 1: Multi-Criteria Mentor Recommendation Engine
Matches a mentee seeking a set of target skills against mentors, computing a weighted compatibility score based on mentor proficiency, availability match, and past reviews:
```sql
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
        ELSE 1 END), 2) AS avg_skill_score,
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
      SELECT skill_id FROM user_skills WHERE user_id = %s -- mentee_id
  )
  AND m.id NOT IN (
      SELECT mentor_id FROM mentorship_relations 
      WHERE status = 'ACTIVE' 
      GROUP BY mentor_id HAVING COUNT(*) >= 5 -- Max capacity limit
  )
GROUP BY m.id, m.first_name, m.last_name, m.current_title, m.organization, r.avg_rating
HAVING matched_skills_count >= 1
ORDER BY matched_skills_count DESC, avg_skill_score DESC, mentor_rating DESC;
```

#### Query 2: Mentor Leaderboard & Engagement Metrics
Aggregates activity, completion rate, and satisfaction across relations, meetings, and reviews:
```sql
SELECT 
    u.id AS mentor_id,
    CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
    u.organization,
    COUNT(DISTINCT mr.id) AS total_mentorships,
    SUM(CASE WHEN mr.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_mentorships,
    COUNT(DISTINCT m.id) AS total_meetings_held,
    COALESCE(ROUND(AVG(rr.rating), 2), 0.0) AS avg_rating,
    COUNT(DISTINCT rr.id) AS total_reviews
FROM users u
JOIN mentorship_relations mr ON u.id = mr.mentor_id
LEFT JOIN meetings m ON mr.id = m.relation_id AND m.status = 'COMPLETED'
LEFT JOIN reviews_and_ratings rr ON mr.id = rr.relation_id AND rr.reviewee_id = u.id
WHERE u.role = 'MENTOR'
GROUP BY u.id, u.first_name, u.last_name, u.organization
HAVING total_mentorships >= 1
ORDER BY avg_rating DESC, total_meetings_held DESC;
```

#### Query 3: Mentee Goal Progress & Activity Correlation
Tracks goal execution rates by correlating mentee targets with scheduled sessions:
```sql
SELECT 
    g.id AS goal_id,
    g.title AS goal_title,
    g.status AS goal_status,
    g.target_completion_date,
    COUNT(DISTINCT mt.id) AS total_meetings_held,
    MAX(mt.scheduled_start) AS latest_meeting_date
FROM mentorship_goals g
LEFT JOIN mentorship_applications ma ON g.id = ma.goal_id AND ma.status = 'ACCEPTED'
LEFT JOIN mentorship_relations mr ON ma.id = mr.application_id
LEFT JOIN meetings mt ON mr.id = mt.relation_id AND mt.status = 'COMPLETED'
WHERE g.mentee_id = %s
GROUP BY g.id, g.title, g.status, g.target_completion_date
ORDER BY g.target_completion_date ASC;
```

---

### 7. Version Control & Contribution Policy

1. **Shared GitHub Repository**: The codebase will be hosted on a shared GitHub repository with all 5 members granted Collaborator access.
2. **Feature Branch Workflow**: Each member develops their assigned tables and routes in isolated feature branches (e.g., `feature/member1-auth`, `feature/member2-skills`, etc.).
3. **Commit Standards**: Each member commits using their individual GitHub account with descriptive conventional commit messages (e.g. `feat(skills): add raw SQL search query with proficiency filter`).
4. **Code Reviews & Pull Requests**: No member commits code on another's behalf. Merges into `main` require review and verification against SQL guidelines (ensuring raw SQL without ORM).

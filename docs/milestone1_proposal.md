# BBF 302E Database Systems — Fall 2026
## Term Project Proposal: Milestone 1

---

### Team Information
- **Team Name**: Black Swan
- **Selected Project Topic**: Mentor–Mentee Matching Platform
- **Topic Registered in Mapping Document**: Yes
- **Course Sections**: Gaffar Dulkadir is in section 12495 (assigned by TAs); all other members are in section 15742.

---

### 1. Group Formation & Roles

| # | Full Name | Student ID | Section | Role in Team | E-mail (ITU) | Assigned Database Tables |
| :-: | :--- | :--- | :-: | :--- | :--- | :--- |
| **1** | **Gaffar Dulkadir** | 150210306 | 12495 | **Team Leader** &bull; Mentorship Relationship & Availability Management | `dulkadir21@itu.edu.tr` | `mentorship_relations`<br>`mentor_availability` |
| **2** | **Denils Mahmuti** | 150230984 | 15742 | Skill Management & Mentor Discovery | `mahmuti23@itu.edu.tr` | `skills`<br>`user_skills` |
| **3** | **Ravan Seyfullayev** | 150240928 | 15742 | Authentication, User Profiles & Notification System | `seyfullayev24@itu.edu.tr` | `users`<br>`notifications` |
| **4** | **Abdullokhon Valikhonov** | 150240942 | 15742 | Mentorship Goals & Application Management | `valikhonov24@itu.edu.tr` | `mentorship_goals`<br>`mentorship_applications` |
| **5** | **Raimbek Erik** | 150230932 | 15742 | Meeting, Session Notes & Review Management | `erik23@itu.edu.tr` | `meetings`<br>`reviews_and_ratings`<br>*(aux: `meeting_notes`)* |

---

### 2. Project Overview & Rationale

#### 2.1 Project Description
The **Mentor–Mentee Matching Platform** is a web-based database system that connects mentees seeking academic, career, and technical guidance with experienced mentors. Finding the right mentor is usually informal and unstructured; our system makes it systematic by matching people on skills, proficiency levels, goals, and availability, while keeping the entire mentorship lifecycle in one place.

- **Mentees**: Build a profile with skills, define learning goals, search and filter mentors, and send formal applications.
- **Mentors**: Review applications, publish recurring weekly availability windows, conduct 1-on-1 sessions, and log meeting notes.
- **Relationships**: Accepted applications turn into formal mentorship relationships whose meetings, notes, and bidirectional 1–5 star reviews are tracked over time.
- **Administrators**: Manage the skill taxonomy and user accounts; a public leaderboard ranks mentors by rating and engagement.
- **Technology**: Built with **Flask**, **Jinja2 templates**, and **raw parameterized SQL (strictly no ORM)** running against **MySQL 8**.

#### 2.2 Why Does This Project Need a Database?
A mentorship platform cannot be implemented reliably with flat files or unstructured document stores because its data is deeply interconnected:
1. **Relational Integrity**: An application links a mentee, mentor, and specific goal; a relationship links an accepted application; a meeting links an active relationship; a review links the participants of a relationship. Foreign key constraints guarantee child records are never orphaned and states stay consistent.
2. **Concurrent Access & ACID Transactions**: Multiple users act simultaneously. Booking a meeting requires checking the mentor's availability and preventing two mentees from booking the same slot concurrently; transactions provide atomicity and isolation.
3. **Querying with Raw SQL**: The course forbids ORMs, so all access is through parameterized SQL. Indexes on lookup and foreign key columns (`users.email`, `user_skills.skill_id`, `mentorship_relations.status`, etc.) ensure join efficiency.
4. **Reporting & Analytics**: Mentor ratings (`AVG`), skill-match scores, meeting counts, and platform activity metrics all require multi-table joins, grouping, and aggregation handled natively by a relational DBMS.

#### 2.3 Overview of Stored Data
- **User Accounts**: Salted bcrypt password hashes, role (`MENTEE`, `MENTOR`, `ADMIN`), name, biography, title, and organization.
- **Skills and Expertise**: Standardized skill taxonomy by category, mapped to users with discrete proficiency levels (`BEGINNER` to `EXPERT`) and years of experience.
- **Goals**: Mentee objectives with descriptions, target completion dates, and status (`ACTIVE`, `ACHIEVED`, `ABANDONED`).
- **Applications**: Mentee-to-mentor applications with a motivation message, target goal, and decision status (`PENDING`, `ACCEPTED`, `REJECTED`, `WITHDRAWN`).
- **Mentorship Relationships**: Active or archived mentor–mentee pairs with start/end dates, status, and supervision notes.
- **Availability**: Recurring weekly mentor availability windows (day of week, start time, end time).
- **Meetings & Meeting Notes**: Scheduled sessions, meeting links, agendas, status, cancellation reasons, post-session summaries, and action items.
- **Reviews & Notifications**: 1–5 star ratings with written feedback, and system alerts for applications, decisions, meeting reminders, and reviews.

---

### 3. User Roles

| Role | Description | Permissions & Capabilities |
| :--- | :--- | :--- |
| **Admin** | Platform & System Manager | Full CRUD on all tables; create/edit/delete skills in taxonomy; manage user accounts; view platform-wide analytics. |
| **Mentor** | Experienced Guidance Provider | Edit profile & skills; review and accept/reject applications; manage availability windows; manage relationships, meetings, and meeting notes; review mentees. |
| **Mentee** | Guidance Seeker | Edit profile & skills; create goals; search mentors; submit/withdraw applications; book and cancel meetings; write meeting notes; review mentors. |
| **Guest** | Unauthenticated Visitor | View public mentor leaderboard and skill catalog; register; log in. |

---

### 4. Functional Requirements (FR)

| ID | Requirement Description | User Role(s) | Related Table(s) | CRUD | Responsible Member |
| :-: | :--- | :--- | :--- | :-: | :--- |
| **FR-01** | **User Registration & Role Selection**: Register with email, password, name, and role (`MENTEE` or `MENTOR`). | Guest | `users` | C | **Ravan Seyfullayev** |
| **FR-02** | **Authentication & Session Management**: Verify credentials, manage secure sessions, and enforce role-based access control. | All | `users` | R | **Ravan Seyfullayev** |
| **FR-03** | **User Profile & Notifications**: Update bio, organization, title; system notifies users about decisions and upcoming meetings. | Mentee, Mentor | `users`, `notifications` | C, R, U, D | **Ravan Seyfullayev** |
| **FR-04** | **Skill Catalog Management**: Admins create and categorize skills; users browse skills by category. | Admin, All | `skills` | C, R, U, D | **Denils Mahmuti** |
| **FR-05** | **User Skills & Proficiency**: Mentors and mentees attach skills to profile with proficiency level and experience years. | Mentee, Mentor | `user_skills`, `skills` | C, R, U, D | **Denils Mahmuti** |
| **FR-06** | **Mentor Search & Multi-Skill Filtering**: Mentees search and filter mentors by skill category, keyword, and minimum proficiency. | Mentee | `users`, `user_skills`, `skills` | R | **Denils Mahmuti** |
| **FR-07** | **Goal Formulation**: Mentees define learning goals with description, target date, and status. | Mentee | `mentorship_goals` | C, R, U, D | **Abdullokhon Valikhonov** |
| **FR-08** | **Application Submission**: Mentees submit applications to mentors selecting a goal and motivation; withdraw or delete pending applications. | Mentee | `mentorship_applications`, `mentorship_goals` | C, R, U, D | **Abdullokhon Valikhonov** |
| **FR-09** | **Application Review**: Mentors view received applications with mentee goals and skills and accept or reject them. | Mentor | `mentorship_applications`, `user_skills` | R, U | **Abdullokhon Valikhonov** |
| **FR-10** | **Relationship Lifecycle**: Accepting an application creates a relationship; users can pause, complete, or terminate it. | Mentor, Mentee, Admin | `mentorship_relations`, `mentorship_applications` | C, R, U, D | **Gaffar Dulkadir** |
| **FR-11** | **Mentor Availability**: Mentors define recurring weekly availability windows and toggle active status. | Mentor | `mentor_availability` | C, R, U, D | **Gaffar Dulkadir** |
| **FR-12** | **Meeting Scheduling**: Mentees book sessions with their active mentor inside the mentor's availability windows. | Mentee | `meetings`, `mentor_availability`, `mentorship_relations` | C, R, U | **Raimbek Erik** |
| **FR-13** | **Meeting Status & Cancellation**: Mark meetings as Completed, Cancelled (with mandatory reason), or No-show; delete invalid records. | Mentee, Mentor, Admin | `meetings` | U, D | **Raimbek Erik** |
| **FR-14** | **Session Notes & Action Items**: Participants record discussion summaries and next steps linked to a meeting. | Mentee, Mentor | `meeting_notes`, `meetings` | C, R, U, D | **Raimbek Erik** |
| **FR-15** | **Bidirectional Reviews & Leaderboard**: Both parties submit, edit, or delete 1–5 star reviews; public leaderboard ranks mentors. | Mentee, Mentor, Guest | `reviews_and_ratings`, `mentorship_relations` | C, R, U, D | **Raimbek Erik** |

---

### 5. Non-Functional Requirements (NFR)

| ID | Category | Requirement Description | Responsible Member |
| :-: | :--- | :--- | :--- |
| **NFR-01** | **Security** | Passwords stored as salted bcrypt hashes; session cookies use `HttpOnly` and `SameSite` flags; protected routes redirect unauthenticated users to `/login`. | **Ravan Seyfullayev** |
| **NFR-02** | **Security** | 100% of database interactions use parameterized SQL statements; no query is built by string concatenation (SQL injection prevention). | **Ravan Seyfullayev** |
| **NFR-03** | **Performance** | Foreign keys and search columns (`skills.name`, `user_skills.skill_id`, `users.role`) indexed to maintain sub-100ms response time on catalog search. | **Denils Mahmuti** |
| **NFR-04** | **Data Integrity** | Foreign key constraints enforce referential integrity (`ON DELETE RESTRICT` on active relationships, `CASCADE` on notifications/skills, `SET NULL` on goals). | **Abdullokhon Valikhonov** |
| **NFR-05** | **Concurrency** | Transaction isolation prevents overlapping meeting bookings for the same mentor in the same time slot. | **Gaffar Dulkadir** |
| **NFR-06** | **Usability** | Web interface styled with Bootstrap 5 and Jinja2 templates, usable on both desktop and mobile viewports without external JS build chains. | **Raimbek Erik** |

---

### 6. Data Requirements & Schema Breakdown (11 Tables)

Each member is responsible for 2 distinct primary tables:

1. **Ravan Seyfullayev**:
   - `users`: `id (PK), email (UQ), password_hash, first_name, last_name, role, bio, current_title, organization, created_at`
   - `notifications`: `id (PK), user_id (FK), title, message, is_read, created_at`
2. **Denils Mahmuti**:
   - `skills`: `id (PK), name (UQ), category, description`
   - `user_skills`: `id (PK), user_id (FK), skill_id (FK), proficiency, years_of_experience`
3. **Abdullokhon Valikhonov**:
   - `mentorship_goals`: `id (PK), mentee_id (FK), title, description, target_completion_date, status, created_at`
   - `mentorship_applications`: `id (PK), mentee_id (FK), mentor_id (FK), goal_id (FK), message, status, created_at, decided_at`
4. **Gaffar Dulkadir**:
   - `mentorship_relations`: `id (PK), application_id (FK, UQ), mentee_id (FK), mentor_id (FK), start_date, end_date, status, notes`
   - `mentor_availability`: `id (PK), mentor_id (FK), day_of_week, start_time, end_time, is_active`
5. **Raimbek Erik**:
   - `meetings`: `id (PK), relation_id (FK), scheduled_start, scheduled_end, meeting_link, agenda, status, cancellation_reason`
   - `reviews_and_ratings`: `id (PK), relation_id (FK), reviewer_id (FK), reviewee_id (FK), rating, review_text, created_at`
   - `meeting_notes` *(Auxiliary Table)*: `id (PK), meeting_id (FK), author_id (FK), summary, action_items, created_at`

---

### 7. Planned Complex Queries

| ID | Query Name | Purpose and Involved Tables | Responsible Member |
| :-: | :--- | :--- | :--- |
| **CQ-01** | **Personal Dashboard Summary** | For the logged-in user: aggregates unread notifications, pending applications, active relationships, and meetings in the next 7 days (`users`, `notifications`, `mentorship_applications`, `mentorship_relations`, `meetings`). | **Ravan Seyfullayev** |
| **CQ-02** | **Mentor Recommendation Engine** | Ranks mentors for a mentee by number of matching skills, proficiency score, and average rating, excluding mentors at full capacity (`users`, `user_skills`, `reviews_and_ratings`, `mentorship_relations`). | **Denils Mahmuti** |
| **CQ-03** | **Goal Progress & Activity Correlation** | For each goal of a mentee: computes total completed meetings and latest session date (`mentorship_goals`, `mentorship_applications`, `mentorship_relations`, `meetings`). | **Abdullokhon Valikhonov** |
| **CQ-04** | **Availability Occupancy & Free-Slot Finder** | For each active weekly window of a mentor: calculates booked meetings and remaining free minutes in the next 7 days (`mentor_availability`, `mentorship_relations`, `meetings`). | **Gaffar Dulkadir** |
| **CQ-05** | **Mentor Leaderboard & Analytics** | Ranks mentors by average rating, total completed meetings, and active/completed mentorship counts (`users`, `mentorship_relations`, `meetings`, `reviews_and_ratings`). | **Raimbek Erik** |

---

### 8. Technology Stack Summary
- **Relational DBMS**: MySQL 8.0+
- **Driver**: `mysql-connector-python` using parameterized raw SQL (Strictly No ORM)
- **Web Framework**: Flask with server-side Jinja2 templates, HTML5, and Bootstrap 5
- **Authentication**: Session-based with bcrypt password hashing and role-based decorators (`MENTEE`, `MENTOR`, `ADMIN`)
- **Seeding**: Python Faker seeding script inserting records via parameterized SQL

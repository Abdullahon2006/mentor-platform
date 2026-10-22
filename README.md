# Mentor–Mentee Matching Platform

**BBF 302E Database Systems — Term Project (Fall 2026)**  
**Team**: Black Swan  
A relational database-driven web application connecting individuals seeking academic, technical, and career guidance with experienced mentors.

---

## 📌 Project Overview
Built strictly following the **BBF 302E Term Project Guidelines**:
- **Framework**: Flask (Python) with Jinja2 templates and Bootstrap 5.
- **Relational DBMS**: MySQL 8.0+.
- **Database Architecture**: **Strictly Raw Parameterized SQL (No ORM used)**.
- **Data Model**: 11 relational tables normalized to 3NF/BCNF.
- **Team Division**: 5 members, each responsible for 2 distinct tables and their respective CRUD operations, routes, and complex queries.

---

## 👥 Team Black Swan & Table Ownership Breakdown

| Member | Student ID | Section | Assigned Tables | Functional Domain |
| :--- | :-: | :-: | :--- | :--- |
| **Gaffar Dulkadir (Team Leader)** | 150210306 | 12495 | `mentorship_relations`<br>`mentor_availability` | Mentorship relationships state machine, recurring weekly availability scheduling (CQ-04). |
| **Denils Mahmuti** | 150230984 | 15742 | `skills`<br>`user_skills` | Standardized skill taxonomy, proficiency levels, user endorsements, multi-skill search and recommendation engine (CQ-02). |
| **Ravan Seyfullayev** | 150240928 | 15742 | `users`<br>`notifications` | Authentication (bcrypt), user profile management, session handling, notifications & personal dashboard summary (CQ-01). |
| **Abdullokhon Valikhonov** | 150240942 | 15742 | `mentorship_goals`<br>`mentorship_applications` | Mentee goal tracking, connection applications, mentor review workflow (Accept/Decline), goal progress correlation (CQ-03). |
| **Raimbek Erik** | 150230932 | 15742 | `meetings`<br>`reviews_and_ratings`<br>*(aux: `meeting_notes`)* | Meeting booking with conflict detection, session minutes & action items, 1-5 star reviews, mentor leaderboard (CQ-05). |

---

## 🚀 Quick Start Guide

### 1. Database Setup (MySQL 8.0)
Log in to your MySQL instance and run the schema and seed scripts:
```bash
mysql -u root -p < sql/01_schema.sql
mysql -u root -p < sql/02_seed_data.sql
```

### 2. Environment Configuration
Configure database connection variables in `.env`:
```bash
cp .env.example .env
# Edit DB_HOST, DB_USER, DB_PASSWORD, DB_NAME if needed
```

### 3. Install Dependencies & Run
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## 🔑 Demo Accounts
All seed accounts use the default password: **`password123`**
- **Mentor**: `dr.demir@techcorp.com` (Dr. Ahmet Demir - Principal Engineer)
- **Mentor**: `selin.kaya@ailabs.org` (Selin Kaya - Senior AI Scientist)
- **Mentee**: `ali.yilmaz@itu.edu.tr` (Ali Yilmaz - Junior CE Student)
- **Mentee**: `ayse.can@itu.edu.tr` (Ayse Can - Data Science Senior)
- **Admin**: `admin@itu.edu.tr` (System Administrator)

---

## 📊 Planned Complex Queries
1. **CQ-01 (Ravan)**: Personal Dashboard Summary (`users`, `notifications`, `mentorship_applications`, `mentorship_relations`, `meetings`).
2. **CQ-02 (Denils)**: Multi-Criteria Mentor Recommendation Engine (`users`, `user_skills`, `reviews_and_ratings`, `mentorship_relations`).
3. **CQ-03 (Abdullokhon)**: Mentee Goal Progress & Activity Correlation (`mentorship_goals`, `mentorship_applications`, `mentorship_relations`, `meetings`).
4. **CQ-04 (Gaffar)**: Availability Occupancy & Free-Slot Finder (`mentor_availability`, `mentorship_relations`, `meetings`).
5. **CQ-05 (Raimbek)**: Mentor Leaderboard & Engagement Metrics (`users`, `mentorship_relations`, `meetings`, `reviews_and_ratings`).

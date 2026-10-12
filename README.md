# Mentor–Mentee Matching Platform

**BBF 302E Database Systems — Term Project (Fall 2026)**  
A relational database-driven web application connecting individuals seeking academic, technical, and career guidance with experienced mentors.

---

## 📌 Project Overview
Built strictly following the **BBF 302E Term Project Guidelines**:
- **Framework**: Flask (Python) with Jinja2 templates and Bootstrap 5.
- **Relational DBMS**: MySQL 8.0+.
- **Database Architecture**: **Strictly Raw Parameterized SQL (No ORM used)**.
- **Data Model**: 11 relational tables normalized to 3NF/BCNF.
- **Team Division**: 5 members, each responsible for 2 distinct tables and their respective CRUD operations and view routes.

---

## 👥 Team & Table Ownership Breakdown

| Member | Assigned Tables | Functional Domain |
| :--- | :--- | :--- |
| **Member 1 (Team Leader)** | `users`, `notifications` | Authentication (bcrypt), user profile management, session handling, notifications & user dashboard. |
| **Member 2** | `skills`, `user_skills` | Standardized skill taxonomy, proficiency levels, user endorsements, multi-skill search and filtering. |
| **Member 3** | `mentorship_goals`, `mentorship_applications` | Mentee goal tracking, connection applications, mentor review workflow (Accept/Decline). |
| **Member 4** | `mentorship_relations`, `mentor_availability` | Formal relationship state machine, mentor recurring weekly availability windows. |
| **Member 5** | `meetings`, `reviews_and_ratings` *(aux: `meeting_notes`)* | Meeting booking with conflict detection, session minutes & action items, 1-5 star reviews, mentor leaderboard. |

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

## 📊 Complex SQL Queries Implemented
1. **Multi-Criteria Mentor Recommendation Engine** (`/recommendations`): Matches mentee's targeted skills with available mentors, calculating weighted proficiency scores while filtering out mentors at capacity.
2. **Mentor Leaderboard & Engagement Metrics** (`/leaderboard`): Aggregates activity across 4 tables with multi-table joins, grouped review ratings, and completed session counts.
3. **Mentee Goal Progress Correlation** (`/analytics/goals`): Tracks completion status of learning goals against scheduled and completed meetings.

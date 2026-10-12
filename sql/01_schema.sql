-- =====================================================================
-- BBF 302E Database Systems - Term Project Schema
-- Topic: Mentor–Mentee Matching Platform
-- Relational DBMS: MySQL 8.0+
-- Strict Guideline: Pure SQL DDL, Normalized to 3NF/BCNF, No ORM
-- =====================================================================

CREATE DATABASE IF NOT EXISTS mentor_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mentor_platform;

-- Disable foreign key checks during cleanup
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS meeting_notes;
DROP TABLE IF EXISTS reviews_and_ratings;
DROP TABLE IF EXISTS meetings;
DROP TABLE IF EXISTS mentor_availability;
DROP TABLE IF EXISTS mentorship_relations;
DROP TABLE IF EXISTS mentorship_applications;
DROP TABLE IF EXISTS mentorship_goals;
DROP TABLE IF EXISTS user_skills;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Table 1: users (Member 1)
-- Stores account credentials, core profile, and role-based access flag
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,
    role ENUM('MENTEE', 'MENTOR', 'ADMIN') NOT NULL DEFAULT 'MENTEE',
    bio TEXT,
    current_title VARCHAR(100),
    organization VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 2: notifications (Member 1)
-- In-app notifications for application status, meeting reminders, etc.
-- ---------------------------------------------------------------------
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_notifications_user_read (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 3: skills (Member 2)
-- Standardized taxonomy of technical and professional mentorship domains
-- ---------------------------------------------------------------------
CREATE TABLE skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    category VARCHAR(60) NOT NULL,
    description TEXT,
    INDEX idx_skills_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 4: user_skills (Member 2)
-- M:N junction table mapping users to skills with proficiency & experience
-- ---------------------------------------------------------------------
CREATE TABLE user_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency ENUM('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT') NOT NULL,
    years_of_experience INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_user_skills_user FOREIGN KEY (user_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_skills_skill FOREIGN KEY (skill_id) 
        REFERENCES skills (id) ON DELETE CASCADE,
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id),
    CONSTRAINT chk_years_exp CHECK (years_of_experience >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 5: mentorship_goals (Member 3)
-- Milestones and objectives defined by mentees
-- ---------------------------------------------------------------------
CREATE TABLE mentorship_goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mentee_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    target_completion_date DATE,
    status ENUM('ACTIVE', 'ACHIEVED', 'ABANDONED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_goals_mentee FOREIGN KEY (mentee_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_goals_mentee_status (mentee_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 6: mentorship_applications (Member 3)
-- Formal connection requests from a mentee to a mentor
-- ---------------------------------------------------------------------
CREATE TABLE mentorship_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mentee_id INT NOT NULL,
    mentor_id INT NOT NULL,
    goal_id INT NULL,
    message TEXT NOT NULL,
    status ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME NULL,
    CONSTRAINT fk_apps_mentee FOREIGN KEY (mentee_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_apps_mentor FOREIGN KEY (mentor_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_apps_goal FOREIGN KEY (goal_id) 
        REFERENCES mentorship_goals (id) ON DELETE SET NULL,
    INDEX idx_apps_mentor_status (mentor_id, status),
    INDEX idx_apps_mentee_status (mentee_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 7: mentorship_relations (Member 4)
-- Formally active or historic mentorship partnerships
-- ---------------------------------------------------------------------
CREATE TABLE mentorship_relations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL UNIQUE,
    mentee_id INT NOT NULL,
    mentor_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    status ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED') NOT NULL DEFAULT 'ACTIVE',
    notes TEXT,
    CONSTRAINT fk_relations_app FOREIGN KEY (application_id) 
        REFERENCES mentorship_applications (id) ON DELETE RESTRICT,
    CONSTRAINT fk_relations_mentee FOREIGN KEY (mentee_id) 
        REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_relations_mentor FOREIGN KEY (mentor_id) 
        REFERENCES users (id) ON DELETE RESTRICT,
    INDEX idx_relations_mentor_status (mentor_id, status),
    INDEX idx_relations_mentee_status (mentee_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 8: mentor_availability (Member 4)
-- Recurring weekly availability blocks set by mentors
-- ---------------------------------------------------------------------
CREATE TABLE mentor_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mentor_id INT NOT NULL,
    day_of_week TINYINT NOT NULL COMMENT '0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_availability_mentor FOREIGN KEY (mentor_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT chk_time_window CHECK (end_time > start_time),
    INDEX idx_availability_mentor (mentor_id, day_of_week, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 9: meetings (Member 5)
-- Specific 1-on-1 scheduled sessions under an active relationship
-- ---------------------------------------------------------------------
CREATE TABLE meetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    relation_id INT NOT NULL,
    scheduled_start DATETIME NOT NULL,
    scheduled_end DATETIME NOT NULL,
    meeting_link VARCHAR(255),
    agenda TEXT,
    status ENUM('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW') NOT NULL DEFAULT 'SCHEDULED',
    cancellation_reason VARCHAR(255),
    CONSTRAINT fk_meetings_relation FOREIGN KEY (relation_id) 
        REFERENCES mentorship_relations (id) ON DELETE CASCADE,
    CONSTRAINT chk_meeting_times CHECK (scheduled_end > scheduled_start),
    INDEX idx_meetings_relation_status (relation_id, status),
    INDEX idx_meetings_schedule (scheduled_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 10: reviews_and_ratings (Member 5)
-- Quantitative (1-5 stars) and qualitative evaluations
-- ---------------------------------------------------------------------
CREATE TABLE reviews_and_ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    relation_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    rating TINYINT NOT NULL,
    review_text TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reviews_relation FOREIGN KEY (relation_id) 
        REFERENCES mentorship_relations (id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_reviewee FOREIGN KEY (reviewee_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT chk_rating_range CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT uq_review_per_party UNIQUE (relation_id, reviewer_id, reviewee_id),
    INDEX idx_reviews_reviewee (reviewee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Table 11: meeting_notes (Auxiliary Table - Member 5)
-- Discussion notes, takeaways, and action items recorded per meeting
-- ---------------------------------------------------------------------
CREATE TABLE meeting_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meeting_id INT NOT NULL,
    author_id INT NOT NULL,
    summary TEXT NOT NULL,
    action_items TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notes_meeting FOREIGN KEY (meeting_id) 
        REFERENCES meetings (id) ON DELETE CASCADE,
    CONSTRAINT fk_notes_author FOREIGN KEY (author_id) 
        REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_notes_meeting (meeting_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

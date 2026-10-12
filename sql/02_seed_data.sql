-- =====================================================================
-- BBF 302E Database Systems - Term Project Seed Data
-- Topic: Mentor–Mentee Matching Platform
-- Default password for all seed accounts: password123
-- =====================================================================

USE mentor_platform;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE meeting_notes;
TRUNCATE TABLE reviews_and_ratings;
TRUNCATE TABLE meetings;
TRUNCATE TABLE mentor_availability;
TRUNCATE TABLE mentorship_relations;
TRUNCATE TABLE mentorship_applications;
TRUNCATE TABLE mentorship_goals;
TRUNCATE TABLE user_skills;
TRUNCATE TABLE skills;
TRUNCATE TABLE notifications;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 1. Insert Users (Admin, 4 Mentors, 5 Mentees)
-- ---------------------------------------------------------------------
INSERT INTO users (id, email, password_hash, first_name, last_name, role, bio, current_title, organization) VALUES
-- Admin
(1, 'admin@itu.edu.tr', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'System', 'Administrator', 'ADMIN', 'Platform Administrator managing skills catalog and user oversight.', 'Platform Coordinator', 'ITU Computer Engineering'),

-- Mentors
(2, 'dr.demir@techcorp.com', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Ahmet', 'Demir', 'MENTOR', 'Staff Backend Architect with 12 years experience building distributed database systems.', 'Principal Engineer', 'CloudScale Inc.'),
(3, 'selin.kaya@ailabs.org', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Selin', 'Kaya', 'MENTOR', 'Machine Learning Research Engineer focusing on LLM fine-tuning and computer vision architectures.', 'Senior AI Scientist', 'VisionLabs'),
(4, 'mehmet.oz@fintech.io', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Mehmet', 'Oz', 'MENTOR', 'Technical Product Manager guiding junior engineers on career transitions and system design.', 'VP of Engineering', 'FinTech Innovations'),
(5, 'zeynep.yildiz@devops.co', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Zeynep', 'Yildiz', 'MENTOR', 'DevOps & SRE Consultant specializing in Kubernetes clustering, CI/CD pipelines, and cloud security.', 'Lead SRE Consultant', 'CloudOps Global'),

-- Mentees
(6, 'ali.yilmaz@itu.edu.tr', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Ali', 'Yilmaz', 'MENTEE', 'Junior undergraduate in Computer Engineering preparing for backend engineering internships.', 'Student', 'Istanbul Technical University'),
(7, 'ayse.can@itu.edu.tr', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Ayse', 'Can', 'MENTEE', 'Aspiring Data Scientist with background in statistics, learning Python data pipelines.', 'Senior Student', 'Istanbul Technical University'),
(8, 'burak.erdogan@alumni.itu', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Burak', 'Erdogan', 'MENTEE', 'Recent graduate looking to transition from manual QA testing to full-stack engineering.', 'Junior Developer', 'SoftSolutions'),
(9, 'damla.aksoy@itu.edu.tr', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Damla', 'Aksoy', 'MENTEE', 'Master student working on cloud-native deployments and container orchestration research.', 'Graduate Researcher', 'ITU Informatics Institute'),
(10, 'eren.celik@itu.edu.tr', 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6', 'Eren', 'Celik', 'MENTEE', 'Sophomore passionate about distributed databases and high-performance algorithms.', 'Student', 'Istanbul Technical University');

-- ---------------------------------------------------------------------
-- 2. Insert Skills (12 skills across 4 categories)
-- ---------------------------------------------------------------------
INSERT INTO skills (id, name, category, description) VALUES
(1, 'Python Backend & Flask', 'Programming', 'Backend API development using Python, Flask framework, and WSGI microservices.'),
(2, 'Relational Database Design & SQL', 'Databases', 'Relational data modeling, 3NF/BCNF normalization, indexing, and raw SQL queries.'),
(3, 'Distributed Systems Architecture', 'System Architecture', 'High-availability microservice architectures, caching strategies, and event-driven design.'),
(4, 'Machine Learning & PyTorch', 'AI & Data', 'Model development, fine-tuning deep neural networks, and ML pipeline engineering.'),
(5, 'Data Analysis & Pandas', 'AI & Data', 'Exploratory data analysis, statistical modeling, data wrangling and visualization.'),
(6, 'Docker & Kubernetes', 'DevOps & Cloud', 'Containerization, microservices deployment, Helm charts, and cluster operations.'),
(7, 'CI/CD Pipelines & GitHub Actions', 'DevOps & Cloud', 'Automated testing workflows, continuous integration, and cloud delivery pipelines.'),
(8, 'Cloud Infrastructure (AWS / GCP)', 'DevOps & Cloud', 'Cloud-native services, IAM policies, VPC networking, and managed database services.'),
(9, 'Career Planning & Resume Review', 'Career & Leadership', 'Technical CV polishing, portfolio design, and tech industry career pathing.'),
(10, 'Coding Interview Preparation', 'Career & Leadership', 'Data structures, algorithm complexity analysis, and whiteboard mock interviews.'),
(11, 'Product Thinking for Engineers', 'Product & Agile', 'Translating user requirements into technical specifications and sprint backlogs.'),
(12, 'Go / Golang Microservices', 'Programming', 'Concurrent backend programming, goroutines, channels, and RESTful service development.');

-- ---------------------------------------------------------------------
-- 3. Insert User Skills (Mentors as Expert/Advanced, Mentees as Beginner/Intermediate)
-- ---------------------------------------------------------------------
INSERT INTO user_skills (user_id, skill_id, proficiency, years_of_experience) VALUES
-- Mentor 2 (Ahmet Demir)
(2, 1, 'EXPERT', 10),
(2, 2, 'EXPERT', 12),
(2, 3, 'ADVANCED', 8),
(2, 10, 'ADVANCED', 6),

-- Mentor 3 (Selin Kaya)
(3, 4, 'EXPERT', 7),
(3, 5, 'EXPERT', 8),
(3, 1, 'ADVANCED', 6),
(3, 9, 'INTERMEDIATE', 4),

-- Mentor 4 (Mehmet Oz)
(4, 9, 'EXPERT', 10),
(4, 10, 'EXPERT', 9),
(4, 11, 'EXPERT', 11),
(4, 3, 'ADVANCED', 7),

-- Mentor 5 (Zeynep Yildiz)
(5, 6, 'EXPERT', 8),
(5, 7, 'EXPERT', 7),
(5, 8, 'ADVANCED', 6),
(5, 12, 'ADVANCED', 5),

-- Mentee 6 (Ali Yilmaz)
(6, 1, 'INTERMEDIATE', 2),
(6, 2, 'BEGINNER', 1),
(6, 10, 'BEGINNER', 1),

-- Mentee 7 (Ayse Can)
(7, 4, 'BEGINNER', 1),
(7, 5, 'INTERMEDIATE', 2),
(7, 1, 'BEGINNER', 1),

-- Mentee 8 (Burak Erdogan)
(8, 1, 'BEGINNER', 1),
(8, 9, 'BEGINNER', 0),
(8, 10, 'BEGINNER', 1),

-- Mentee 9 (Damla Aksoy)
(9, 6, 'INTERMEDIATE', 2),
(9, 7, 'BEGINNER', 1),
(9, 8, 'BEGINNER', 1),

-- Mentee 10 (Eren Celik)
(10, 2, 'INTERMEDIATE', 2),
(10, 3, 'BEGINNER', 1);

-- ---------------------------------------------------------------------
-- 4. Insert Mentorship Goals
-- ---------------------------------------------------------------------
INSERT INTO mentorship_goals (id, mentee_id, title, description, target_completion_date, status) VALUES
(1, 6, 'Master Raw SQL & Relational Normalization', 'Design scalable relational schemas and optimize complex SQL queries for upcoming internships.', '2026-12-15', 'ACTIVE'),
(2, 7, 'Build an End-to-End PyTorch ML Pipeline', 'Develop, evaluate, and package a production-grade machine learning model for portfolio demonstration.', '2026-12-30', 'ACTIVE'),
(3, 8, 'Land First Software Engineer Role', 'Refine resume, pass technical whiteboard rounds, and master clean code principles.', '2027-01-20', 'ACTIVE'),
(4, 9, 'Kubernetes Production Cluster Readiness', 'Attain deep proficiency in Helm, Kubernetes ingress, and cloud CI/CD pipelines.', '2026-11-30', 'ACTIVE'),
(5, 10, 'Distributed Transaction Systems Study', 'Understand 2PC, Raft consensus, and transactional isolation levels in modern RDBMS.', '2026-12-25', 'ACHIEVED');

-- ---------------------------------------------------------------------
-- 5. Insert Mentorship Applications
-- ---------------------------------------------------------------------
INSERT INTO mentorship_applications (id, mentee_id, mentor_id, goal_id, message, status, created_at, decided_at) VALUES
(1, 6, 2, 1, 'Hello Dr. Demir, I admire your backend architectural background. I am aiming to master relational database design and raw SQL optimization for high throughput systems.', 'ACCEPTED', '2026-10-01 10:00:00', '2026-10-02 14:30:00'),
(2, 7, 3, 2, 'Dear Selin, I am a senior at ITU passionate about computer vision and ML engineering. I would love your guidance on model evaluation and research industry transitions.', 'ACCEPTED', '2026-10-02 11:15:00', '2026-10-03 09:00:00'),
(3, 8, 4, 3, 'Hi Mehmet, I am transitioning from QA into engineering and looking to prepare for coding interviews and system design fundamentals.', 'ACCEPTED', '2026-10-03 16:45:00', '2026-10-04 11:20:00'),
(4, 9, 5, 4, 'Dear Zeynep, I am conducting research into container orchestration and would value your feedback on real-world Kubernetes deployments.', 'PENDING', '2026-10-08 14:00:00', NULL),
(5, 10, 2, 5, 'Dr. Demir, I am looking to dive deep into database storage engines and B-tree indexing strategies.', 'REJECTED', '2026-09-15 08:30:00', '2026-09-16 10:00:00');

-- ---------------------------------------------------------------------
-- 6. Insert Mentorship Relations (Active pairs created from accepted apps)
-- ---------------------------------------------------------------------
INSERT INTO mentorship_relations (id, application_id, mentee_id, mentor_id, start_date, end_date, status, notes) VALUES
(1, 1, 6, 2, '2026-10-02', '2026-12-31', 'ACTIVE', 'Focusing on database indexing, raw SQL queries, and normalization to 3NF.'),
(2, 2, 7, 3, '2026-10-03', '2026-12-31', 'ACTIVE', 'Bi-weekly code reviews and PyTorch architecture critique sessions.'),
(3, 3, 8, 4, '2026-10-04', '2027-01-31', 'ACTIVE', 'Weekly mock whiteboard interview and CV optimization milestone.');

-- ---------------------------------------------------------------------
-- 7. Insert Mentor Availability Slots
-- ---------------------------------------------------------------------
INSERT INTO mentor_availability (id, mentor_id, day_of_week, start_time, end_time, is_active) VALUES
-- Mentor 2 (Ahmet Demir): Tuesdays & Thursdays 17:00 - 19:00
(1, 2, 1, '17:00:00', '19:00:00', TRUE),
(2, 2, 3, '17:00:00', '19:00:00', TRUE),

-- Mentor 3 (Selin Kaya): Wednesdays 18:00 - 20:00, Saturdays 10:00 - 12:00
(3, 3, 2, '18:00:00', '20:00:00', TRUE),
(4, 3, 5, '10:00:00', '12:00:00', TRUE),

-- Mentor 4 (Mehmet Oz): Mondays & Fridays 19:00 - 21:00
(5, 4, 0, '19:00:00', '21:00:00', TRUE),
(6, 4, 4, '19:00:00', '21:00:00', TRUE),

-- Mentor 5 (Zeynep Yildiz): Saturdays 14:00 - 17:00
(7, 5, 5, '14:00:00', '17:00:00', TRUE);

-- ---------------------------------------------------------------------
-- 8. Insert Meetings
-- ---------------------------------------------------------------------
INSERT INTO meetings (id, relation_id, scheduled_start, scheduled_end, meeting_link, agenda, status, cancellation_reason) VALUES
-- Relation 1 Meetings (Ali & Ahmet)
(1, 1, '2026-10-06 17:00:00', '2026-10-06 18:00:00', 'https://meet.jit.si/itu-mentorship-1', 'Initial alignment on database schema and project requirements.', 'COMPLETED', NULL),
(2, 1, '2026-10-13 17:00:00', '2026-10-13 18:00:00', 'https://meet.jit.si/itu-mentorship-1', 'Deep dive into 3NF and BCNF normalization anomalies.', 'SCHEDULED', NULL),

-- Relation 2 Meetings (Ayse & Selin)
(3, 2, '2026-10-07 18:00:00', '2026-10-07 19:00:00', 'https://meet.jit.si/itu-mentorship-2', 'Reviewing dataset curation and PyTorch DataLoader optimization.', 'COMPLETED', NULL),
(4, 2, '2026-10-14 18:00:00', '2026-10-14 19:00:00', 'https://meet.jit.si/itu-mentorship-2', 'Hyperparameter tuning and loss convergence analysis.', 'SCHEDULED', NULL),

-- Relation 3 Meetings (Burak & Mehmet)
(5, 3, '2026-10-05 19:00:00', '2026-10-05 20:00:00', 'https://meet.jit.si/itu-mentorship-3', 'Resume revamp and identifying target junior software engineering roles.', 'COMPLETED', NULL),
(6, 3, '2026-10-09 19:00:00', '2026-10-09 20:00:00', 'https://meet.jit.si/itu-mentorship-3', 'Array manipulation and dynamic programming mock problem.', 'CANCELLED', 'Rescheduled due to conference travel');

-- ---------------------------------------------------------------------
-- 9. Insert Meeting Notes
-- ---------------------------------------------------------------------
INSERT INTO meeting_notes (id, meeting_id, author_id, summary, action_items) VALUES
(1, 1, 2, 'Discussed the overall structure of the term project database schema. Reviewed candidate keys, primary keys, and composite primary keys.', '1. Draft initial ER diagram.\n2. Identify functional dependencies for all 10 tables.\n3. Verify absence of transitive dependencies.'),
(2, 3, 3, 'Evaluated training loss vs validation loss curves for baseline model. Explored data augmentation techniques.', '1. Implement random cropping and color jitter.\n2. Log metrics with TensorBoard.\n3. Benchmark batch size performance on GPU.'),
(3, 5, 4, 'Polished CV summary and highlighted open-source contributions. Outlined technical interview roadmap.', '1. Update LinkedIn profile with recent projects.\n2. Practice two medium LeetCode problems daily.\n3. Review Big-O complexity tables.');

-- ---------------------------------------------------------------------
-- 10. Insert Reviews & Ratings
-- ---------------------------------------------------------------------
INSERT INTO reviews_and_ratings (id, relation_id, reviewer_id, reviewee_id, rating, review_text) VALUES
-- Mentee reviews for mentors
(1, 1, 6, 2, 5, 'Outstanding mentor! Dr. Demir gave clear explanations on database indexing and transaction isolation that helped me excel in my coursework.'),
(2, 2, 7, 3, 5, 'Selin is incredibly knowledgeable in AI and model architecture. Her feedback helped me structure my training pipeline effectively.'),
(3, 3, 8, 4, 5, 'Mehmet provided actionable career guidance and gave me great confidence for technical interviews.'),

-- Mentors reviews for mentees
(4, 1, 2, 6, 5, 'Ali is dedicated, prepared, and quickly grasps complex relational database theory. High potential.'),
(5, 2, 3, 7, 4, 'Ayse is proactive and diligent. Recommended to continue building practical experimentation rigor.');

-- ---------------------------------------------------------------------
-- 11. Insert Notifications
-- ---------------------------------------------------------------------
INSERT INTO notifications (id, user_id, title, message, is_read) VALUES
(1, 6, 'Application Accepted', 'Dr. Ahmet Demir accepted your mentorship application! You can now view your active relationship.', TRUE),
(2, 6, 'Upcoming Meeting', 'You have an upcoming mentorship meeting with Dr. Ahmet Demir on October 13 at 17:00.', FALSE),
(3, 7, 'Application Accepted', 'Selin Kaya accepted your mentorship application! Check your active relationship tab.', TRUE),
(4, 9, 'Application Submitted', 'Your mentorship application to Zeynep Yildiz was successfully sent and is pending review.', FALSE),
(5, 5, 'New Application Received', 'You received a new mentorship application from Damla Aksoy regarding Kubernetes clusters.', FALSE);

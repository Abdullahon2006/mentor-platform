"""
Utility to initialize demo.db with all 11 tables and seed data
Allows immediate interactive preview and testing inside containers or machines without MySQL daemon running.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'demo.db')

def init_demo_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create Tables
    cursor.executescript("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'MENTEE',
        bio TEXT,
        current_title TEXT,
        organization TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE user_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        proficiency TEXT NOT NULL,
        years_of_experience INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE,
        UNIQUE (user_id, skill_id)
    );

    CREATE TABLE mentorship_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mentee_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        target_completion_date TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (mentee_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE mentorship_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mentee_id INTEGER NOT NULL,
        mentor_id INTEGER NOT NULL,
        goal_id INTEGER,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        decided_at TEXT,
        FOREIGN KEY (mentee_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (mentor_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (goal_id) REFERENCES mentorship_goals (id) ON DELETE SET NULL
    );

    CREATE TABLE mentorship_relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL UNIQUE,
        mentee_id INTEGER NOT NULL,
        mentor_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        notes TEXT,
        FOREIGN KEY (application_id) REFERENCES mentorship_applications (id),
        FOREIGN KEY (mentee_id) REFERENCES users (id),
        FOREIGN KEY (mentor_id) REFERENCES users (id)
    );

    CREATE TABLE mentor_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mentor_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (mentor_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        relation_id INTEGER NOT NULL,
        scheduled_start TEXT NOT NULL,
        scheduled_end TEXT NOT NULL,
        meeting_link TEXT,
        agenda TEXT,
        status TEXT NOT NULL DEFAULT 'SCHEDULED',
        cancellation_reason TEXT,
        FOREIGN KEY (relation_id) REFERENCES mentorship_relations (id) ON DELETE CASCADE
    );

    CREATE TABLE meeting_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        action_items TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE reviews_and_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        relation_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        reviewee_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        review_text TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (relation_id) REFERENCES mentorship_relations (id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (reviewee_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE (relation_id, reviewer_id, reviewee_id)
    );
    """)

    # Populate Seed Users
    # Password hash for 'password123'
    pwd = 'scrypt:32768:8:1$POZPWTsCdoieRDD9$7957242380b45e74132a5c482a8cfc815c523aadaeef58e1ece19441b6aed6d4c4abefae3f6642a48554e8ba87ca5fae73e3af8a95f707aff7136578cc04bee6'
    
    users = [
        (1, 'admin@itu.edu.tr', pwd, 'System', 'Administrator', 'ADMIN', 'Platform Administrator managing skills catalog and user oversight.', 'Platform Coordinator', 'ITU Computer Engineering'),
        (2, 'dr.demir@techcorp.com', pwd, 'Ahmet', 'Demir', 'MENTOR', 'Staff Backend Architect with 12 years experience building distributed database systems.', 'Principal Engineer', 'CloudScale Inc.'),
        (3, 'selin.kaya@ailabs.org', pwd, 'Selin', 'Kaya', 'MENTOR', 'Machine Learning Research Engineer focusing on LLM fine-tuning and computer vision architectures.', 'Senior AI Scientist', 'VisionLabs'),
        (4, 'mehmet.oz@fintech.io', pwd, 'Mehmet', 'Oz', 'MENTOR', 'Technical Product Manager guiding junior engineers on career transitions and system design.', 'VP of Engineering', 'FinTech Innovations'),
        (5, 'zeynep.yildiz@devops.co', pwd, 'Zeynep', 'Yildiz', 'MENTOR', 'DevOps & SRE Consultant specializing in Kubernetes clustering, CI/CD pipelines, and cloud security.', 'Lead SRE Consultant', 'CloudOps Global'),
        (6, 'ali.yilmaz@itu.edu.tr', pwd, 'Ali', 'Yilmaz', 'MENTEE', 'Junior undergraduate in Computer Engineering preparing for backend engineering internships.', 'Student', 'Istanbul Technical University'),
        (7, 'ayse.can@itu.edu.tr', pwd, 'Ayse', 'Can', 'MENTEE', 'Aspiring Data Scientist with background in statistics, learning Python data pipelines.', 'Senior Student', 'Istanbul Technical University'),
        (8, 'burak.erdogan@alumni.itu', pwd, 'Burak', 'Erdogan', 'MENTEE', 'Recent graduate looking to transition from manual QA testing to full-stack engineering.', 'Junior Developer', 'SoftSolutions'),
        (9, 'damla.aksoy@itu.edu.tr', pwd, 'Damla', 'Aksoy', 'MENTEE', 'Master student working on cloud-native deployments and container orchestration research.', 'Graduate Researcher', 'ITU Informatics Institute'),
        (10, 'eren.celik@itu.edu.tr', pwd, 'Eren', 'Celik', 'MENTEE', 'Sophomore passionate about distributed databases and high-performance algorithms.', 'Student', 'Istanbul Technical University')
    ]
    cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))", users)

    # Populate Skills
    skills = [
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
        (12, 'Go / Golang Microservices', 'Programming', 'Concurrent backend programming, goroutines, channels, and RESTful service development.')
    ]
    cursor.executemany("INSERT INTO skills VALUES (?, ?, ?, ?)", skills)

    # User Skills
    user_skills = [
        (1, 2, 1, 'EXPERT', 10),
        (2, 2, 2, 'EXPERT', 12),
        (3, 2, 3, 'ADVANCED', 8),
        (4, 2, 10, 'ADVANCED', 6),
        (5, 3, 4, 'EXPERT', 7),
        (6, 3, 5, 'EXPERT', 8),
        (7, 3, 1, 'ADVANCED', 6),
        (8, 3, 9, 'INTERMEDIATE', 4),
        (9, 4, 9, 'EXPERT', 10),
        (10, 4, 10, 'EXPERT', 9),
        (11, 4, 11, 'EXPERT', 11),
        (12, 4, 3, 'ADVANCED', 7),
        (13, 5, 6, 'EXPERT', 8),
        (14, 5, 7, 'EXPERT', 7),
        (15, 5, 8, 'ADVANCED', 6),
        (16, 5, 12, 'ADVANCED', 5),
        (17, 6, 1, 'INTERMEDIATE', 2),
        (18, 6, 2, 'BEGINNER', 1),
        (19, 6, 10, 'BEGINNER', 1),
        (20, 7, 4, 'BEGINNER', 1),
        (21, 7, 5, 'INTERMEDIATE', 2),
        (22, 7, 1, 'BEGINNER', 1),
        (23, 8, 1, 'BEGINNER', 1),
        (24, 8, 9, 'BEGINNER', 0),
        (25, 8, 10, 'BEGINNER', 1),
        (26, 9, 6, 'INTERMEDIATE', 2),
        (27, 9, 7, 'BEGINNER', 1),
        (28, 9, 8, 'BEGINNER', 1),
        (29, 10, 2, 'INTERMEDIATE', 2),
        (30, 10, 3, 'BEGINNER', 1)
    ]
    cursor.executemany("INSERT INTO user_skills VALUES (?, ?, ?, ?, ?)", user_skills)

    # Mentorship Goals
    goals = [
        (1, 6, 'Master Raw SQL & Relational Normalization', 'Design scalable relational schemas and optimize complex SQL queries for upcoming internships.', '2026-12-15', 'ACTIVE'),
        (2, 7, 'Build an End-to-End PyTorch ML Pipeline', 'Develop, evaluate, and package a production-grade machine learning model for portfolio demonstration.', '2026-12-30', 'ACTIVE'),
        (3, 8, 'Land First Software Engineer Role', 'Refine resume, pass technical whiteboard rounds, and master clean code principles.', '2027-01-20', 'ACTIVE'),
        (4, 9, 'Kubernetes Production Cluster Readiness', 'Attain deep proficiency in Helm, Kubernetes ingress, and cloud CI/CD pipelines.', '2026-11-30', 'ACTIVE'),
        (5, 10, 'Distributed Transaction Systems Study', 'Understand 2PC, Raft consensus, and transactional isolation levels in modern RDBMS.', '2026-12-25', 'ACHIEVED')
    ]
    cursor.executemany("INSERT INTO mentorship_goals VALUES (?, ?, ?, ?, ?, ?, datetime('now'))", goals)

    # Mentorship Applications
    apps = [
        (1, 6, 2, 1, 'Hello Dr. Demir, I admire your backend architectural background. I am aiming to master relational database design and raw SQL optimization for high throughput systems.', 'ACCEPTED', '2026-10-01 10:00:00', '2026-10-02 14:30:00'),
        (2, 7, 3, 2, 'Dear Selin, I am a senior at ITU passionate about computer vision and ML engineering. I would love your guidance on model evaluation and research industry transitions.', 'ACCEPTED', '2026-10-02 11:15:00', '2026-10-03 09:00:00'),
        (3, 8, 4, 3, 'Hi Mehmet, I am transitioning from QA into engineering and looking to prepare for coding interviews and system design fundamentals.', 'ACCEPTED', '2026-10-03 16:45:00', '2026-10-04 11:20:00'),
        (4, 9, 5, 4, 'Dear Zeynep, I am conducting research into container orchestration and would value your feedback on real-world Kubernetes deployments.', 'PENDING', '2026-10-08 14:00:00', None),
        (5, 10, 2, 5, 'Dr. Demir, I am looking to dive deep into database storage engines and B-tree indexing strategies.', 'REJECTED', '2026-09-15 08:30:00', '2026-09-16 10:00:00')
    ]
    cursor.executemany("INSERT INTO mentorship_applications VALUES (?, ?, ?, ?, ?, ?, ?, ?)", apps)

    # Mentorship Relations
    relations = [
        (1, 1, 6, 2, '2026-10-02', '2026-12-31', 'ACTIVE', 'Focusing on database indexing, raw SQL queries, and normalization to 3NF.'),
        (2, 2, 7, 3, '2026-10-03', '2026-12-31', 'ACTIVE', 'Bi-weekly code reviews and PyTorch architecture critique sessions.'),
        (3, 3, 8, 4, '2026-10-04', '2027-01-31', 'ACTIVE', 'Weekly mock whiteboard interview and CV optimization milestone.')
    ]
    cursor.executemany("INSERT INTO mentorship_relations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", relations)

    # Availability
    availability = [
        (1, 2, 1, '17:00:00', '19:00:00', 1),
        (2, 2, 3, '17:00:00', '19:00:00', 1),
        (3, 3, 2, '18:00:00', '20:00:00', 1),
        (4, 3, 5, '10:00:00', '12:00:00', 1),
        (5, 4, 0, '19:00:00', '21:00:00', 1),
        (6, 4, 4, '19:00:00', '21:00:00', 1),
        (7, 5, 5, '14:00:00', '17:00:00', 1)
    ]
    cursor.executemany("INSERT INTO mentor_availability VALUES (?, ?, ?, ?, ?, ?)", availability)

    # Meetings
    meetings = [
        (1, 1, '2026-10-06 17:00:00', '2026-10-06 18:00:00', 'https://meet.jit.si/itu-mentorship-1', 'Initial alignment on database schema and project requirements.', 'COMPLETED', None),
        (2, 1, '2026-10-18 17:00:00', '2026-10-18 18:00:00', 'https://meet.jit.si/itu-mentorship-1', 'Deep dive into 3NF and BCNF normalization anomalies.', 'SCHEDULED', None),
        (3, 2, '2026-10-07 18:00:00', '2026-10-07 19:00:00', 'https://meet.jit.si/itu-mentorship-2', 'Reviewing dataset curation and PyTorch DataLoader optimization.', 'COMPLETED', None),
        (4, 2, '2026-10-21 18:00:00', '2026-10-21 19:00:00', 'https://meet.jit.si/itu-mentorship-2', 'Hyperparameter tuning and loss convergence analysis.', 'SCHEDULED', None),
        (5, 3, '2026-10-05 19:00:00', '2026-10-05 20:00:00', 'https://meet.jit.si/itu-mentorship-3', 'Resume revamp and identifying target junior software engineering roles.', 'COMPLETED', None),
        (6, 3, '2026-10-09 19:00:00', '2026-10-09 20:00:00', 'https://meet.jit.si/itu-mentorship-3', 'Array manipulation and dynamic programming mock problem.', 'CANCELLED', 'Rescheduled due to conference travel')
    ]
    cursor.executemany("INSERT INTO meetings VALUES (?, ?, ?, ?, ?, ?, ?, ?)", meetings)

    # Meeting Notes
    notes = [
        (1, 1, 2, 'Discussed the overall structure of the term project database schema. Reviewed candidate keys, primary keys, and composite primary keys.', '1. Draft initial ER diagram.\n2. Identify functional dependencies for all 10 tables.\n3. Verify absence of transitive dependencies.'),
        (2, 3, 3, 'Evaluated training loss vs validation loss curves for baseline model. Explored data augmentation techniques.', '1. Implement random cropping and color jitter.\n2. Log metrics with TensorBoard.\n3. Benchmark batch size performance on GPU.'),
        (3, 5, 4, 'Polished CV summary and highlighted open-source contributions. Outlined technical interview roadmap.', '1. Update LinkedIn profile with recent projects.\n2. Practice two medium LeetCode problems daily.\n3. Review Big-O complexity tables.')
    ]
    cursor.executemany("INSERT INTO meeting_notes VALUES (?, ?, ?, ?, ?, datetime('now'))", notes)

    # Reviews
    reviews = [
        (1, 1, 6, 2, 5, 'Outstanding mentor! Dr. Demir gave clear explanations on database indexing and transaction isolation that helped me excel in my coursework.'),
        (2, 2, 7, 3, 5, 'Selin is incredibly knowledgeable in AI and model architecture. Her feedback helped me structure my training pipeline effectively.'),
        (3, 3, 8, 4, 5, 'Mehmet provided actionable career guidance and gave me great confidence for technical interviews.'),
        (4, 1, 2, 6, 5, 'Ali is dedicated, prepared, and quickly grasps complex relational database theory. High potential.'),
        (5, 2, 3, 7, 4, 'Ayse is proactive and diligent. Recommended to continue building practical experimentation rigor.')
    ]
    cursor.executemany("INSERT INTO reviews_and_ratings VALUES (?, ?, ?, ?, ?, ?, datetime('now'))", reviews)

    # Notifications
    notifications = [
        (1, 6, 'Application Accepted', 'Dr. Ahmet Demir accepted your mentorship application! You can now view your active relationship.', 1),
        (2, 6, 'Upcoming Meeting', 'You have an upcoming mentorship meeting with Dr. Ahmet Demir on October 18 at 17:00.', 0),
        (3, 7, 'Application Accepted', 'Selin Kaya accepted your mentorship application! Check your active relationship tab.', 1),
        (4, 9, 'Application Submitted', 'Your mentorship application to Zeynep Yildiz was successfully sent and is pending review.', 0),
        (5, 5, 'New Application Received', 'You received a new mentorship application from Damla Aksoy regarding Kubernetes clusters.', 0)
    ]
    cursor.executemany("INSERT INTO notifications VALUES (?, ?, ?, ?, ?, datetime('now'))", notifications)

    conn.commit()
    conn.close()
    print("Demo database initialized successfully at:", DB_PATH)

if __name__ == '__main__':
    init_demo_db()

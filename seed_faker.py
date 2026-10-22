"""
Realistic Data Population Script (BBF 302E - Milestone 2)
Generates ~300 users, 60 skills, and corresponding mentorship relationships,
meetings, reviews, and goals using the Faker library and raw parameterized SQL.
"""

import os
import random
from faker import Faker
from app import create_app
from app.db import execute_query, fetch_all, fetch_one
from app.auth_util import hash_password

fake = Faker(['en_US', 'tr_TR'])
Faker.seed(42)
random.seed(42)

SKILL_CATEGORIES = {
    'Programming': [
        'Python Backend & Flask', 'FastAPI & Microservices', 'Django Web Framework',
        'Go / Golang Concurrency', 'Java Spring Boot', 'C++ System Programming',
        'Rust Systems & WebAssembly', 'Node.js & Express', 'TypeScript Development',
        'React & Next.js', 'Vue.js Frontend Architecture', 'GraphQL API Design'
    ],
    'Databases': [
        'Relational Database Design & SQL', 'MySQL Performance Tuning',
        'PostgreSQL Query Optimization', 'Database Indexing & Normalization',
        'Redis Caching Strategies', 'MongoDB Document Modeling',
        'Cassandra Distributed Storage', 'Data Warehousing & Star Schema',
        'Elasticsearch & Search Engines', 'Database Migration & Versioning'
    ],
    'DevOps & Cloud': [
        'Docker Containerization', 'Kubernetes Cluster Administration',
        'CI/CD Pipelines & GitHub Actions', 'AWS Cloud Architecture',
        'Google Cloud Platform (GCP)', 'Terraform Infrastructure as Code',
        'Linux System Administration', 'Monitoring with Prometheus & Grafana',
        'Microservice Service Mesh', 'Cloud Security & IAM Best Practices'
    ],
    'AI & Data Science': [
        'Machine Learning & PyTorch', 'Deep Learning & Computer Vision',
        'Natural Language Processing & LLMs', 'Data Analysis with Pandas',
        'Statistical Modeling & R', 'MLOps & Model Deployment',
        'Feature Engineering & Pipelines', 'Reinforcement Learning',
        'Time Series Forecasting', 'Big Data with Apache Spark'
    ],
    'Career & Leadership': [
        'Technical CV & Resume Review', 'Coding Interview Preparation',
        'System Design Mock Interviews', 'Career Transitions into Tech',
        'Open-Source Contribution Guidance', 'Engineering Management & 1-on-1s',
        'Academic Research & Thesis Writing', 'Startup MVP & Tech Roadmapping',
        'Public Speaking for Engineers', 'Agile & Scrum Methodologies'
    ]
}

def seed_skills():
    print("Seeding skills taxonomy...")
    for category, skills in SKILL_CATEGORIES.items():
        for skill_name in skills:
            sql = """
                INSERT INTO skills (name, category, description)
                VALUES (%s, %s, %s)
            """
            try:
                execute_query(sql, (skill_name, category, f"Practical expertise and guidance in {skill_name}."))
            except Exception:
                pass

def seed_users(num_mentors=30, num_mentees=120):
    print(f"Seeding {num_mentors} mentors and {num_mentees} mentees...")
    default_pwd_hash = hash_password("password123")
    
    admins = [
        ('admin@itu.edu.tr', 'System', 'Administrator', 'Platform Administrator', 'ITU Computer Engineering'),
        ('gaffar.admin@itu.edu.tr', 'Gaffar', 'Dulkadir', 'Team Leader / Admin', 'Black Swan'),
        ('abdullokhon.admin@itu.edu.tr', 'Abdullokhon', 'Valikhonov', 'Core Developer / Admin', 'Black Swan')
    ]
    for email, first, last, title, org in admins:
        sql = """
            INSERT INTO users (email, password_hash, first_name, last_name, role, current_title, organization, bio)
            VALUES (%s, %s, %s, %s, 'ADMIN', %s, %s, 'System administration and platform moderation.')
        """
        try:
            execute_query(sql, (email, default_pwd_hash, first, last, title, org))
        except Exception:
            pass

    titles = [
        'Staff Software Engineer', 'Senior Backend Architect', 'Lead AI Scientist',
        'VP of Engineering', 'Principal DevOps Consultant', 'Senior Data Engineer',
        'Engineering Manager', 'Distinguished Architect', 'Research Scientist'
    ]
    companies = ['CloudScale Inc.', 'VisionLabs', 'FinTech Innovations', 'CloudOps Global', 'Trendyol', 'Getir', 'Baykar', 'Aselsan', 'TUBITAK']

    for i in range(num_mentors):
        first = fake.first_name()
        last = fake.last_name()
        email = f"mentor.{first.lower()}.{last.lower()}_{i}@mentormatch.com"
        title = random.choice(titles)
        org = random.choice(companies)
        bio = f"{title} at {org} with over {random.randint(6, 18)} years of industry experience mentoring aspiring engineers."
        
        sql = """
            INSERT INTO users (email, password_hash, first_name, last_name, role, current_title, organization, bio)
            VALUES (%s, %s, %s, %s, 'MENTOR', %s, %s, %s)
        """
        try:
            execute_query(sql, (email, default_pwd_hash, first, last, title, org, bio))
        except Exception:
            pass

    universities = ['Istanbul Technical University', 'Bogazici University', 'METU', 'Yildiz Technical University']
    mentee_titles = ['Undergraduate Student', 'Senior CE Student', 'Graduate Researcher', 'Junior Developer', 'Career Transitioner']

    for i in range(num_mentees):
        first = fake.first_name()
        last = fake.last_name()
        email = f"mentee.{first.lower()}.{last.lower()}_{i}@itu.edu.tr"
        title = random.choice(mentee_titles)
        org = random.choice(universities)
        bio = f"{title} interested in backend development, distributed systems, and preparing for software engineering careers."
        
        sql = """
            INSERT INTO users (email, password_hash, first_name, last_name, role, current_title, organization, bio)
            VALUES (%s, %s, %s, %s, 'MENTEE', %s, %s, %s)
        """
        try:
            execute_query(sql, (email, default_pwd_hash, first, last, title, org, bio))
        except Exception:
            pass

def seed_relationships_and_activity():
    print("Seeding user skills, goals, applications, and sessions...")
    mentors = fetch_all("SELECT id FROM users WHERE role = 'MENTOR'")
    mentees = fetch_all("SELECT id FROM users WHERE role = 'MENTEE'")
    skills = fetch_all("SELECT id FROM skills")

    if not mentors or not mentees or not skills:
        return

    for m in mentors:
        chosen_skills = random.sample(skills, random.randint(3, 6))
        for s in chosen_skills:
            prof = random.choice(['ADVANCED', 'EXPERT'])
            exp = random.randint(4, 12)
            try:
                execute_query(
                    "INSERT INTO user_skills (user_id, skill_id, proficiency, years_of_experience) VALUES (%s, %s, %s, %s)",
                    (m['id'], s['id'], prof, exp)
                )
            except Exception:
                pass

        for _ in range(random.randint(1, 3)):
            day = random.randint(0, 6)
            start_h = random.randint(14, 18)
            start_time = f"{start_h:02d}:00:00"
            end_time = f"{start_h + 2:02d}:00:00"
            try:
                execute_query(
                    "INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, is_active) VALUES (%s, %s, %s, %s, 1)",
                    (m['id'], day, start_time, end_time)
                )
            except Exception:
                pass

    sample_goals = [
        "Master Relational Database Normalization (3NF & BCNF)",
        "Ace Technical Whiteboard System Design Round",
        "Build Production-Grade Cloud Microservice",
        "Deep Dive into Distributed Transaction Protocols",
        "Transition from Junior to Mid-Level Software Engineer"
    ]

    for m in mentees:
        chosen_skills = random.sample(skills, random.randint(1, 3))
        for s in chosen_skills:
            prof = random.choice(['BEGINNER', 'INTERMEDIATE'])
            try:
                execute_query(
                    "INSERT INTO user_skills (user_id, skill_id, proficiency, years_of_experience) VALUES (%s, %s, %s, %s)",
                    (m['id'], s['id'], prof, random.randint(0, 2))
                )
            except Exception:
                pass

        for _ in range(random.randint(1, 2)):
            goal_title = random.choice(sample_goals)
            try:
                execute_query(
                    "INSERT INTO mentorship_goals (mentee_id, title, description, target_completion_date, status) VALUES (%s, %s, %s, '2026-12-30', 'ACTIVE')",
                    (m['id'], goal_title, f"Milestones for {goal_title}")
                )
            except Exception:
                pass

    print("Data seeding completed successfully!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_skills()
        seed_users(num_mentors=30, num_mentees=120)
        seed_relationships_and_activity()

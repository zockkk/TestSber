import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

fake = Faker()

def connect_db():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )

def generate_departments(conn, count=5):
    with conn.cursor() as cur:
        for _ in range(count):
            cur.execute(
                """INSERT INTO departments 
                (name, budget, established_date, active, description) 
                VALUES (%s, %s, %s, %s, %s)""",
                (
                    fake.company_suffix() + " " + fake.bs().title(),
                    round(random.uniform(50000, 500000), 2),
                    fake.date_between(start_date='-10y', end_date='-1y'),
                    random.choice([True, False]),
                    fake.paragraph()
                )
            )
        conn.commit()
        print(f"Generated {count} departments")

def generate_employees(conn, count=50):
    with conn.cursor() as cur:
        cur.execute("SELECT department_id FROM departments")
        dept_ids = [row[0] for row in cur.fetchall()]
        
        if not dept_ids:
            raise ValueError("No departments found")
        
        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            cur.execute(
                """INSERT INTO employees 
                (first_name, last_name, email, salary, hire_date, 
                department_id, is_manager, performance_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING employee_id""",
                (
                    first_name,
                    last_name,
                    f"{first_name.lower()}.{last_name.lower()}@example.com",
                    round(random.uniform(30000, 150000), 2),
                    fake.date_between(start_date='-5y', end_date='today'),
                    random.choice(dept_ids),
                    random.random() < 0.2,
                    random.randint(1, 5)
                )
            )
            employee_id = cur.fetchone()[0]
            
            if random.random() < 0.3:
                cur.execute(
                    "UPDATE employees SET profile_description = %s WHERE employee_id = %s",
                    (fake.paragraph(), employee_id)
                )
                
        conn.commit()
        print(f"Generated {count} employees")

def generate_projects(conn, count=15):
    with conn.cursor() as cur:
        cur.execute("SELECT employee_id FROM employees WHERE is_manager = TRUE")
        manager_ids = [row[0] for row in cur.fetchall()] or [None]
        
        for _ in range(count):
            start_date = fake.date_between(start_date='-2y', end_date='today')
            end_date = (start_date + timedelta(days=random.randint(30, 365))) if random.random() > 0.2 else None
            
            cur.execute(
                """INSERT INTO projects 
                (name, start_date, end_date, budget, completed, manager_id)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    fake.catch_phrase(),
                    start_date,
                    end_date,
                    round(random.uniform(10000, 500000), 2),
                    random.random() < 0.3,
                    random.choice(manager_ids)
                )
            )
        conn.commit()
        print(f"Generated {count} projects")

if __name__ == "__main__":
    try:
        with connect_db() as conn:
            generate_departments(conn)
            generate_employees(conn)
            generate_projects(conn)
    except Exception as e:
        print(f"Error: {e}")
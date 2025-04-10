CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    budget DECIMAL(15, 2),
    completed BOOLEAN DEFAULT FALSE,
    manager_id INTEGER REFERENCES employees(employee_id)
);
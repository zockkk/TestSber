import os
from datetime import datetime, date, timedelta
from functools import wraps
import logging
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from io import BytesIO

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
app.config['JSON_SORT_KEYS'] = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALID_SORT_COLUMNS = {
    'employee_id', 'first_name', 'last_name', 'email',
    'salary', 'hire_date', 'is_manager', 'performance_rating',
    'department_name', 'department_budget', 'projects_count'
}
MAX_EXPORT_ROWS = 10000

class DatabaseError(Exception):
    pass

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            connect_timeout=5
        )
        conn.autocommit = False
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise DatabaseError("Failed to connect to database")

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database operation failed: {e}")
            return jsonify({'error': str(e)}), 500
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    return wrapper

def validate_filters(filters):
    if 'salary_min' in filters:
        try:
            filters['salary_min'] = float(filters['salary_min']) if filters['salary_min'] not in [None, ''] else None
        except (ValueError, TypeError):
            raise ValueError('Invalid salary_min value')
    
    if 'salary_max' in filters:
        try:
            filters['salary_max'] = float(filters['salary_max']) if filters['salary_max'] not in [None, ''] else None
            if 'salary_min' in filters and filters['salary_max'] and filters['salary_min'] and filters['salary_max'] < filters['salary_min']:
                raise ValueError('salary_max must be greater than salary_min')
        except (ValueError, TypeError):
            raise ValueError('Invalid salary_max value')
    
    # Валидация сортировки
    if 'sort_by' in filters:
        if filters['sort_by'] not in VALID_SORT_COLUMNS:
            raise ValueError(f'Invalid sort column. Allowed: {", ".join(sorted(VALID_SORT_COLUMNS))}')
    
    if 'sort_order' in filters and filters['sort_order'].upper() not in ('ASC', 'DESC'):
        raise ValueError('Invalid sort order. Use ASC or DESC')
    
    return filters

def build_employee_query(filters):
    base_query = """
    SELECT 
        e.employee_id, e.first_name, e.last_name, e.email, 
        e.salary, e.hire_date, e.is_manager, e.performance_rating,
        d.name as department_name, d.budget as department_budget,
        COUNT(p.project_id) as projects_count
    FROM employees e
    LEFT JOIN departments d ON e.department_id = d.department_id
    LEFT JOIN projects p ON e.employee_id = p.manager_id
    """
    
    conditions = []
    params = []
    
    if filters.get('department'):
        conditions.append("d.name ILIKE %s")
        params.append(f"%{filters['department']}%")
    
    if filters.get('salary_min') is not None:
        conditions.append("e.salary >= %s")
        params.append(float(filters['salary_min']))
    
    if filters.get('salary_max') is not None:
        conditions.append("e.salary <= %s")
        params.append(float(filters['salary_max']))
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    group_clause = """
    GROUP BY 
        e.employee_id, e.first_name, e.last_name, e.email,
        e.salary, e.hire_date, e.is_manager, e.performance_rating,
        d.name, d.budget
    """
    
    query = base_query + where_clause + group_clause
    
    if filters.get('sort_by') and filters['sort_by'] in VALID_SORT_COLUMNS:
        sort_order = 'DESC' if filters.get('sort_order', '').upper() == 'DESC' else 'ASC'
        
        if filters['sort_by'] == 'is_manager':
            query += f" ORDER BY e.is_manager {sort_order}"
        elif filters['sort_by'] == 'performance_rating':
            query += f" ORDER BY e.performance_rating {sort_order} NULLS LAST"
        else:
            query += f" ORDER BY {filters['sort_by']} {sort_order}"
    
    return query, params

@app.route('/api/employees', methods=['GET'])
@handle_errors
def get_employees():
    filters = validate_filters(request.args.to_dict())
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    query, params = build_employee_query(filters)
    
    count_query = """
    SELECT COUNT(DISTINCT e.employee_id)
    FROM employees e
    LEFT JOIN departments d ON e.department_id = d.department_id
    LEFT JOIN projects p ON e.employee_id = p.manager_id
    """ + (" WHERE " + " AND ".join([
        c for c in [
            "d.name ILIKE %s" if filters.get('department') else None,
            "e.salary >= %s" if filters.get('salary_min') is not None else None,
            "e.salary <= %s" if filters.get('salary_max') is not None else None
        ] if c is not None
    ]) if any([
        filters.get('department'), 
        filters.get('salary_min') is not None,
        filters.get('salary_max') is not None
    ]) else "")
    
    data_query = query + " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(data_query, params)
            columns = [desc[0] for desc in cur.description]
            employees = [dict(zip(columns, row)) for row in cur.fetchall()]
            
            count_params = [p for p in [
                f"%{filters['department']}%" if filters.get('department') else None,
                float(filters['salary_min']) if filters.get('salary_min') is not None else None,
                float(filters['salary_max']) if filters.get('salary_max') is not None else None
            ] if p is not None]
            
            cur.execute(count_query, count_params)
            total = cur.fetchone()[0]
            
            cur.execute("SELECT name FROM departments ORDER BY name")
            departments = [row[0] for row in cur.fetchall()]
    
    result = {
        'data': employees,
        'meta': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'departments': departments,
            'sortable_columns': sorted(VALID_SORT_COLUMNS)
        }
    }
    
    return jsonify(result)

@app.route('/api/export', methods=['GET'])
@handle_errors
def export_employees():
    try:
        filters = validate_filters(request.args.to_dict())
        export_type = request.args.get('export_type', 'filtered')
        
        base_query = """
        SELECT 
            e.employee_id, e.first_name, e.last_name, e.email, 
            e.salary, e.hire_date, e.is_manager, e.performance_rating,
            d.name as department_name, d.budget as department_budget,
            COUNT(p.project_id) as projects_count
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN projects p ON e.employee_id = p.manager_id
        """
        
        conditions = []
        params = []
        
        if export_type == 'filtered':
            if filters.get('department'):
                conditions.append("d.name ILIKE %s")
                params.append(f"%{filters['department']}%")
            
            if filters.get('salary_min') is not None:
                conditions.append("e.salary >= %s")
                params.append(float(filters['salary_min']))
            
            if filters.get('salary_max') is not None:
                conditions.append("e.salary <= %s")
                params.append(float(filters['salary_max']))
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        group_clause = """
        GROUP BY 
            e.employee_id, e.first_name, e.last_name, e.email,
            e.salary, e.hire_date, e.is_manager, e.performance_rating,
            d.name, d.budget
        """
        
        query = base_query + where_clause + group_clause
        
        if 'sort_by' in filters and filters['sort_by'] in VALID_SORT_COLUMNS:
            sort_order = 'DESC' if filters.get('sort_order', '').upper() == 'DESC' else 'ASC'
            query += f" ORDER BY {filters['sort_by']} {sort_order}"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                
                if not data:
                    return jsonify({'error': 'No data found for export'}), 404
                
                df = pd.DataFrame(data, columns=columns)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)
        
        return Response(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': 'attachment; filename=employees.xlsx',
                'Access-Control-Expose-Headers': 'Content-Disposition'
            }
        )
    
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate export file'}), 500

@app.route('/api/departments', methods=['GET'])
@handle_errors
def get_departments():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT department_id, name, budget, 
                       established_date, active, description 
                FROM departments
                ORDER BY name
            """)
            columns = [desc[0] for desc in cur.description]
            departments = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    return jsonify({'departments': departments})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
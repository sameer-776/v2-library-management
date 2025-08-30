import traceback
from datetime import datetime
import atexit
import pytz
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   get_flashed_messages, send_from_directory, jsonify)

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = 'your_secret_key'
app.config['DEBUG'] = True
IST = pytz.timezone('Asia/Kolkata')

# --- DATABASE CONNECTION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Add your MySQL password here
    'database': 'lib_main'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def execute_query(query, params=None, fetch=False, fetch_one=False):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount
        cursor.close()
        conn.close()
        return result
    except mysql.connector.Error as err:
        print(f"Query execution error: {err}")
        if conn:
            conn.close()
        return None

# --- CONDITIONAL STARTUP CLEANUP ---
def run_startup_cleanup():
    try:
        scheduled_exit_hour = 16  # 4 PM
        now = datetime.now(IST)
        if now.hour > scheduled_exit_hour:
            print(f"[STARTUP-CLEANUP] Server started after {scheduled_exit_hour}:00. Checking for open logs...")
            query = "UPDATE logs SET exit_date = %s, exit_time = %s WHERE exit_date IS NULL OR exit_date = ''"
            cleanup_datetime = now.replace(hour=23, minute=59, second=59)
            count = execute_query("SELECT COUNT(*) as count FROM logs WHERE exit_date IS NULL OR exit_date = ''", fetch_one=True)
            if count and count['count'] > 0:
                print(f"[STARTUP-CLEANUP] Found {count['count']} users with open logs. Exiting them now.")
                execute_query(query, (cleanup_datetime.date(), cleanup_datetime.time()))
            else:
                print("[STARTUP-CLEANUP] No open logs found to clean up.")
        else:
            print(f"[STARTUP-CLEANUP] Server started before scheduled exit time of {scheduled_exit_hour}:00. No cleanup needed.")
    except Exception as e:
        print(f"[STARTUP-CLEANUP ERROR] {e}")

# --- USER FINDER FUNCTIONS ---
def find_student(registry_code):
    query = "SELECT * FROM students WHERE full_reg_no LIKE %s"
    return execute_query(query, (f'%{registry_code}',), fetch_one=True)

def find_faculty(registry_code):
    try:
        query = "SELECT * FROM faculty WHERE full_reg_no = %s"
        return execute_query(query, (int(registry_code),), fetch_one=True)
    except ValueError:
        return None

def find_user_and_validate(registry_code, role):
    if not registry_code or not role:
        return None, "Please enter registration code and select role."
    registry_code = registry_code.strip()
    if role == 'Student':
        if not registry_code.isdigit() or len(registry_code) != 5:
            return None, "Enter a valid 5-digit code for Student."
        user = find_student(registry_code)
    elif role == 'Faculty':
        if not registry_code.isdigit() or len(registry_code) != 4:
            return None, "Enter a valid 4-digit code for Faculty."
        user = find_faculty(registry_code)
    else:
        return None, "Invalid role selected."
    if not user:
        return None, f"No {role} found with that code."
    return user, None

# --- LOG FUNCTIONS ---
def get_open_log(full_reg_no):
    query = "SELECT * FROM logs WHERE full_reg_no = %s AND (exit_date IS NULL OR exit_date = '')"
    return execute_query(query, (str(full_reg_no),), fetch_one=True)

def get_users_inside():
    query = "SELECT full_reg_no, name FROM logs WHERE exit_date IS NULL OR exit_date = '' ORDER BY log_id DESC"
    return execute_query(query, fetch=True) or []

def create_entry_log(user, role):
    now = datetime.now(IST)
    reason = "Self Study"  # Default reason
    query = """INSERT INTO logs (full_reg_no, name, branch, year, entry_date, entry_time, role, reason)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    values = (
        str(user['full_reg_no']),
        user['name'],
        user.get('branch', 'N/A'),
        str(user.get('year', 'N/A')),
        now.date(),
        now.time(),
        role,
        reason
    )
    return execute_query(query, values)

def update_exit_log(full_reg_no):
    now = datetime.now(IST)
    query = "UPDATE logs SET exit_date = %s, exit_time = %s WHERE full_reg_no = %s AND (exit_date IS NULL OR exit_date = '')"
    return execute_query(query, (now.date(), now.time(), str(full_reg_no)))

def check_password(user_id, password):
    query = "SELECT * FROM password WHERE id = %s AND pass = %s"
    return bool(execute_query(query, (user_id, password), fetch_one=True))

# --- STATS FUNCTIONS ---
def get_live_stats():
    today = datetime.now(IST).date()

    total_entries_query = "SELECT COUNT(*) as count FROM logs WHERE entry_date = %s"
    total_entries_result = execute_query(total_entries_query, (today,), fetch_one=True)
    total_entries_today = total_entries_result['count'] if total_entries_result else 0

    unique_visitors_query = "SELECT COUNT(DISTINCT full_reg_no) as count FROM logs WHERE entry_date = %s"
    unique_visitors_result = execute_query(unique_visitors_query, (today,), fetch_one=True)
    unique_visitors_today = unique_visitors_result['count'] if unique_visitors_result else 0

    inside_query = "SELECT COUNT(*) as count FROM logs WHERE exit_date IS NULL OR exit_date = ''"
    inside_result = execute_query(inside_query, fetch_one=True)
    currently_inside = inside_result['count'] if inside_result else 0

    peak_hour_query = """SELECT HOUR(entry_time) as hour, COUNT(log_id) as count
                         FROM logs WHERE entry_date = %s
                         GROUP BY HOUR(entry_time) ORDER BY count DESC, hour DESC LIMIT 1"""
    peak_hour_result = execute_query(peak_hour_query, (today,), fetch_one=True)
    peak_hour_str = "N/A"
    if peak_hour_result and peak_hour_result['hour'] is not None:
        hour = int(peak_hour_result['hour'])
        if hour == 0:
            peak_hour_str = "12 AM"
        elif hour < 12:
            peak_hour_str = f"{hour} AM"
        elif hour == 12:
            peak_hour_str = "12 PM"
        else:
            peak_hour_str = f"{hour - 12} PM"

    return {
        "total_entries_today": total_entries_today,
        "unique_visitors_today": unique_visitors_today,
        "currently_inside": currently_inside,
        "peak_hour_today": peak_hour_str
    }

# --- AUTO EXIT SCHEDULER ---
def auto_exit_users():
    try:
        now = datetime.now(IST)
        query = "UPDATE logs SET exit_date = %s, exit_time = %s WHERE exit_date IS NULL OR exit_date = ''"
        count = execute_query(query, (now.date(), now.time()))
        if count and count > 0:
            print(f"[AUTO-EXIT] {count} users exited automatically at 16:30 IST.")
        else:
            print("[AUTO-EXIT] No open logs found at 16:30 IST.")
    except Exception as e:
        print(f"[AUTO-EXIT ERROR] {e}")

try:
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(auto_exit_users, trigger='cron', hour=16, minute=30, id='auto_exit_job')
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
except Exception as e:
    print(f"Scheduler initialization error: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    try:
        users_inside = get_users_inside()
        messages = get_flashed_messages(with_categories=True)
        toast_message, toast_type = ('', 'info')
        if messages:
            toast_type, toast_message = messages[0]
        return render_template('index.html', toast_message=toast_message, toast_type=toast_type, users_inside=users_inside)
    except Exception as e:
        print(f"Index route error: {e}")
        return f"Error: {str(e)}"

@app.route('/check', methods=['POST'])
def check_user():
    try:
        registry_code = request.form.get('registry_last_digits', '').strip()
        role = request.form.get('role', '').strip()

        if not role:
            flash("Please select a role.", "error")
            return redirect(url_for('index'))

        user, error = find_user_and_validate(registry_code, role)
        if error:
            flash(error, "error")
            return redirect(url_for('index'))

        open_log = get_open_log(user['full_reg_no'])

        if open_log:
            # User inside → Exit
            if open_log['role'] != role:
                flash(f"Exit denied. You entered as {open_log['role']} and must exit with the same role.", "error")
                return redirect(url_for('index'))
            update_exit_log(user['full_reg_no'])
            flash(f"Goodbye! {user['name']} exited the library.", "success")
        else:
            # User outside → Entry
            # Strictly check no open log exists before entry to prevent duplicates
            existing_open_log = execute_query(
                "SELECT * FROM logs WHERE full_reg_no = %s AND (exit_date IS NULL OR exit_date = '')",
                (str(user['full_reg_no']),),
                fetch_one=True
            )
            if existing_open_log:
                flash(f"{user['name']} is already inside. Cannot enter again without exiting!", "error")
                return redirect(url_for('index'))

            now = datetime.now(IST)
            if now.hour < 7 or now.hour >= 20:
                flash("Library closed. Hours: 7 AM - 8 PM", "error")
                return redirect(url_for('index'))

            create_entry_log(user, role)
            flash(f"Welcome! {user['name']} entered the library.", "success")

        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error in /check route: {e}")
        traceback.print_exc()
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('index'))

# --- MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    run_startup_cleanup()
    app.run(debug=True, host='0.0.0.0', port=5000)

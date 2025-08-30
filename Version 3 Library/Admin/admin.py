# --- 1. Import Necessary Libraries ---
import pandas as pd
import mysql.connector
from flask import (
    Flask,
    request,
    send_file,
    jsonify,
    render_template,
    send_from_directory
)
from flask_cors import CORS
from datetime import datetime, timedelta
import io

# --- 2. Database Configuration ---
db_config = {
    'host': 'localhost',      # Or your database server IP
    'user': 'root',           # Your database username
    'password': '',           # Your database password
    'database': 'lib_main'
}

# --- 3. Initialize the Flask Application ---
app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)  # Enable CORS to allow requests from the browser

# --- 4. Helper Function to Fetch Data from MySQL ---
def get_log_data():
    """
    Connects to the MySQL database and fetches the library logs.
    Returns a pandas DataFrame.
    """
    try:
        conn = mysql.connector.connect(**db_config)
        query = """
            SELECT 
                full_reg_no, 
                name, 
                branch, 
                year, 
                entry_date, 
                TIME_FORMAT(entry_time, '%H:%i:%s') AS entry_time,
                exit_date,
                TIME_FORMAT(exit_time, '%H:%i:%s') AS exit_time
            FROM logs
        """
        df = pd.read_sql(query, conn)

        # Format entry & exit dates properly
        df['entry_date'] = pd.to_datetime(df['entry_date'], errors='coerce').dt.strftime('%d-%m-%Y')
        df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce').dt.strftime('%d-%m-%Y')

        # Fill missing exit date/time with "Still Inside"
        df['exit_date'] = df['exit_date'].fillna("Still Inside")
        df['exit_time'] = df['exit_time'].fillna("Still Inside")

        # Rename columns for professional Excel reports
        df.rename(columns={
            "full_reg_no": "Registration No",
            "name": "Name",
            "branch": "Branch",
            "year": "Year",
            "entry_date": "Entry Date",
            "entry_time": "Entry Time",
            "exit_date": "Exit Date",
            "exit_time": "Exit Time"
        }, inplace=True)

        return df

    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL or fetching data: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# --- 5. Helper Function to Create and Send Excel Files ---
def create_excel_response(df, filename="report.xlsx"):
    """
    Converts a pandas DataFrame to an in-memory Excel file and prepares it for download.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# --- 6. API Endpoints for Reports ---
@app.route('/sty.css')
def serve_css():
    return send_from_directory('.', 'sty.css')

@app.route('/scr.js')
def serve_js():
    return send_from_directory('.', 'scr.js')

# -------------------- DAILY STUDENT COUNT --------------------
@app.route('/report/daily_student_count', methods=['GET'])
def daily_student_count():
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "A 'date' parameter is required. Format: YYYY-MM-DD"}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

    daily_logs = log_df[log_df['Entry Date'] == target_date.strftime('%d-%m-%Y')]
    if daily_logs.empty:
        return jsonify({"error": f"No library entries found for {date_str}."}), 404

    student_count = daily_logs['Registration No'].nunique()
    report_df = pd.DataFrame({
        'Date': [target_date.strftime('%d-%m-%Y')],
        'Unique Student Count': [student_count]
    })
    filename = f"daily_student_count_{date_str}.xlsx"
    return create_excel_response(report_df, filename)

# -------------------- DAILY SUMMARY --------------------
@app.route('/report/daily_summary', methods=['GET'])
def daily_summary():
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "A 'date' parameter is required. Format: YYYY-MM-DD"}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

    daily_summary_df = log_df[log_df['Entry Date'] == target_date.strftime('%d-%m-%Y')].copy()
    if daily_summary_df.empty:
        return jsonify({"error": f"No library entries found for {date_str}."}), 404

    filename = f"daily_summary_{date_str}.xlsx"
    return create_excel_response(daily_summary_df, filename)

# -------------------- WEEKLY SUMMARY --------------------
@app.route('/report/weekly_summary', methods=['GET'])
def weekly_summary():
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500
        
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "A 'date' parameter is required. Format: YYYY-MM-DD"}), 400

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_mask = (
        pd.to_datetime(log_df['Entry Date'], format='%d-%m-%Y') >= start_of_week
    ) & (
        pd.to_datetime(log_df['Entry Date'], format='%d-%m-%Y') <= end_of_week
    )

    weekly_summary_df = log_df.loc[weekly_mask].copy()

    if weekly_summary_df.empty:
        return jsonify({"error": f"No library entries found for the week of {start_of_week.strftime('%Y-%m-%d')}."}), 404

    filename = f"weekly_report_{start_of_week.strftime('%Y%m%d')}_to_{end_of_week.strftime('%Y%m%d')}.xlsx"
    return create_excel_response(weekly_summary_df, filename)

# -------------------- FULL LOG DUMP --------------------
@app.route('/report/full_log_dump', methods=['GET'])
def full_log_dump():
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    full_df = log_df.sort_values(by=['Entry Date', 'Entry Time'], ascending=[False, False]).copy()
    filename = "full_library_log_dump.xlsx"
    return create_excel_response(full_df, filename)

@app.route('/')
def Home():
    return render_template('ind.html')

# --- 7. Run the Application ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

Library Gate: A Modern Library Management System
Welcome to Library Gate, a full-stack web application designed to track and manage student and faculty entries and exits from a university library. This system provides a seamless, modern interface for administrators and a robust, automated backend to ensure data integrity.


✨ Features
Secure Authentication: A session-based login system with a full-screen, glassmorphism overlay secures the dashboard. It includes a lockout mechanism after 5 failed attempts to prevent brute-force attacks.

Live Dashboard: The main interface features a real-time list of all users currently inside the library, which updates instantly after every check-in or check-out.

Dynamic UI: The user interface is built with modern CSS and vanilla JavaScript, featuring smooth transitions and an intuitive, multi-step panel for user interaction.

Intelligent Entry/Exit Flow: The system automatically detects if a user is entering or exiting and adjusts the workflow accordingly. It validates user roles (Student/Faculty) and their corresponding ID formats.

Automated Daily Logout: A background scheduler automatically checks out all remaining users at 4:30 PM IST each day, ensuring logs are accurately closed and preventing data inconsistencies.

Keyboard Navigation: The interface is fully navigable using keyboard shortcuts (Enter, Escape, ArrowUp, ArrowDown) for efficient and fast operation.

Instant Feedback: Toast notifications provide immediate, non-intrusive feedback for all actions, such as successful entries, exits, or errors.

🛠️ Tech Stack
Frontend: HTML5, CSS3, JavaScript (ES6+)

Backend: Python (with Flask)

Database: MySQL

Scheduler: APScheduler for running automated background tasks.

🚀 System Workflow
Login: The operator is first greeted with a login screen. After successful authentication, a session is created that lasts for the entire day.

Dashboard: The main screen displays the current time, date, and a live table of users inside the library.

Initiate Action: Clicking the central logo opens the action panel.

Role & ID: The operator selects a role (Student or Faculty) and enters the last 5 digits of a student's ID or the last 4 digits of a faculty ID.

Status Check: The system sends a request to the backend to validate the user and check if they have an "open log" (i.e., are already inside).

Process Action:

If the user is outside, they are prompted to select a reason for their visit before the system creates a new entry log.

If the user is inside, the system immediately processes an exit, updating their log with an exit timestamp.

🗄️ Database Schema
The system requires a MySQL database named lib_main with the following tables:

students: Stores student information.

full_reg_no (VARCHAR, Primary Key)

name (VARCHAR)

branch (VARCHAR)

year (INT)

faculty: Stores faculty information.

full_reg_no (VARCHAR, Primary Key)

name (VARCHAR)

logs: Records all entry and exit activities.

id (INT, Primary Key, Auto-Increment)

full_reg_no (VARCHAR)

name (VARCHAR)

entry_date (DATE)

entry_time (TIME)

exit_date (DATE, NULLable)

exit_time (TIME, NULLable)

role (VARCHAR)

reason (VARCHAR)

password: Stores login credentials for the dashboard operator.

id (VARCHAR, Primary Key)

pass (VARCHAR)

⚙️ Setup and Installation
To run this project locally, follow these steps:

Clone the repository:

bash
git clone https://github.com/your-username/library-gate.git
cd library-gate
Set up the database:

Make sure you have a MySQL server running.

Create a database named lib_main.

Create the tables as defined in the Database Schema section and populate the students, faculty, and password tables with some sample data.

Update the database credentials in students.py:

python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_mysql_user',
    'password': 'your_mysql_password',
    'database': 'lib_main'
}
Install Python dependencies:

bash
pip install Flask mysql-connector-python pytz APScheduler
Run the application:

bash
python students.py
Access the application:
Open your web browser and navigate to http://127.0.0.1:5000.

📂 Project Structure
text
.
├── index.html         # Main HTML file with Jinja2 templating
├── script.js          # Frontend logic for interactivity and API calls
├── style.css          # Styling for the entire application
├── students.py        # Flask backend server
├── logo.png           # Application logo
├── background.png     # Background image
└── README.md
🌐 API Endpoints
The Flask application exposes the following endpoints:

GET /: Renders the main index.html page.

POST /login: Authenticates the operator.

POST /check-status: Checks if a user exists and is currently inside the library.

POST /check: The primary endpoint that handles the logic for both entry and exit by redirecting after processing.

GET /logo.png, /background.png, etc.: Serve static files.

👥 Credits
This project was developed by:

Sameer & Aryan Gaikwad (B.Tech AIML 2024-28)

Kshitij & Mohit Kumar (BCA 2024-27)

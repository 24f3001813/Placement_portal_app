from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = "secret_placement_key" # Needed for sessions and flash messages

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row # This lets us access columns by name like row['username']
    return conn

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()
        conn.close()

        if user:
            if user['role'] == 'company' and user['status'] == 'Pending':
                flash("Your account is pending Admin approval.", "warning")
                return redirect(url_for('login'))
            
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'company':
                return redirect(url_for('company_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid credentials!", "danger")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role'] # 'student' or 'company'
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        dept = request.form.get('department', 'General')
        
        conn = get_db_connection()
        try:
            status = 'Pending' if role == 'company' else 'Approved'
            cursor = conn.cursor()
            cursor.execute('INSERT INTO Users (username, password, role, status) VALUES (?, ?, ?, ?)',
                           (username, password, role, status))
            user_id = cursor.lastrowid
            
            if role == 'student':
                cursor.execute('INSERT INTO Students (user_id, full_name, department) VALUES (?, ?, ?)', 
                               (user_id, name, dept))
                # cursor.execute('INSERT INTO Students (user_id, full_name) VALUES (?, ?)', (user_id, name))
            else:
                cursor.execute('INSERT INTO Companies (user_id, company_name) VALUES (?, ?)', (user_id, name))
            
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#ADMIN Routes:

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    total_students = conn.execute('SELECT COUNT(*) FROM Students').fetchone()[0]
    total_companies = conn.execute('SELECT COUNT(*) FROM Companies').fetchone()[0]
    total_drives = conn.execute('SELECT COUNT(*) FROM PlacementDrives').fetchone()[0]

    pending_companies = conn.execute('''
        SELECT Users.user_id, Companies.company_name, Users.status 
        FROM Users 
        JOIN Companies ON Users.user_id = Companies.user_id 
        WHERE Users.role = 'company' AND Users.status = 'Pending'
    ''').fetchall()

    conn.close()
    return render_template('admin/dashboard.html', 
                           students=total_students, 
                           companies=total_companies, 
                           drives=total_drives,
                           pending=pending_companies)

@app.route('/admin/companies')
def manage_companies():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    companies = conn.execute('''
        SELECT Companies.*, Users.status, Users.user_id 
        FROM Companies 
        JOIN Users ON Companies.user_id = Users.user_id
    ''').fetchall()
    conn.close()
    return render_template('admin/manage_companies.html', companies=companies)

@app.route('/admin/students')
def manage_students():
    search = request.args.get('search', '')
    conn = get_db_connection()
    
    sql = "SELECT Students.*, Users.status FROM Students JOIN Users ON Students.user_id = Users.user_id"
    
    if search:
        students = conn.execute(sql + " WHERE full_name LIKE ?", ('%' + search + '%',)).fetchall()
    else:
        students = conn.execute(sql).fetchall()
        
    conn.close()
    return render_template('admin/manage_students.html', students=students)

@app.route('/admin/view-drives')
def admin_view_drives():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    drives = conn.execute('''
        SELECT PlacementDrives.*, Companies.company_name 
        FROM PlacementDrives 
        JOIN Companies ON PlacementDrives.company_id = Companies.company_id
    ''').fetchall()
    conn.close()
    return render_template('admin/view_drives.html', drives=drives)


@app.route('/admin/approve/<int:user_id>')
def approve_company(user_id):
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute('UPDATE Users SET status = "Approved" WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash("Company Approved!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve-drive/<int:drive_id>/<action>')
def manage_drive_status(drive_id, action):
    status = 'Approved' if action == 'approve' else 'Rejected'
    conn = get_db_connection()
    conn.execute('UPDATE PlacementDrives SET status = ? WHERE drive_id = ?', (status, drive_id))
    conn.commit()
    conn.close()
    flash(f"Drive {status}!", "success")
    return redirect(url_for('admin_view_drives'))

@app.route('/admin/blacklist/<int:user_id>/<string:role>')
def blacklist_user(user_id, role):
    conn = get_db_connection()
    
    # Change status to Blacklisted in the Users table
    conn.execute('UPDATE Users SET status = "Blacklisted" WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()

    return redirect(url_for('manage_students') if role == 'student' else url_for('admin_dashboard'))

# COMPANY Routes:

@app.route('/company/dashboard')
def company_dashboard():
    if session.get('role') != 'company':
        return redirect(url_for('login'))

    conn = get_db_connection()
    company = conn.execute('SELECT company_id FROM Companies WHERE user_id = ?', 
                           (session['user_id'],)).fetchone()
    
    drives = conn.execute('SELECT * FROM PlacementDrives WHERE company_id = ?', 
                          (company['company_id'],)).fetchall()
    conn.close()
    
    return render_template('company/dashboard.html', drives=drives)

@app.route('/company/create-drive', methods=['GET', 'POST'])
def create_drive():
    if request.method == 'POST':
        job_title = request.form['job_title']
        description = request.form['description']
        deadline = request.form['deadline']
        eligibility = request.form.get('eligibility', 'Open to all')
        
        conn = get_db_connection()
        company = conn.execute('SELECT company_id FROM Companies WHERE user_id = ?', 
                               (session['user_id'],)).fetchone()
        
        conn.execute('''
            INSERT INTO PlacementDrives (company_id, job_title, job_description, deadline, eligibility, status) 
            VALUES (?, ?, ?, ?, ?, 'Pending') 
        ''', (company['company_id'], job_title, description, deadline, eligibility))

        conn.commit()
        conn.close()
        flash("Placement Drive Created!", "success")
        return redirect(url_for('company_dashboard'))
        
    return render_template('company/create_drive.html')

@app.route('/company/view_applicants/<int:drive_id>')
def view_applicants(drive_id):
    conn = get_db_connection()
    applications = conn.execute('''
        SELECT Applications.application_id, Students.full_name, Students.department, 
               Students.resume_path, Applications.status 
        FROM Applications 
        JOIN Students ON Applications.student_id = Students.student_id 
        WHERE Applications.drive_id = ?
    ''', (drive_id,)).fetchall()
    conn.close()
    return render_template('company/view_applicants.html', apps=applications, drive_id=drive_id)

@app.route('/company/shortlist/<int:app_id>/<int:drive_id>')
def shortlist_student(app_id, drive_id):
    conn = get_db_connection()
    conn.execute('UPDATE Applications SET status = "Shortlisted" WHERE application_id = ?', (app_id,))
    conn.commit()
    conn.close()
    flash("Student Shortlisted!", "success")
    return redirect(url_for('view_applicants', drive_id=drive_id))

@app.route('/company/drive/edit/<int:drive_id>', methods=['GET', 'POST'])
def edit_drive(drive_id):
    conn = get_db_connection()
    if request.method == 'POST':
        # Update the query to include eligibility
        conn.execute('''
            UPDATE PlacementDrives 
            SET job_title=?, job_description=?, eligibility=?, deadline=? 
            WHERE drive_id=?
        ''', (request.form['job_title'], 
              request.form['description'], 
              request.form.get('eligibility'), 
              request.form['deadline'], 
              drive_id))
        
        conn.commit()
        conn.close()
        flash("Drive updated successfully!", "success")
        return redirect(url_for('company_dashboard'))

    drive = conn.execute('SELECT * FROM PlacementDrives WHERE drive_id = ?', (drive_id,)).fetchone()
    conn.close()
    return render_template('company/edit_drive.html', drive=drive)

@app.route('/company/status/<int:app_id>/<status>/<int:drive_id>')
def update_status(app_id, status, drive_id):
    conn = get_db_connection()
    conn.execute('UPDATE Applications SET status = ? WHERE application_id = ?', (status, app_id))
    conn.commit()
    conn.close()
    flash(f"Status updated to {status}!", "info")
    return redirect(url_for('view_applicants', drive_id=drive_id))

# STUDENT Routes:

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    drives = conn.execute('SELECT * FROM PlacementDrives WHERE status = "Approved"').fetchall()
    conn.close()
    
    return render_template('student/dashboard.html', drives=drives)

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        full_name = request.form['full_name']
        dept = request.form.get('department' , 'General') 
        file = request.files.get('resume') 
        
        resume_path = None
        if file and file.filename != '':
            filename = f"resume_{session['username']}.pdf"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            resume_path = filename

        if resume_path:
            conn.execute('UPDATE Students SET full_name = ?, department = ?, resume_path = ? WHERE user_id = ?', 
                         (full_name, dept, resume_path, session['user_id']))
        else:
            conn.execute('UPDATE Students SET full_name = ?, department = ? WHERE user_id = ?', 
                         (full_name, dept, session['user_id']))
            
        conn.commit()
        flash("Profile and Resume updated!", "success")
        return redirect(url_for('student_dashboard'))

    student = conn.execute('SELECT * FROM Students WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('student/profile.html', student=student)

@app.route('/student/drive/<int:drive_id>')
def drive_details(drive_id):
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    drive = conn.execute('''
        SELECT PlacementDrives.*, Companies.company_name 
        FROM PlacementDrives 
        JOIN Companies ON PlacementDrives.company_id = Companies.company_id 
        WHERE PlacementDrives.drive_id = ?
    ''', (drive_id,)).fetchone()
    conn.close()
    
    return render_template('student/drive_details.html', drive=drive)

@app.route('/student/apply/<int:drive_id>')
def apply_for_drive(drive_id):
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    student = conn.execute('SELECT student_id FROM Students WHERE user_id = ?', 
                           (session['user_id'],)).fetchone()
    
    check = conn.execute('SELECT * FROM Applications WHERE student_id = ? AND drive_id = ?', 
                         (student['student_id'], drive_id)).fetchone()
    
    if check:
        flash("You have already applied for this drive!", "warning")
    else:
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        conn.execute('''
            INSERT INTO Applications (student_id, drive_id, apply_date, status) 
            VALUES (?, ?, ?, 'Applied')
        ''', (student['student_id'], drive_id, today))
        conn.commit()
        flash("Application submitted successfully!", "success")
    
    conn.close()
    return redirect(url_for('student_dashboard'))


@app.route('/student/history')
def student_history():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    student = conn.execute('SELECT student_id FROM Students WHERE user_id = ?', 
                           (session['user_id'],)).fetchone()
    
    history = conn.execute('''
        SELECT PlacementDrives.job_title, Applications.apply_date, Applications.status 
        FROM Applications 
        JOIN PlacementDrives ON Applications.drive_id = PlacementDrives.drive_id 
        WHERE Applications.student_id = ?
    ''', (student['student_id'],)).fetchall()
    
    conn.close()
    return render_template('student/history.html', history=history)

if __name__ == "__main__":
    app.run(debug=True)


import sqlite3

def create_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            role VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'Approved'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_name VARCHAR(100) NOT NULL, -- Increased length
            hr_contact VARCHAR(100),
            website VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name VARCHAR(100) NOT NULL, -- Increased length
            department VARCHAR(100),
            contact_info VARCHAR(100),
            resume_path TEXT,                -- Changed to TEXT for long file paths
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PlacementDrives (
            drive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            job_title VARCHAR(100) NOT NULL,
            job_description TEXT,            -- Changed to TEXT for long descriptions
            eligibility VARCHAR(255),
            deadline VARCHAR(50),
            status VARCHAR(50) DEFAULT 'Pending',
            FOREIGN KEY (company_id) REFERENCES Companies(company_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            drive_id INTEGER,
            apply_date VARCHAR(50),
            status VARCHAR(50) DEFAULT 'Applied',
            FOREIGN KEY (student_id) REFERENCES Students(student_id),
            FOREIGN KEY (drive_id) REFERENCES PlacementDrives(drive_id)
        )
    ''')

    cursor.execute("SELECT * FROM Users WHERE role = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)", 
                       ('admin', 'admin123', 'admin'))
        print("Admin user created: username='admin', password='admin123'")

    conn.commit()
    conn.close()
    print("Database and tables created successfully!")

if __name__ == "__main__":
    create_db()
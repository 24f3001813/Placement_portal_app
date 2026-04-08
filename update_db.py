import sqlite3

def update_schema():
    conn = sqlite3.connect('database.db')
    try:
        conn.execute('ALTER TABLE PlacementDrives ADD COLUMN eligibility TEXT;')
        conn.commit()
        print("Database updated successfully!")
    except sqlite3.OperationalError:
        print("Column 'eligibility' already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
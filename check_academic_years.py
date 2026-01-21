import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def check_academic_years():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'school_management_system')
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # Query academic years
        cursor.execute("SELECT * FROM system_academic_years ORDER BY start_year DESC")
        academic_years = cursor.fetchall()
        
        print("Current academic years in the system:")
        for year in academic_years:
            print(f"- ID: {year['id']}, Name: {year['name']}, Start: {year['start_year']}, End: {year['end_year']}, Is_Current: {year['is_current']}")
        
        conn.close()
        return academic_years
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []

if __name__ == "__main__":
    check_academic_years()
import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def delete_specific_academic_years():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'school_management_system')
        )
        
        cursor = conn.cursor()
        
        # Academic years to delete
        years_to_delete = ['2029/2030', '2028/2029', '2027/2028', '2026/2027', '2025/2026']
        
        print("Deleting academic years:", years_to_delete)
        
        for year_name in years_to_delete:
            # First get the ID of the academic year
            cursor.execute("SELECT id FROM system_academic_years WHERE name = %s", (year_name,))
            result = cursor.fetchone()
            
            if result:
                year_id = result[0]
                print(f"Found academic year '{year_name}' with ID {year_id}")
                
                # Delete related records first (these should cascade anyway, but we do it explicitly)
                cursor.execute("DELETE FROM student_grades WHERE academic_year_id = %s", (year_id,))
                cursor.execute("DELETE FROM student_attendance WHERE academic_year_id = %s", (year_id,))
                
                # Delete the academic year itself
                cursor.execute("DELETE FROM system_academic_years WHERE id = %s", (year_id,))
                
                print(f"Deleted academic year '{year_name}' (ID: {year_id})")
            else:
                print(f"Academic year '{year_name}' not found in the database")
        
        conn.commit()
        
        # Show remaining academic years
        cursor.execute("SELECT * FROM system_academic_years ORDER BY start_year DESC")
        remaining_years = cursor.fetchall()
        
        print("\nRemaining academic years in the system:")
        for year in remaining_years:
            print(f"- ID: {year[0]}, Name: {year[1]}, Start: {year[2]}, End: {year[3]}, Is_Current: {year[6]}")
        
        conn.close()
        print("\nDeletion completed successfully!")
        
    except Exception as e:
        print(f"Error connecting to database or performing deletion: {e}")

if __name__ == "__main__":
    delete_specific_academic_years()
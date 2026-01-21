from database import get_mysql_pool

def check_db():
    pool = get_mysql_pool()
    if not pool:
        print("❌ Could not connect to MySQL")
        return
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        print('Tables in database:')
        for row in cur.fetchall():
            print(f"- {row[0]}")
            
        for table in ['schools', 'students', 'subjects']:
            cur.execute(f"DESCRIBE {table}")
            print(f'\n{table.capitalize()} table structure:')
            for col in cur.fetchall():
                # Field, Type, Null, Key, Default, Extra
                print(f"- {col[0]} ({col[1]})")
    finally:
        conn.close()

if __name__ == '__main__':
    check_db()

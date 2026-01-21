import json
from database import get_mysql_pool

def clean_corrupted_data():
    query_select = 'SELECT id, detailed_scores FROM students WHERE detailed_scores LIKE "%[object Object]%"'
    
    pool = get_mysql_pool()
    if not pool:
        print("❌ Could not connect to MySQL")
        return
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query_select)
        rows = cur.fetchall()
        
        if not rows:
            print('No corrupted records found.')
            return
            
        print(f'Found {len(rows)} corrupted records. Cleaning...')
        for row in rows:
            row_id = row['id']
            scores_json = row['detailed_scores']
            try:
                scores = json.loads(scores_json)
                cleaned = {k: v for k, v in scores.items() if k != '[object Object]'}
                cur.execute('UPDATE students SET detailed_scores = %s WHERE id = %s', (json.dumps(cleaned), row_id))
                print(f'Successfully cleaned student ID {row_id}')
            except Exception as e:
                print(f'Error cleaning student ID {row_id}: {e}')
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    clean_corrupted_data()

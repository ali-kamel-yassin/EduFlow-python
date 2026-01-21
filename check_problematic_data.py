import json
from database import get_mysql_pool

def check_problematic_data():
    query = 'SELECT id, full_name, detailed_scores FROM students'
    
    rows = []
    pool = get_mysql_pool()
    if not pool:
        print("❌ Could not connect to MySQL")
        return
        
    conn = pool.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query)
        rows = cur.fetchall()
    finally:
        conn.close()
        
    print('Checking student records for issues...')
    problematic = []
    
    for row in rows:
        row_id = row['id']
        full_name = row['full_name']
        scores_json = row['detailed_scores']
        
        if scores_json and '[object Object]' in scores_json:
            problematic.append((row_id, full_name, scores_json))
            
    if problematic:
        print('Problematic records found:')
        for rid, name, scores in problematic:
            print(f'ID: {rid}, Name: {name}')
            print(f'Detailed scores: {scores}')
            print('---')
    else:
        print('No problematic records found with [object Object] issue')
        
    print('\nChecking for JSON parsing issues...')
    for row in rows:
        row_id = row['id']
        scores_json = row['detailed_scores']
        try:
            if scores_json:
                json.loads(scores_json)
        except Exception as e:
            print(f'Invalid JSON in student ID {row_id}: {e}')
            print(f'Content: {scores_json}')

if __name__ == '__main__':
    check_problematic_data()

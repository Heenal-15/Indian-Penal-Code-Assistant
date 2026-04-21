import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect('query-history.db') 
    return conn

def create_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """  
            CREATE TABLE IF NOT EXISTS query_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT,
                related_information TEXT
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error while creating table: {e}")


def save_query_to_db(question, answer, related_information):
    try:
        related_information_json = json.dumps(related_information)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO query_history (question, answer, related_information) VALUES (?, ?, ?)"
        cursor.execute(query, (question, answer, related_information_json))
        conn.commit()
        conn.close()
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def update_history_in_db(record_id, new_question, new_answer=None, new_related_information = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        response = list_history_from_db(condition= f"question = '{new_question}'")
        if len(response['result']) != 0 :
            if new_answer:
                query = "UPDATE query_history SET question = ?, answer = ? WHERE id = ?"
                params = (new_question, new_answer, record_id)
            else:
                query = "UPDATE query_history SET question = ? WHERE id = ?"
                params = (new_question, record_id)
            
            cursor.execute(query, params)
            conn.commit()
        conn.close()
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}

def delete_history_from_db(record_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM query_history WHERE id = ?"
        cursor.execute(query, (record_id,))
        conn.commit()
        conn.close()
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def list_history_from_db(record_id=None, condition=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not record_id and not condition:
            query = "SELECT * FROM query_history"
            params = ()
        elif condition:
            query = f"SELECT * FROM query_history WHERE {condition}"
            params = ()
        else:
            query = "SELECT * FROM query_history WHERE id = ?"
            params = (record_id,)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if rows:
            results = []
            for row in rows:
                related_information = json.loads(row[3]) if row[3] else []
                results.append({
                    'ID': row[0],
                    'Question': row[1],
                    'Answer': row[2],
                    'References': related_information
                })
            return {'status': 'success', 'result': results}
        else:
            return {'status': 'failed', 'result': []}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


create_table()

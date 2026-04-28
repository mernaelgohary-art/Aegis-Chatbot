import psycopg2
from psycopg2.extras import Json

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "merna123",
    "host": "localhost",
    "port": "5432"
}

def save_chat_message(session_id, new_message, title=None, model_name=None):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # If title and model_name are provided, it is a NEW session
        if title and model_name:
            query = """
                INSERT INTO chat_sessions (session_id, history, chat_title, model_name)
                VALUES (%s, %s::jsonb, %s, %s)
                ON CONFLICT (session_id)
                DO UPDATE SET 
                    history = chat_sessions.history || EXCLUDED.history,
                    updated_at = NOW();
            """
            cur.execute(query, (session_id, Json([new_message]), title, model_name))
        else:
            # Just append message for EXISTING sessions
            query = """
                UPDATE chat_sessions 
                SET history = history || %s::jsonb, updated_at = NOW()
                WHERE session_id = %s;
            """
            cur.execute(query, (Json([new_message]), session_id))
            
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"!!! DB Error: {e}")
    finally:
        if conn: conn.close()

def search_sessions(search_term):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = "SELECT session_id, chat_title, model_name FROM chat_sessions WHERE chat_title ILIKE %s ORDER BY updated_at DESC;"
        cur.execute(query, (f"%{search_term}%",))
        results = cur.fetchall()
        cur.close()
        return results
    except:
        return []
    finally:
        if conn: conn.close()

def get_all_sessions():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT session_id, chat_title, model_name FROM chat_sessions ORDER BY updated_at DESC;")
        results = cur.fetchall()
        cur.close()
        return results
    except:
        return []
    finally:
        if conn: conn.close()

def get_session_history(session_id):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT history FROM chat_sessions WHERE session_id = %s;", (session_id,))
        result = cur.fetchone()
        cur.close()
        return result[0] if result else []
    finally:
        if conn: conn.close()
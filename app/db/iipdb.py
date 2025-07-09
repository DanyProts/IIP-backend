import psycopg2
from db_config import host, user, password, db_name

def create_database_tables():
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
            client_encoding='UTF8'
        )

        with connection.cursor() as cursor:
            # Создание таблицы users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(20) DEFAULT 'student',
                    avatar_url TEXT,
                    join_date TIMESTAMP,
                    last_visit TIMESTAMP
                )
            """)

            # Создание таблицы courses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    category VARCHAR(100),
                    author_id INTEGER REFERENCES users(id),
                    level VARCHAR(20),
                    created_at TIMESTAMP,
                    is_active BOOLEAN
                )
            """)

            # Создание таблицы course_modules
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_modules (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER REFERENCES courses(id),
                    title VARCHAR(200) NOT NULL,
                    order_index INTEGER
                )
            """)

            # Создание таблицы course_content
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_content (
                    id SERIAL PRIMARY KEY,
                    module_id INTEGER REFERENCES course_modules(id),
                    title VARCHAR(200) NOT NULL,
                    content_type VARCHAR(20),
                    content_url TEXT,
                    order_index INTEGER,
                    duration_minutes INTEGER
                )
            """)

            # Создание таблицы user_course_enrollment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_course_enrollment (
                    user_id INTEGER REFERENCES users(id),
                    course_id INTEGER REFERENCES courses(id),
                    enrolled_at TIMESTAMP,
                    PRIMARY KEY (user_id, course_id)
                )
            """)

            # Создание таблицы user_course_progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_course_progress (
                    user_id INTEGER REFERENCES users(id),
                    course_id INTEGER REFERENCES courses(id),
                    progress_percent NUMERIC(5,2),
                    last_activity TIMESTAMP,
                    completed_lessons INTEGER,
                    total_time_minutes INTEGER,
                    streak_days INTEGER,
                    PRIMARY KEY (user_id, course_id)
                )
            """)

            # Создание таблицы lesson_completion
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_completion (
                    user_id INTEGER REFERENCES users(id),
                    content_id INTEGER REFERENCES course_content(id),
                    completed_at TIMESTAMP,
                    PRIMARY KEY (user_id, content_id)
                )
            """)

            # Создание таблицы assignments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER REFERENCES courses(id),
                    title VARCHAR(200) NOT NULL,
                    instructions TEXT,
                    type VARCHAR(20),
                    max_score INTEGER,
                    deadline TIMESTAMP
                )
            """)

            # Создание таблицы user_assignments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_assignments (
                    user_id INTEGER REFERENCES users(id),
                    assignment_id INTEGER REFERENCES assignments(id),
                    submission TEXT,
                    submitted_at TIMESTAMP,
                    score INTEGER,
                    feedback TEXT,
                    PRIMARY KEY (user_id, assignment_id)
                )
            """)

            # Создание таблицы user_activity_log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action VARCHAR(100) NOT NULL,
                    related_object_type VARCHAR(50),
                    related_object_id INTEGER,
                    timestamp TIMESTAMP
                )
            """)

            # Создание таблицы questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    title VARCHAR(200) NOT NULL,
                    body TEXT,
                    course_id INTEGER REFERENCES courses(id),
                    created_at TIMESTAMP
                )
            """)

            # Создание таблицы answers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS answers (
                    id SERIAL PRIMARY KEY,
                    question_id INTEGER REFERENCES questions(id),
                    user_id INTEGER REFERENCES users(id),
                    body TEXT,
                    created_at TIMESTAMP,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0
                )
            """)

            # Создание таблицы votes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    answer_id INTEGER REFERENCES answers(id),
                    vote_type VARCHAR(10) NOT NULL,
                    UNIQUE (user_id, answer_id)
                )
            """)

            connection.commit()
            print("Все таблицы успешно созданы!")

    except Exception as _ex:
        print("ERROR:", _ex)
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    create_database_tables()
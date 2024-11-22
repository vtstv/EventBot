import mysql.connector
from mysql.connector import Error
import yaml
import os
from dotenv import load_dotenv

class DatabaseManager:
    def __init__(self):
        load_dotenv()
        self.config = self._load_config()
        self.connection = None
        self.connect()

    def _load_config(self):
        with open('config/config.yml', 'r') as file:
            return yaml.safe_load(file)['database']

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=os.getenv('DATABASE_PASSWORD')
            )
            if self.connection.is_connected():
                self._create_tables()
        except Error as e:
            print(f"Error connecting to MySQL Database: {e}")

    def _create_tables(self):
        cursor = self.connection.cursor()
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                creator_id BIGINT NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                start_date DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'open',
                template_name VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                role_name VARCHAR(60) NOT NULL,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )
        ''')
        # Guild settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id BIGINT PRIMARY KEY,
                listening_channel BIGINT
            )
        ''')
        self.connection.commit()
        cursor.close()

    def create_event(self, guild_id, creator_id, name, description, start_date, template_name=None):
        cursor = self.connection.cursor()
        query = '''
            INSERT INTO events (guild_id, creator_id, name, description, start_date, template_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(query, (guild_id, creator_id, name, description, start_date, template_name))
        self.connection.commit()
        event_id = cursor.lastrowid
        cursor.close()
        return event_id

    def get_event(self, event_id):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM events WHERE id = %s', (event_id,))
        event = cursor.fetchone()
        cursor.close()
        return event

    def update_event(self, event_id, **kwargs):
        cursor = self.connection.cursor()
        set_clause = ', '.join(f"{k}=%s" for k in kwargs.keys())
        query = f'UPDATE events SET {set_clause} WHERE id = %s'
        values = list(kwargs.values()) + [event_id]
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def delete_event(self, event_id):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM events WHERE id = %s', (event_id,))
        self.connection.commit()
        cursor.close()

    def add_participant(self, event_id, user_id, role_name):
        cursor = self.connection.cursor()
        query = '''
            INSERT INTO participants (event_id, user_id, role_name)
            VALUES (%s, %s, %s)
        '''
        cursor.execute(query, (event_id, user_id, role_name))
        self.connection.commit()
        cursor.close()

    def remove_participant(self, event_id, user_id):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM participants WHERE event_id = %s AND user_id = %s', (event_id, user_id))
        self.connection.commit()
        cursor.close()

    def get_participants(self, event_id):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM participants WHERE event_id = %s', (event_id,))
        participants = cursor.fetchall()
        cursor.close()
        return participants

    def update_guild_settings(self, guild_id, listening_channel):
        cursor = self.connection.cursor()
        query = '''
            INSERT INTO guild_settings (guild_id, listening_channel)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE listening_channel = VALUES(listening_channel)
        '''
        cursor.execute(query, (guild_id, listening_channel))
        self.connection.commit()
        cursor.close()

    def get_guild_settings(self, guild_id):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM guild_settings WHERE guild_id = %s', (guild_id,))
        settings = cursor.fetchone()
        cursor.close()
        return settings

    def __del__(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

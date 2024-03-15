import mysql.connector
from src.Keys import Key
import datetime
import logging

logger = logging.getLogger(__name__)


class BotSQL:
    def __init__(self):
        config = {
            "user": Key.MYSQL_USER,
            "password": Key.MYSQL_PASSWORD,
            "host": "localhost",
            "database": "telegram",
        }
        try:
            self.conn = mysql.connector.connect(**config)
            logger.info("MySQL database connected")
        except mysql.connector.Error as e:
            logger.error(f"MySQL connection error {e.msg}")

        self.cursor = self.conn.cursor(buffered=True)

    def exec(self, query, values, commit=False):
        self.cursor.execute(query, values)
        try:
            if commit:
                self.conn.commit()
            return True
        except mysql.connector.Error:
            logger.error(f"MySQL error executing: \n{query} <- {values}")
            return False

    def insert(self, table: str, data: dict):
        query = ""
        values = ""
        match table:
            case "users":
                query = "INSERT INTO users(chatid) VALUES(%s)"
                values = (data["chatid"],)

            case "events":
                query = "INSERT INTO events(user, name, datetime) VALUES(%s, %s, %s)"
                values = (data["user"], data["name"], data["datetime"],)

            case "recurringevents":
                query = "INSERT INTO recurringevents(user, name, recurrence, time) VALUES(%s, %s, %s, %s)"
                values = (data["user"], data["name"], data["recurrence"], data["time"],)

            case "todoitems":
                query = "INSERT INTO todoitems(user, item) VALUES(%s, %s)"
                values = (data["user"], data["item"],)

        return self.exec(query, values, True)

    def fetchall(self, query=None, values=None):
        try:
            results = self.cursor.fetchall()
        except mysql.connector.errors.InterfaceError:
            return None
        if len(results) > 0:
            return results
        else:
            logger.error(f"SQLFetchError: Error fetching or executing select with query {query} and values {values}")

    def fetchone(self, query=None, values=None):
        try:
            results = self.cursor.fetchone()
        except mysql.connector.errors.InterfaceError:
            return None

        if len(results) > 0:
            return results
        else:
            logger.error(f"SQLFetchError: Error fetching or executing select with query {query} and values {values}")

    def insert_zip(self, chatid: int, zip: int):
        query = "UPDATE users SET zip=%s WHERE chatid=%s"
        values = (zip, chatid)
        return self.exec(query, values, True)

    def remove_zip(self, user):
        query = "UPDATE users SET zip=NULL WHERE chatid=%s"
        values = (user,)
        return self.exec(query, values, True)

    def remove_nr_event(self, user: int, event_name: str, event_time: datetime.datetime):
        query = "DELETE FROM events WHERE user=%s and datetime=%s and name=%s"
        values = (user, event_time, event_name)
        return self.exec(query, values)

    def events_on(self, user: int, date: datetime.date):
        query = f"SELECT * FROM events WHERE user=%s AND datetime LIKE %S"
        values = (user, datetime)
        self.exec(query, values)
        return self.fetchall(query, values)

    def events_between(self, user, start: datetime.date, end: datetime.date):
        query = f'SELECT * FROM events WHERE user=%s AND datetime BETWEEN %s AND %s'
        values = (user, start, end)
        self.exec(query, values)
        return self.fetchall()

    def recurring_events_on(self, user: int, day: str):
        query = f"SELECT * FROM recurringevents WHERE user=%s AND recurrence LIKE %s"
        values = (user, f"%{day.capitalize()}")
        self.exec(query, values)
        return self.fetchall(query, values)

    def check_for_user(self, user: int):
        query = "SELECT * FROM users WHERE chatid=%s"
        values = (user,)
        self.exec(query, values)
        return self.fetchall()

    def todo_items(self, user: int):
        query = "SELECT * FROM todoitems WHERE user=%s"
        values = (user,)
        self.exec(query, values)
        return self.fetchall()


import logging
import sqlite3
import pandas as pd

logger = logging.getLogger("__name__")

class DatabaseSqlite3():
    def __init__(self, connection_string):
        self.set_conn(connection_string)
        self.set_cursor(self.get_conn())
        self.set_type("sqlite3")

        # Player table
        column_names = ["chat_id","name","trains","points","color"]
        column_types = ["INTEGER", "TEXT", "INTEGER", "INTEGER", "TEXT"]
        column_extras = ["PRIMARY KEY NOT NULL", "NOT NULL", "NOT NULL", "NOT NULL",""]
        self.player_columns = [column_names, column_types, column_extras]

        # City table
        column_names = ["id","name","station"]
        column_types = ["INTEGER", "TEXT", "INTEGER"]
        column_extras = ["PRIMARY KEY NOT NULL", "NOT NULL", "NOT NULL"]
        self.city_columns = [column_names, column_types, column_extras]

        # Route table
        column_names = ["id","city1","city2","color","distance","locomotives","tunnel","owner"]
        column_types = ["INTEGER", "TEXT", "TEXT", "TEXT", "INTEGER", "INTEGER", "INTEGER", "INTEGER"]
        column_extras = ["PRIMARY KEY NOT NULL", "NOT NULL", "NOT NULL", "NOT NULL","NOT NULL","NOT NULL", "NOT NULL", "NOT NULL"]
        self.route_columns = [column_names, column_types, column_extras]

        # Ticket table
        column_names = ["id","city1","city2","value","owner"]
        column_types = ["INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER"]
        column_extras = ["NOT NULL", "NOT NULL", "NOT NULL", "NOT NULL","NOT NULL"]
        self.ticket_columns = [column_names, column_types, column_extras]

        # Card table
        column_names = ["id","color","owner"]
        column_types = ["INTEGER", "TEXT", "INTEGER"]
        column_extras = ["NOT NULL", "NOT NULL", ""]
        self.card_columns = [column_names, column_types, column_extras]

        tables = self.table_info()
        if "Player" not in tables:
            self.create_table("Player", self.player_columns)
        if "City" not in tables:
            self.create_table("City", self.city_columns)
        if "Route" not in tables:
            self.create_table("Route", self.route_columns)
        if "Ticket" not in tables:
            self.create_table("Ticket", self.ticket_columns)
        if "Card" not in tables:
            self.create_table("Card", self.card_columns)
        logger.info("All variables present in database!")

    def create_table(self, table_name, columns_info):
        """Create a table with table_name as name and columns_info as columns"""
        query = "CREATE TABLE IF NOT EXISTS " + table_name + " ("
        for i in range(0, len(columns_info[0])):
            query += columns_info[0][i] + " " + columns_info[1][i] + " " + columns_info[2][i] + ","
        # Delete latest character and raplace it with the create ending
        query = query[:-1]
        query = query + ");"

        try:
            self.cursor.execute(query)
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to create: " + table_name)
            logger.error(e)

    def insert_data_table(self, table_name, columns, data):
        """
        Inserts data rows in a table specified by table_name.
        data is a list of tuples 
        """
        query = "INSERT INTO " + table_name + " ("
        for i in range(len(columns[0])):
            query += columns[0][i] + ","
        query = query[:-1]
        query = query + ") VALUES ("

        for i in range(len(columns[0])):
            query += "?, "
        query = query[:-2]
        query = query + ");"

        try:
            self.cursor.executemany(query, data)
            self.conn.commit()
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to add data rows")
            logger.error(e)

    def insert_df_table(self, table_name, data):
        """Inserts a pandas Dataframe in a table specified by table_name."""
        # https://www.dataquest.io/blog/sql-insert-tutorial/
        try:
            data.to_sql(name=table_name, con=self.conn, if_exists="append", index=False)
        except Exception as e:
            logger.error("Unable to add dataframe rows")
            logger.error(e)
            

    def update_data_table(self, table_name, data, where):
        """
        Update a row in a table specified by table_name
        data is a dict of the columns and data you want to update
        where is a string that defines which records to update
        """
        query = "UPDATE "  + table_name + " SET " 
        for column, value in data:
            query += column + " = " + value + " ,"
        query = query[:-1]
        query += " WHERE " + where
        
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to update row")
            logger.error(e)

    def get_data_table(self, table_name, columns, where):
        """"
        Get the data from a table specified by table_name.
        columns is a list of the columns you want to have
        where is the column string
        A tuple is returned.
        """
        result = ()
        query = "SELECT "
        for column in columns[0]:
            query += column + ","
        query = query[:-1]  
        query += " FROM " + table_name + " WHERE " + where + ";"

        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to get data")
            logger.error(e)

        return result

    def get_data_df_table(self, table_name, columns, where, between_1, between_2, index = None):
        """
        Get the data from a table specified by table_name.
        columns is a list of the columns you want to have
        where is the column string
        between are the strings for the values
        A Pandas dataframe is returned.
        """
        df = pd.DataFrame()
        query = "SELECT "
        for column in columns[0]:
            query += column + ","
        query = query[:-1]  
        query += " FROM " + table_name + " WHERE " + where + " BETWEEN " + str(between_1) + " AND " + str(between_2) + ";"
        try:
            df = pd.read_sql_query(query, self.conn)
            if index is not None:
                try:
                    df = df.set_index(index)
                except Exception as e:
                    logger.error("Unable to set index: " + index + " for query: " + query)
                    logger.error(e)
            
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to get data and place it in a dataframe")
            logger.error(e)
        
        return df

    def get_max_from_column(self, table_name, column):
        """Get the row in which the maximum of a specified column is present""" 
        self.cursor.execute("SELECT max(" + column + ") FROM " + table_name)
        return self.cursor.fetchone()

    def get_min_from_column(self, table_name, column):
        """Get the row in which the maximum of a specified column is present""" 
        self.cursor.execute("SELECT min(" + column + ") FROM " + table_name)
        return self.cursor.fetchone()

    def add_column_to_table(self, table_name, column):
        """Add a column to the database specified by the table_name and the column as string"""
        query = "ALTER TABLE " + table_name + " ADD COLUMN " + column + " varchar(32)"

        try:
            self.cursor.execute(query)
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to add column")
            logger.error(e)

    def delete_table(self, table_name):
        """Delete a specific table"""
        query = "DROP TABLE " + table_name
        try:
            self.cursor.execute(query)
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to delete: " + table_name)
            logger.error(e)

    def table_info(self):
        """Get the name of the tables present in the database"""
        table_names = []
        query = "SELECT name FROM sqlite_master WHERE type ='table';"
        try:
            self.cursor.execute(query)
            names = self.cursor.fetchall()
            for name in names:
                table_names.append(name[0])

        except Exception as e:
            logger.debug(query)
            logger.error("Unable to get table info")
            logger.error(e)
        return list(table_names)

    def columns_info(self, table_name):
        """Get column names and types from a table. Returns 2 dimensional array"""
        column_names = []
        query = "PRAGMA table_info(" + table_name + ")"
        try:
            self.cursor.execute(query)
            names = self.cursor.fetchall()
            for name in names:
                column_names.append(name[1])
        except Exception as e:
            logger.debug(query)
            logger.error("Unable to get column info of: " + table_name)
            logger.error(e)
        return column_names

    ### GET ###

    def get_conn(self):
        return self.conn

    def get_cursor(self):
        return self.cursor

    def get_type(self):
        return self.type

    ### SET ###

    def set_conn(self, connection_string):
        try:
            self.conn = sqlite3.connect(connection_string)
        except Exception as e:
            logger.critical("Unable to connect to database with connection string: " + connection_string)
            logger.critical(e)
            exit()
    
    def set_cursor(self, conn):
        self.cursor = conn.cursor()

    def set_type(self, db_type):
        self.type = db_type

    
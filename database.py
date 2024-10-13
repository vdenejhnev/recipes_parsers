import mysql.connector

class Database:
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password

        self.cnx = mysql.connector.connect(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password
        )

        self.cursor = self.cnx.cursor()

    def create(self, table_name, data):
        try:
            columns = ', '.join(data.keys())
            values = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
            self.cursor.execute(query, list(data.values()))
            self.cnx.commit()
            return self.cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error creating record: {err}")
            self.cnx.rollback()
            return None

    def get(self, table_name, columns='*', filters=None, options=None):
        try:
            query = f"SELECT {columns} FROM {table_name}"
            params = []

            if filters:
                where_clauses = []

                for key, value in filters.items():
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        operator, value = value
                        where_clauses.append(f"{key} {operator} %s")
                        params.append(value)
                    elif key == '_fulltext':
                        columns, value, mode = value
                        if mode == 'natural':
                            where_clauses.append(f"MATCH ({columns}) AGAINST (%s IN NATURAL LANGUAGE MODE)")
                        elif mode == 'boolean':
                            where_clauses.append(f"MATCH ({columns}) AGAINST (%s IN BOOLEAN MODE)")
                        elif mode == 'query':
                            where_clauses.append(f"MATCH ({columns}) AGAINST (QUERY(%s) IN NATURAL LANGUAGE MODE)")
                        params.append(value)
                    else:
                        where_clauses.append(f"{key} = %s")
                        params.append(value)

                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)

            if options:
                if 'group_by' in options:
                    query += f" GROUP BY {options['group_by']}"

                if 'having' in options:
                    query += f" HAVING {options['having']}"

                if 'order_by' in options:
                    query += f" ORDER BY {options['order_by']}"

                if 'limit' in options:
                    query += f" LIMIT {options['limit']}"

                if 'offset' in options:
                    query += f" OFFSET {options['offset']}"

            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error getting records: {err}")
            return None

    def update(self, table_name, id, data):
        try:
            columns = ', '.join([f"{key} = %s" for key in data.keys()])
            query = f"UPDATE {table_name} SET {columns} WHERE id = %s"
            self.cursor.execute(query, list(data.values()) + [id])
            self.cnx.commit()
        except mysql.connector.Error as err:
            print(f"Error updating record: {err}")
            self.cnx.rollback()

    def delete(self, table_name, filters=None):
        try:
            if filters:
                where_clauses = []
                params = []
    
                for key, value in filters.items():
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        operator, value = value
                        where_clauses.append(f"{key} {operator} %s")
                        params.append(value)
                    else:
                        where_clauses.append(f"{key} = %s")
                        params.append(value)
    
                query = f"DELETE FROM {table_name} WHERE " + " AND ".join(where_clauses)
                self.cursor.execute(query, tuple(params))
            else:
                query = f"DELETE FROM {table_name}"
                self.cursor.execute(query)
    
            self.cnx.commit()
        except mysql.connector.Error as err:
            print(f"Error deleting record: {err}")
            self.cnx.rollback()

    def close(self):
        try:
            self.cursor.close()
            self.cnx.close()
        except mysql.connector.Error as err:
            print(f"Error closing connection: {err}")
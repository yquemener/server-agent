import sqlite3


class SqlModule:
    def __init__(self, db_file):
        self.db_file = db_file
        self.history = list()

    def reset(self):
        self.history.clear()

    def conversation(self):
        return "\n".join([f"{h[0]}\nResult of the query: {h[1]}" for h in self.history])

    def execute_query(self, queries):
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            ret = []
            for i, query in enumerate(queries.strip().split(";")):
                try:
                    if query.strip() == "":
                        continue
                    query = query.strip() + ";"
                    c.execute(query)
                    conn.commit()
                    result = c.fetchall()
                    if len(result) == 0:
                        result = "Success"
                    ret.append((query, result))
                except sqlite3.Error as e:
                    ret.append((query, f"{type(e).__name__}: {e}"))
                self.history.append(ret[-1])
            conn.close()
            return ret
        except Exception as e:
            print(f"SQL Error: {e}")
        return

    def context(self):
        s = ""
        # Connect to the SQLite database
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Retrieve the table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()

        # Loop through each table and get its structure
        for name in table_names:
            table_name = name[0]
            s += f"Table Name: {table_name}\n"

            # Get the table's columns and data types
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            s += "Columns:\n"
            for column in columns:
                column_name = column[1]
                column_type = column[2]
                s += f"\t{column_name}: {column_type}\n"

            s += "\n"

        # Close the database connection
        conn.close()
        return s
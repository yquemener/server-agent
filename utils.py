import sqlite3


# Does a SQL request, returns result if any
def db_req(dbname, req, args=None):
    if args is None:
        args = []
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    res = cursor.execute(req, args)
    if res:
        res = res.fetchall()
    conn.commit()
    conn.close()
    return res


# Turns a number of seconds into a human(and LLM)-readable approximation
def format_time_interval(seconds):
    intervals = [
        ('days', 86400),
        ('hours', 3600),
        ('minutes', 60),
        ('seconds', 1)]
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(f"{value} {name}")
    return result[0]


# Removes the "@" from a matrix handle and the ":matrix.org" if present
def extract_username(s):
    name = s.lstrip("@")
    server = s.split(":")[-1]
    if server == "matrix.org":
        return name.split(":")[0]
    else:
        return name
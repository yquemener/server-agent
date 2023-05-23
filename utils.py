import sqlite3


# Does a SQL request, returns result if any
def db_req(dbname, req, args=None, row_factory=False):
    if args is None:
        args = []
    conn = sqlite3.connect(dbname)
    if row_factory:
        conn.row_factory = sqlite3.Row
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


def pprint(l, indent=0):
    if isinstance(l, list) or isinstance(l, tuple) or isinstance(l, set):
        for ll in l:
            pprint(ll, indent+2)
    elif isinstance(l, dict):
        for k,v in l.items():
            if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set) or isinstance(v, dict):
                print(f"{indent*' '}{k}:")
                pprint(v, indent+2)
            else:
                print(f"{indent*' '}{k}: {v}")
    else:
        print(indent*' '+str(l))
def execute_sql(query, conn):
    cursor = conn.cursor()
    for subq in query.split(";"):
        if not subq.strip(): continue
        try:
            cursor.execute(subq)
            print("executed:")
            print(subq)
        except Exception as e:
            print(e)
    
def print_db(dbname, connection):
    """
    print_db(dbname, connection): -> None
    prints all tables in db using connection
    """
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    print(f"Tablas en la base de datos {dbname}:")

    for table in tables:
        cursor.execute(f"SELECT * from {table[0]}")
        print_table(table[0], [desc[0] for desc in cursor.description], cursor.fetchall())
        print()

def print_table(name, headers, lines):
    if not lines:
        return
    if not lines[0]:
        return
    table = list()
    column_widths = list(map(len, headers))

    for line in lines:
        column_widths = [max(width, len(str(cell))) for width, cell in zip(column_widths, line)]
        table.append(line)

    separator = "+-" + "-+-".join("-" * length for length in column_widths) + "-+"
    print(separator)
    line_len = 3 * (len(headers) - 1) + sum(column_widths)
    print("| " + f"{name:^{line_len}}" + " |")
    print(separator)
    header_line = "| " + " | ".join(
        f"{header:{width}}"
        for width, header in zip(column_widths, headers)
    ) + " |"
    print(header_line)
    print(separator)
    #print("| " + " | ".join(map( lambda ind, x: f"x:>{column_lengths[ind]}", enumerate(headers))) + " |")
    for line in table:
        print("| " + " | ".join(f"{x:.>{width}}" for x, width in zip(line, column_widths)) + " |")
    print(separator)


def generate_er(user="user", password="pass", host="localhost"):
  """eralchemy"""
  from eralchemy import render_er
  
  connection_str = f'mysql+mysqlconnector://{user}:{password}@{host}/{dbname}'
  render_er(connection_str, 'er_diagram.png')
  from IPython.display import Image
  Image('er_diagram.png')

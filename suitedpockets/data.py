import pyodbc
from azure.identity import DefaultAzureCredential
import os
import pandas as pd
import struct


SERVER = os.environ.get('DB_SERVER') or 'suitedpockets.database.windows.net'

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE=poker;"
    f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60"
)

def get_conn(conn_str: str) -> pyodbc.Connection:

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
    conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})

    return conn


def load_games():
    with get_conn(connection_string) as conn:
        pdata = pd.read_sql(
            sql="SELECT * FROM vw_game",
            con=conn
        )

    pdata['game_date'] = pd.to_datetime(pdata['game_date']).dt.date
    return pdata


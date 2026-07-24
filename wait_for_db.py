#!/usr/bin/env python3
import os
import time

import psycopg2
from psycopg2 import OperationalError

DB_USER = os.getenv("POSTGRES_USER", "logistic_system_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "logistic_system_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "logistic_system_db")

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

max_retries = 30
for i in range(max_retries):
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        print("PostgreSQL is ready!")
        break
    except OperationalError:
        print(f"PostgreSQL not ready yet ({i + 1}/{max_retries})...")
        time.sleep(2)
else:
    raise RuntimeError("PostgreSQL not available after 30 retries")

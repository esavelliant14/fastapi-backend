from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

JUN_USER = os.getenv("JUN_USER")
JUN_PASS = os.getenv("JUN_PASS")
JUN_PORT = int(os.getenv("JUN_PORT", 22))


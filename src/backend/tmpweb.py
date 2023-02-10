import secrets
import sqlite3


def create_site():
    # Generated URLs will have a 9 byte long base64 path. As base64 encodes 3 bytes
    # to 4 characters this gives us a nice length of URL whilst having sufficient
    # keyspace for randomly finding a page to take many millennia.
    site_id = secrets.token_urlsafe(9)

"""
One-off script to create/reset the admin panel login.
Usage: python seed_admin.py <username> <password>
"""
import sys
from database import db
from admin_auth import hash_password

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python seed_admin.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    db.create_admin_user(username, hash_password(password))
    print(f"Admin user '{username}' created/updated successfully.")

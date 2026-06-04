#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/kevin/kantorteman/backend')

# Load env vars
from dotenv import load_dotenv
load_dotenv('/home/kevin/kantorteman/backend/.env')

from main import SessionLocal, User
import bcrypt

db = SessionLocal()

# Check if admin user exists
admin = db.query(User).filter(User.email == "admin@kantorteman.com").first()
if admin:
    print("Admin user already exists")
else:
    # Create admin user
    hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    admin = User(
        name="Admin",
        email="admin@kantorteman.com",
        hashed_password=hashed,
        role="admin"
    )
    db.add(admin)
    db.commit()
    print("Admin user created successfully")

db.close()

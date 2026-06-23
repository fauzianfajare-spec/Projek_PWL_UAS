import os
import django
import firebase_admin
from firebase_admin import credentials, firestore

# Set environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owichat.settings')
django.setup()

db = firestore.client()

print("--- USERS IN FIRESTORE ---")
try:
    users_ref = db.collection('users').stream()
    count = 0
    for doc in users_ref:
        print(f"Document ID: {doc.id}")
        print(f"Data: {doc.to_dict()}")
        print("-" * 30)
        count += 1
    print(f"Total users found: {count}")
except Exception as e:
    import traceback
    print("Error listing users:")
    traceback.print_exc()

#!/usr/bin/env python
import os
import django
from firebase_admin import auth, firestore

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owichat.settings')
django.setup()

db = firestore.client()

# Test users data
test_users = [
    {
        'username': 'admin',
        'email': 'admin@owichat.com',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'System',
    },
    {
        'username': 'alice',
        'email': 'alice@owichat.com',
        'password': 'password123',
        'first_name': 'Alice',
        'last_name': 'Johnson',
    },
    {
        'username': 'bob',
        'email': 'bob@owichat.com',
        'password': 'password123',
        'first_name': 'Bob',
        'last_name': 'Smith',
    },
    {
        'username': 'charlie',
        'email': 'charlie@owichat.com',
        'password': 'password123',
        'first_name': 'Charlie',
        'last_name': 'Brown',
    },
    {
        'username': 'diana',
        'email': 'diana@owichat.com',
        'password': 'password123',
        'first_name': 'Diana',
        'last_name': 'Prince',
    },
]

uids_by_username = {}

for u_data in test_users:
    username = u_data['username']
    email = u_data['email']
    password = u_data['password']
    
    uid = None
    try:
        # Check if user already exists in Firebase Auth
        user_record = auth.get_user_by_email(email)
        uid = user_record.uid
        print(f"User '{username}' already exists in Firebase Auth (UID: {uid})")
    except auth.UserNotFoundError:
        # Create user in Firebase Auth
        try:
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )
            uid = user_record.uid
            print(f"User '{username}' created successfully in Firebase Auth (UID: {uid})")
        except Exception as e:
            print(f"Failed to create user '{username}' in Firebase Auth: {e}")
            continue
    except Exception as e:
        print(f"Error checking user '{username}' in Firebase Auth: {e}")
        continue

    if uid:
        uids_by_username[username] = uid
        # Store/Update profile in Firestore
        try:
            db.collection('users').document(uid).set({
                'username': username,
                'email': email,
                'phone': '',
                'bio': f'Hello, I am {username}!',
                'avatar': '',
                'first_name': u_data['first_name'],
                'last_name': u_data['last_name'],
            }, merge=True)
            print(f"User profile '{username}' saved/updated in Firestore.")
        except Exception as e:
            print(f"Failed to save user profile for '{username}' in Firestore: {e}")

# Create test group conversation "Web Development Team"
group_name = "Web Development Team"
group_participants = ['alice', 'bob', 'charlie']

participant_uids = [uids_by_username[uname] for uname in group_participants if uname in uids_by_username]
creator_username = 'alice'

if len(participant_uids) >= 2:
    creator_uid = uids_by_username.get(creator_username)
    if creator_uid:
        try:
            # Check if group already exists in Firestore conversations
            convs_ref = db.collection('conversations')
            query = convs_ref.where('conversation_type', '==', 'group').where('name', '==', group_name).limit(1).stream()
            group_exists = False
            for doc in query:
                group_exists = True
                print(f"Group '{group_name}' already exists in Firestore (ID: {doc.id})")
                break
            
            if not group_exists:
                # Add group to Firestore
                new_group_ref = convs_ref.document()
                new_group_ref.set({
                    'name': group_name,
                    'conversation_type': 'group',
                    'participants': participant_uids,
                    'created_by': creator_uid,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'group_avatar': ''
                })
                print(f"Group '{group_name}' created successfully in Firestore (ID: {new_group_ref.id})")
        except Exception as e:
            print(f"Failed to check or create group '{group_name}' in Firestore: {e}")
else:
    print(f"Not enough participants successfully created in Firebase to create a group.")

print("\n[SUCCESS] Setup completed successfully!")
print("Admin credentials: username=admin, password=admin123")
print("Test users: alice, bob, charlie, diana (password: password123)")

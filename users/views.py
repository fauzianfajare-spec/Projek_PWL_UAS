from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
from chat.decorators import firebase_login_required
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib import messages
import json
import firebase_admin
from firebase_admin import auth, firestore
import requests
import os

# Pastikan Firestore client sudah terinisialisasi
db = firestore.client()

# GANTI INI dengan Web API Key dari Project Settings Firebase Console kamu!
FIREBASE_WEB_API_KEY = "AIzaSyD9l4LlyC641lKqAMPS1tUPylyGWBWlto4"

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            return render(request, 'users/register.html', {'error': 'Passwords do not match'})

        uid = None
        try:
            # 1. Coba daftarkan akun baru ke Firebase Authentication
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )
            uid = user_record.uid
        except Exception as auth_error:
            # Jika error karena email sudah ada, kita ambil UID dari email yang sudah terdaftar tersebut
            error_str = str(auth_error)
            if "EMAIL_EXISTS" in error_str or "already exists" in error_str:
                try:
                    user_record = auth.get_user_by_email(email)
                    uid = user_record.uid
                except Exception:
                    return render(request, 'users/register.html', {'error': f'Gagal mendapatkan data user: {str(auth_error)}'})
            else:
                # Jika error lainnya (seperti masalah konfigurasi), tampilkan errornya
                return render(request, 'users/register.html', {'error': f'Registrasi gagal: {error_str}'})

        # 2. Buat / Pastikan dokumen profil tersimpan di Firestore
        if uid:
            try:
                db.collection('users').document(uid).set({
                    'username': username,
                    'email': email,
                    'phone': '',
                    'bio': '',
                    'avatar': '',
                    'is_online': False
                })
                
                # 3. ALUR SUKSES MUTLAK: Langsung alihkan ke halaman login
                return redirect('users:login')
            except Exception as firestore_error:
                return render(request, 'users/register.html', {'error': f'Gagal menyimpan profil ke Firestore: {str(firestore_error)}'})

    return render(request, 'users/register.html')

@csrf_exempt 
def google_auth(request):
    """
    Endpoint untuk Google Sign-In (Mendukung data POST Form & JSON, mengembalikan respon JSON)
    """
    if request.method == 'POST':
        try:
            # Ambil token dari POST parameter form
            id_token = request.POST.get('id_token')
            
            # Jika tidak ditemukan (karena dikirim via fetch JSON), coba baca dari request body
            if not id_token:
                try:
                    data = json.loads(request.body)
                    id_token = data.get('id_token')
                except (json.JSONDecodeError, TypeError):
                    pass
            if not id_token:
                messages.error(request, 'Token tidak ditemukan dari Google Sign-In')
                return redirect('users:login')

            # 1. Verifikasi ID Token dari Firebase Google Sign-In
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            
            username_google = decoded_token.get('name', email.split('@')[0])
            picture_google = decoded_token.get('picture', '/static/images/default-avatar.png')

            # 2. Cek/Simpan data ke Firestore
            user_ref = db.collection('users').document(uid)
            doc = user_ref.get()

            if not doc.exists:
                user_ref.set({
                    'username': username_google,
                    'email': email,
                    'phone': '',
                    'bio': '',
                    'avatar': picture_google,
                    'is_online': True,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                username_final = username_google
                avatar_final = picture_google
            else:
                user_data = doc.to_dict()
                username_final = user_data.get('username', username_google)
                avatar_final = user_data.get('avatar', picture_google)
                user_ref.update({'is_online': True})

            # 3. Sinkronisasi Session Django secara mutlak
            request.session['firebase_user_uid'] = uid
            request.session['username'] = username_final
            request.session['avatar'] = avatar_final
            request.session['email'] = email  # Sesuai kebutuhan fungsi add_contact Anda!
            request.session.modified = True

            # 4. ALUR UTAMA: Kirim respon sukses beserta URL tujuan
            return redirect('chat:chat_list')

        except Exception as e:
            messages.error(request, f"Autentikasi Google gagal: {str(e)}")
            return redirect('users:login')

    messages.error(request, 'Metode tidak diizinkan')
    return redirect('users:login')

@csrf_exempt
def login_view(request):
    """
    Endpoint khusus untuk Login menggunakan Email & Password manual.
    Logika Google telah dipindahkan sepenuhnya ke google_auth.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # 1. Verifikasi login ke Firebase Auth REST API resmi
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                user_firebase_uid = data['localId']
                
                # 2. Ambil data dari Firestore
                username_dari_firestore = data.get('displayName', email.split('@')[0])
                avatar_dari_firestore = '/static/images/default-avatar.png'
                
                try:
                    user_doc = db.collection('users').document(user_firebase_uid).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        username_dari_firestore = user_data.get('username', username_dari_firestore)
                        avatar_dari_firestore = user_data.get('avatar', avatar_dari_firestore)
                        db.collection('users').document(user_firebase_uid).update({
                            'is_online': True
                        })
                except Exception as doc_error:
                    print(f"Gagal mengambil data dari Firestore: {doc_error}")
                
                # 3. Simpan data user ke Session Django
                request.session['firebase_user_uid'] = user_firebase_uid
                request.session['username'] = username_dari_firestore
                request.session['avatar'] = avatar_dari_firestore
                request.session.modified = True
                
                return redirect('chat:chat_list')
            
            else:
                error_message = data.get('error', {}).get('message', 'INVALID_LOGIN_CREDENTIALS')
                if error_message in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
                    return render(request, 'users/login.html', {'error': 'Email atau password yang kamu masukkan salah!'})
                return render(request, 'users/login.html', {'error': f'Login gagal: {error_message}'})
                
        except Exception as e:
            return render(request, 'users/login.html', {'error': f'Koneksi error: {str(e)}'})
            
    return render(request, 'users/login.html')

def logout_view(request):
    my_uid = request.session.get('firebase_user_uid')
    if my_uid:
        try:
            db.collection('users').document(my_uid).update({
                'is_online': False
            })
        except Exception as e:
            print(f"Gagal update status offline di Firestore saat logout: {e}")
            
    request.session.flush()
    return redirect('users:login')


# Fungsi user_profile yang duplikat sebelumnya telah dibersihkan, menyisakan versi dengan decorator ini
@firebase_login_required
def user_profile(request, username):
    try:
        users_ref = db.collection('users').where('username', '==', username).limit(1).stream()
        profile_data = None
        profile_uid = None
        
        for doc in users_ref:
            profile_data = doc.to_dict()
            profile_uid = doc.id 
            
        if not profile_data:
            return HttpResponse("Pengguna tidak ditemukan.", status=404)
            
        context = {
            'profile': profile_data,
            'profile_uid': profile_uid,
            'profile_user_username': username,
        }
        return render(request, 'users/profile.html', context)
    except Exception as e:
        return HttpResponse(f"Error Firestore: {e}", status=500)


@firebase_login_required
def edit_profile(request):
    my_uid = request.session.get('firebase_user_uid')
    doc_ref = db.collection('users').document(my_uid)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        bio = request.POST.get('bio', '').strip()
        
        doc = doc_ref.get()
        old_data = doc.to_dict() if doc.exists else {}
        
        update_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'bio': bio,
            'username': old_data.get('username', request.session.get('username')),
            'avatar': old_data.get('avatar', '/static/images/default-avatar.png')
        }
        
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            fs = FileSystemStorage()
            filename = fs.save(f"avatars/{my_uid}_{avatar_file.name}", avatar_file)
            avatar_url = fs.url(filename)
            update_data['avatar'] = avatar_url

        try:
            doc_ref.set(update_data, merge=True)
            
            request.session['username'] = update_data['username']
            request.session['avatar'] = update_data['avatar']
            request.session.modified = True
            
            return redirect('users:user_profile', username=update_data['username'])
            
        except Exception as e:
            return render(request, 'users/edit_profile.html', {
                'error': f"Gagal menyimpan ke Firebase: {e}",
                'profile': update_data
            })
            
    else:
        doc = doc_ref.get()
        profile_data = doc.to_dict() if doc.exists else {}
        return render(request, 'users/edit_profile.html', {'profile': profile_data})


@firebase_login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    my_username = request.session.get('username')
    results = []

    if query:
        try:
            users_ref = db.collection('users').stream()
            for doc in users_ref:
                u_data = doc.to_dict()
                username_cloud = u_data.get('username', '')
                
                if query.lower() in username_cloud.lower() and username_cloud != my_username:
                    u_data['uid'] = doc.id
                    results.append(u_data)
        except Exception as e:
            print(f"Error saat mencari user di Firestore: {e}")

    return render(request, 'users/search.html', {'results': results, 'query': query})


@firebase_login_required
def delete_user(request):
    my_uid = request.session.get('firebase_user_uid')
    try:
        db.collection('users').document(my_uid).delete()
        auth.delete_user(my_uid)
        request.session.flush()
        return redirect('users:register')
    except Exception as e:
        doc_ref = db.collection('users').document(my_uid)
        doc = doc_ref.get()
        profile_data = doc.to_dict() if doc.exists else {}
        return render(request, 'users/edit_profile.html', {
            'profile': profile_data,
            'error': f'Gagal menghapus akun: {str(e)}'
        })
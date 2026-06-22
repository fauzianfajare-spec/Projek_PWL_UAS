from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
from chat.decorators import firebase_login_required
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
                })
                
                # 3. ALUR SUKSES MUTLAK: Langsung alihkan ke halaman login
                return redirect('users:login')
            except Exception as firestore_error:
                return render(request, 'users/register.html', {'error': f'Gagal menyimpan profil ke Firestore: {str(firestore_error)}'})

    return render(request, 'users/register.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # 1. Melakukan verifikasi login ke Firebase Auth REST API resmi
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            # Jika Firebase mengembalikan status HTTP 200 (Berhasil)
            if response.status_code == 200:
                user_firebase_uid = data['localId']
                
                # 2. Ambil data username asli dari Firestore Cloud berdasarkan UID
                username_dari_firestore = None
                avatar_dari_firestore = None
                try:
                    user_doc = db.collection('users').document(user_firebase_uid).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        username_dari_firestore = user_data.get('username')
                        avatar_dari_firestore = user_data.get('avatar')
                        # Update status online to True
                        db.collection('users').document(user_firebase_uid).update({
                            'is_online': True
                        })
                except Exception as doc_error:
                    print(f"Gagal mengambil data username / update status online dari Firestore: {doc_error}")
                
                # Jika di Firestore tidak ada, gunakan default potongan email depan sebagai username
                if not username_dari_firestore:
                    username_dari_firestore = data.get('displayName', email.split('@')[0])
                
                # 3. Simpan data user ke Session Django agar statusnya terhitung "Masuk/Login"
                request.session['firebase_user_uid'] = user_firebase_uid
                request.session['username'] = username_dari_firestore
                request.session['avatar'] = avatar_dari_firestore
                request.session.modified = True
                
                # 4. ALUR SUKSES MUTLAK: Alihkan langsung ke halaman utama daftar obrolan
                return redirect('chat:chat_list')
            
            else:
                # Menangkap pesan error spesifik dari Firebase API
                error_message = data.get('error', {}).get('message', 'INVALID_LOGIN_CREDENTIALS')
                if error_message in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
                    return render(request, 'users/login.html', {'error': 'Email atau password yang kamu masukkan salah!'})
                return render(request, 'users/login.html', {'error': f'Login gagal: {error_message}'})
                
        except Exception as e:
            return render(request, 'users/login.html', {'error': f'Koneksi error: {str(e)}'})
            
    return render(request, 'users/login.html')

def logout_view(request):
    # Update status online to False
    my_uid = request.session.get('firebase_user_uid')
    if my_uid:
        try:
            db.collection('users').document(my_uid).update({
                'is_online': False
            })
        except Exception as e:
            print(f"Gagal update status offline di Firestore saat logout: {e}")
            
    # Hapus semua data session di browser
    request.session.flush()
    return redirect('users:login')


def user_profile(request, username):
    # Mengambil profil langsung dari Firestore berdasarkan username
    try:
        users_ref = db.collection('users').where('username', '==', username).limit(1).stream()
        profile_data = None
        user_uid = None
        
        for doc in users_ref:
            profile_data = doc.to_dict()
            user_uid = doc.id
            
        if not profile_data:
            return render(request, '404.html', {'error': 'User tidak ditemukan'})
            
        return render(request, 'users/profile.html', {
            'profile_user_username': username,
            'profile': profile_data,
            'profile_uid': user_uid
        })
    except Exception as e:
        return render(request, 'users/profile.html', {'error': str(e)})


# ========================================================
# FITUR TAMBAHAN: EDIT PROFILE FIREBASE FIRESTORE
# ========================================================
@firebase_login_required
def user_profile(request, username):
    try:
        # TANYA KE FIRESTORE: Cari user berdasarkan field 'username' (Bukan SQLite!)
        users_ref = db.collection('users').where('username', '==', username).limit(1).stream()
        profile_data = None
        profile_uid = None
        
        for doc in users_ref:
            profile_data = doc.to_dict()
            profile_uid = doc.id # Mengambil ID dokumen sebagai UID
            
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
        # Ambil data inputan dari Form HTML
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        bio = request.POST.get('bio', '').strip()
        
        # Ambil data profil lama di Firestore agar data penting (seperti username) tidak hilang
        doc = doc_ref.get()
        old_data = doc.to_dict() if doc.exists else {}
        
        # Siapkan data baru untuk di-update ke Firestore
        update_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'bio': bio,
            'username': old_data.get('username', request.session.get('username')),
            'avatar': old_data.get('avatar', '/static/images/default-avatar.png') # Default awal
        }
        
        # Proses Upload Avatar Baru jika user memasukkan file gambar
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            fs = FileSystemStorage()
            # Simpan file ke lokal media dengan nama unik berbasis UID
            filename = fs.save(f"avatars/{my_uid}_{avatar_file.name}", avatar_file)
            avatar_url = fs.url(filename) # Menghasilkan teks path seperti: /media/avatars/...
            update_data['avatar'] = avatar_url

        try:
            # SIMPAN LANGSUNG KE FIRESTORE (Menggunakan set dengan merge=True agar aman)
            doc_ref.set(update_data, merge=True)
            
            # Sinkronisasi data krusial ke session Django agar tidak terjadi miss-match
            request.session['username'] = update_data['username']
            request.session['avatar'] = update_data['avatar']
            request.session.modified = True
            
            # Berhasil! Redirect kembali ke halaman profile utama Anda
            return redirect('users:user_profile', username=update_data['username'])
            
        except Exception as e:
            return render(request, 'users/edit_profile.html', {
                'error': f"Gagal menyimpan ke Firebase: {e}",
                'profile': update_data
            })
            
    else:
        # JIKA AKSES HALAMAN (GET): Ambil data ter-update langsung dari Firestore untuk ditampilkan di Form
        doc = doc_ref.get()
        profile_data = doc.to_dict() if doc.exists else {}
        return render(request, 'users/edit_profile.html', {'profile': profile_data})


# ========================================================
# FITUR TAMBAHAN: PENCARIAN USER BERBASIS FIRESTORE
# ========================================================
@firebase_login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    my_username = request.session.get('username')
    results = []

    if query:
        try:
            # Mengambil data user dari Firestore yang username-nya mirip/sesuai dengan query
            users_ref = db.collection('users').stream()
            for doc in users_ref:
                u_data = doc.to_dict()
                username_cloud = u_data.get('username', '')
                
                # Filter: Cocokkan kata kunci, dan pastikan tidak memunculkan diri sendiri
                if query.lower() in username_cloud.lower() and username_cloud != my_username:
                    u_data['uid'] = doc.id  # Simpan UID-nya untuk link profil/chat
                    results.append(u_data)
        except Exception as e:
            print(f"Error saat mencari user di Firestore: {e}")

    return render(request, 'users/search.html', {'results': results, 'query': query})


@firebase_login_required
def delete_user(request):
    my_uid = request.session.get('firebase_user_uid')
    try:
        # Hapus dokumen pengguna dari Firestore
        db.collection('users').document(my_uid).delete()
        
        # Hapus user dari Firebase Authentication
        auth.delete_user(my_uid)
        
        # Bersihkan session Django
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

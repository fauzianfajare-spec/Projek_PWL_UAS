from django.shortcuts import render, redirect, get_object_or_404
from chat.decorators import firebase_login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import traceback
from django.contrib import messages
from django.conf import settings


# ========================================================
# 1. KONFIGURASI KONEKSI FIREBASE (Berjalan 1 Kali)
# ========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.join(BASE_DIR, 'firebase-key.json')
GEMINI_API_KEY = "AQ.Ab8RN6KNKQ5gGZW-yR7r6bC17zhEqzdoKMRNlMSMkVCncBPdtQ"
if not firebase_admin._apps:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def muat_kata_kasar():
    """Fungsi dinamis untuk membaca file kata_kasar.txt dan kata_kasar.json"""
    kata_terlarang = set()

    # 1. Baca dari file .txt
    path_txt = os.path.join(settings.BASE_DIR, 'chat', 'kata_kasar.txt')
    if os.path.exists(path_txt):
        with open(path_txt, 'r', encoding='utf-8') as f:
            for baris in f:
                kata = baris.strip().lower()
                if kata:
                    kata_terlarang.add(kata)

    # 2. Baca dari file .json
    path_json = os.path.join(settings.BASE_DIR, 'chat', 'kata_kasar.json')
    if os.path.exists(path_json):
        try:
            with open(path_json, 'r', encoding='utf-8') as f:
                data_json = json.load(f)
                if isinstance(data_json, list):
                    for item in data_json:
                        kata = str(item).strip().lower()
                        if kata:
                            kata_terlarang.add(kata)
        except Exception as e:
            print(f"Error membaca file JSON kata kasar: {e}")
                    
    daftar_kata = list(kata_terlarang)
    daftar_kata.sort(key=len, reverse=True)
    return daftar_kata

def filter_kata_kasar(teks_input):
    """Fungsi untuk menyensor kata berdasarkan gabungan .txt dan .json"""
    if not teks_input:
        return teks_input
        
    daftar_kata = muat_kata_kasar()
    if not daftar_kata:
        return teks_input
        
    teks_hasil = teks_input
    for kata in daftar_kata:
        pola = re.compile(r'\b' + re.escape(kata) + r'\b', re.IGNORECASE)
        teks_hasil = pola.sub("*" * len(kata), teks_hasil)
        
    return teks_hasil

# ========================================================
# 2. HELPER CLASSES FOR FIREBASE DATA EMULATION IN TEMPLATES
# ========================================================

class FirestoreImageField:
    def __init__(self, url):
        self.url = url

class FirestoreUserProfile:
    def __init__(self, username, data):
        self.username = username
        self.phone = data.get('phone', '')
        self.bio = data.get('bio', '')
        self.avatar_str = data.get('avatar', '')
        self.is_online = data.get('is_online', False)
        
    @property
    def avatar(self):
        if self.avatar_str:
            return FirestoreImageField(self.avatar_str)
        return None

    def get_avatar_url(self):
        if self.avatar_str:
            return self.avatar_str
        return f"https://ui-avatars.com/api/?name={self.username}&background=667eea&color=fff"

class FirestoreUser:
    def __init__(self, uid, data):
        self.id = uid
        self.username = data.get('username', '')
        self.email = data.get('email', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.profile = FirestoreUserProfile(self.username, data)

    def get_full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.username

class FirestoreConversation:
    def __init__(self, conv_id, data, users_map):
        self.id = conv_id
        self.name = data.get('name', '')
        self.conversation_type = data.get('conversation_type', 'private')
        self.created_by = data.get('created_by', '')
        self.participant_uids = data.get('participants', [])
        self._users_map = users_map
        self.last_message_text = "Belum ada obrolan"
        
        avatar_str = data.get('group_avatar', '')
        self.group_avatar = FirestoreImageField(avatar_str) if avatar_str else None

    @property
    def participants(self):
        class ParticipantsHelper:
            def __init__(self, uids, users_map):
                self._uids = uids
                self._users_map = users_map

            def all(self):
                res = []
                for uid in self._uids:
                    user_info = self._users_map.get(uid, {})
                    res.append(FirestoreUser(uid, user_info))
                return res

            def count(self):
                return len(self._uids)
            
            def filter(self, username=None):
                class FilterHelper:
                    def __init__(self, users):
                        self._users = users
                    def exists(self):
                        return len(self._users) > 0
                
                filtered = []
                for uid in self._uids:
                    user_info = self._users_map.get(uid, {})
                    u = FirestoreUser(uid, user_info)
                    if username is None or u.username == username:
                        filtered.append(u)
                return FilterHelper(filtered)
        
        return ParticipantsHelper(self.participant_uids, self._users_map)

# ========================================================
# 3. VIEWS IMPLEMENTATION
# ========================================================

@firebase_login_required 
def leave_group(request, pk):
    my_uid = request.session.get('firebase_user_uid')

    try:
        conv_ref = db.collection('conversations').document(pk)
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            messages.error(request, "Grup tidak ditemukan.")
            return redirect('chat:chat_list')
        
        conv_data = conv_doc.to_dict()
        if conv_data.get('conversation_type') != 'group':
            messages.error(request, "Percakapan ini bukan grup.")
            return redirect('chat:chat_list')

        participants = conv_data.get('participants', [])
        if my_uid in participants:
            participants.remove(my_uid)
            conv_ref.update({
                'participants': participants,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            messages.success(request, f"Anda telah keluar dari grup '{conv_data.get('name')}'.")
        else:
            messages.error(request, "Anda bukan anggota grup ini.")
    except Exception as e:
        messages.error(request, f"Gagal keluar dari grup: {str(e)}")

    return redirect('chat:chat_list')


@firebase_login_required
def chat_list(request):
    my_uid = request.session.get('firebase_user_uid')
    my_username = request.session.get('username')

    try:
        all_users = {}
        for doc in db.collection('users').stream():
            all_users[doc.id] = doc.to_dict()

        conv_docs = db.collection('conversations') \
                      .where('participants', 'array_contains', my_uid) \
                      .stream()

        conversations = []
        for doc in conv_docs:
            conv_data = doc.to_dict()
            conv_obj = FirestoreConversation(doc.id, conv_data, all_users)

            try:
                docs = db.collection('messages') \
                         .where('conversation_id', '==', doc.id) \
                         .stream()
                
                messages_list = []
                for m_doc in docs:
                    d = m_doc.to_dict()
                    if not d.get('is_deleted', False):
                        messages_list.append(d)
                
                if messages_list:
                    def ambil_waktu_terakhir(msg):
                        w = msg.get('created_at')
                        return w.timestamp() if w and hasattr(w, 'timestamp') else 0
                    
                    messages_list.sort(key=ambil_waktu_terakhir, reverse=True)
                    last_message = messages_list[0]
                    conv_obj.last_message_text = filter_kata_kasar(last_message.get('text') or 'Mengirim gambar/file')
                else:
                    conv_obj.last_message_text = "Belum ada obrolan"
            except Exception as e:
                print(f"Error mengambil pesan terakhir di chat_list: {e}")
                conv_obj.last_message_text = "Gagal memuat pesan"

            conversations.append(conv_obj)

        added_friends = []
        seen_friend_uids = set()

        for conv in conversations:
            if conv.conversation_type == 'private':
                for p_uid in conv.participant_uids:
                    if p_uid != my_uid and p_uid not in seen_friend_uids:
                        seen_friend_uids.add(p_uid)
                        user_info = all_users.get(p_uid, {})
                        display_name = user_info.get('username', 'Unknown')
                        avatar_url = user_info.get('avatar')
                        added_friends.append({
                            'user': {
                                'id': p_uid
                            },
                            'display_name': display_name,
                            'profile_image': FirestoreImageField(avatar_url) if avatar_url else None
                        })

    except Exception as e:
        print(f"Error in chat_list: {traceback.format_exc()}")
        conversations = []
        added_friends = []

    return render(request, 'chat/chat_list.html', {
        'conversations': conversations,
        'users': added_friends  
    })


@firebase_login_required
def conversation_detail(request, pk):
    my_uid = request.session.get('firebase_user_uid')
    my_username = request.session.get('username')

    try:
        all_users = {}
        for doc in db.collection('users').stream():
            all_users[doc.id] = doc.to_dict()

        conv_doc = db.collection('conversations').document(pk).get()
        if not conv_doc.exists:
            return redirect('chat:chat_list')

        conv_data = conv_doc.to_dict()
        conversation = FirestoreConversation(pk, conv_data, all_users)

        is_participant = my_uid in conversation.participant_uids
        if not is_participant:
            return redirect('chat:chat_list')

        conv_docs = db.collection('conversations') \
                      .where('participants', 'array_contains', my_uid) \
                      .stream()

        conversations = []
        for doc in conv_docs:
            c_data = doc.to_dict()
            c_obj = FirestoreConversation(doc.id, c_data, all_users)

            try:
                docs = db.collection('messages') \
                         .where('conversation_id', '==', doc.id) \
                         .stream()
                
                messages_list = []
                for m_doc in docs:
                    d = m_doc.to_dict()
                    if not d.get('is_deleted', False):
                        messages_list.append(d)
                
                if messages_list:
                    def ambil_waktu_terakhir(msg):
                        w = msg.get('created_at')
                        return w.timestamp() if w and hasattr(w, 'timestamp') else 0
                    
                    messages_list.sort(key=ambil_waktu_terakhir, reverse=True)
                    last_message = messages_list[0]
                    c_obj.last_message_text = filter_kata_kasar(last_message.get('text') or 'Mengirim gambar/file')
                else:
                    c_obj.last_message_text = "Belum ada obrolan"
            except Exception as e:
                c_obj.last_message_text = "Gagal memuat pesan"

            conversations.append(c_obj)

        added_friends = []
        seen_friend_uids = set()

        for c_obj in conversations:
            if c_obj.conversation_type == 'private':
                for p_uid in c_obj.participant_uids:
                    if p_uid != my_uid and p_uid not in seen_friend_uids:
                        seen_friend_uids.add(p_uid)
                        user_info = all_users.get(p_uid, {})
                        display_name = user_info.get('username', 'Unknown')
                        avatar_url = user_info.get('avatar')
                        added_friends.append({
                            'user': {
                                'id': p_uid
                            },
                            'display_name': display_name,
                            'profile_image': FirestoreImageField(avatar_url) if avatar_url else None
                        })

        chat_messages = []
        try:
            docs = db.collection('messages') \
                     .where('conversation_id', '==', pk) \
                     .stream()
                     
            for doc in docs:
                data = doc.to_dict()
                if data.get('is_deleted', False):
                    continue
                    
                data['id_firebase'] = doc.id  
                
                waktu = data.get('created_at')
                if waktu and hasattr(waktu, 'timestamp'):
                    data['created_at'] = {
                        'seconds': int(waktu.timestamp()),
                        'nanoseconds': 0
                    }
                else:
                    data['created_at'] = {
                        'seconds': int(timezone.now().timestamp()),
                        'nanoseconds': 0
                    }
                
                reactions_data = data.get('reactions', {})
                list_reaksi_bersih = []
                if isinstance(reactions_data, dict):
                    for user_id, emoji_char in reactions_data.items():
                        list_reaksi_bersih.append({
                            'user_id': user_id,
                            'emoji': emoji_char
                        })
                
                data['list_reaksi_bersih'] = list_reaksi_bersih
                data['text'] = filter_kata_kasar(data.get('text', ''))
                chat_messages.append(data)
                
            chat_messages.sort(key=lambda msg: msg.get('created_at', {}).get('seconds', 0))
                
        except Exception as e:
            print(f"[ERROR FIRESTORE READ]: {e}")
            chat_messages = []

    except Exception as e:
        print(f"Error in conversation_detail: {traceback.format_exc()}")
        return redirect('chat:chat_list')

    daftar_kata = muat_kata_kasar()
    daftar_kata_json = json.dumps(daftar_kata)

    return render(request, 'chat/conversation_detail.html', {
        'conversation': conversation,
        'conversations': conversations,
        'chat_messages': chat_messages,
        'my_username': my_username,
        'my_uid': my_uid,
        'users': added_friends,
        'is_participant': is_participant,
        'daftar_kata_kasar_json': daftar_kata_json,
    })

@firebase_login_required 
def create_group(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name') 
        selected_users = request.POST.getlist('selected_users')

        if not group_name:
            messages.error(request, "Nama grup tidak boleh kosong.")
            return redirect('chat:chat_list')

        my_uid = request.session.get('firebase_user_uid')
        if not my_uid:
            messages.error(request, "Sesi Anda telah berakhir. Silakan login kembali.")
            return redirect('login') 
            
        try:
            participants = list(set([my_uid] + selected_users))

            new_ref = db.collection('conversations').document()
            new_ref.set({
                'name': group_name,
                'conversation_type': 'group',
                'participants': participants,
                'created_by': my_uid,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'group_avatar': ''
            })
            
            messages.success(request, f"Grup '{group_name}' berhasil dibuat!")
            return redirect('chat:conversation_detail', pk=new_ref.id)
            
        except Exception as e:
            messages.error(request, f"Gagal membuat grup: {str(e)}")
            return redirect('chat:chat_list')
            
    return redirect('chat:chat_list')

@firebase_login_required
def start_conversation(request, user_id):
    my_uid = request.session.get('firebase_user_uid')
    
    if my_uid == user_id:
        messages.error(request, "Anda tidak dapat memulai obrolan dengan diri sendiri.")
        return redirect('chat:chat_list')
    
    try:
        query = db.collection('conversations') \
                  .where('conversation_type', '==', 'private') \
                  .where('participants', 'array_contains', my_uid) \
                  .stream()

        existing_conv_id = None
        for doc in query:
            conv_data = doc.to_dict()
            if user_id in conv_data.get('participants', []):
                existing_conv_id = doc.id
                break

        if existing_conv_id:
            return redirect('chat:conversation_detail', pk=existing_conv_id)
        
        new_ref = db.collection('conversations').document()
        new_ref.set({
            'name': '',
            'conversation_type': 'private',
            'participants': [my_uid, user_id],
            'created_by': my_uid,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'group_avatar': ''
        })
        return redirect('chat:conversation_detail', pk=new_ref.id)
    except Exception as e:
        messages.error(request, f"Gagal memulai percakapan: {str(e)}")
        return redirect('chat:chat_list')

@firebase_login_required
def get_messages(request, conversation_id):
    try:
        docs = db.collection('messages') \
                 .where('conversation_id', '==', conversation_id) \
                 .stream()
        
        chat_messages = []
        for doc in docs:
            data = doc.to_dict()
            if data.get('is_deleted', False):
                continue
                
            data['id_firebase'] = doc.id
            waktu = data.get('created_at')
            if waktu and hasattr(waktu, 'timestamp'):
                data['created_at'] = {
                    'seconds': int(waktu.timestamp()),
                    'nanoseconds': 0
                }
            else:
                data['created_at'] = {
                    'seconds': int(timezone.now().timestamp()),
                    'nanoseconds': 0
                }
            chat_messages.append(data)
            
        chat_messages.sort(key=lambda msg: msg.get('created_at', {}).get('seconds', 0))
        return JsonResponse({'status': 'success', 'messages': chat_messages})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_POST
@firebase_login_required
def send_message(request):
    my_username = request.session.get('username')
    my_uid = request.session.get('firebase_user_uid')
    conversation_id = request.POST.get('conversation_id')
    text = request.POST.get('text', '')
    text = filter_kata_kasar(text)
    
    image_url = None
    file_url = None 
    
    try:
        conv_doc = db.collection('conversations').document(conversation_id).get()
        if not conv_doc.exists:
            return JsonResponse({'status': 'error', 'message': 'Percakapan tidak ditemukan.'}, status=404)

        conv_data = conv_doc.to_dict()
        if conv_data.get('conversation_type') == 'group':
            if my_uid not in conv_data.get('participants', []):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Akses ditolak. Anda sudah bukan bagian dari grup ini.'
                }, status=403)
        
        db.collection('messages').add({
            'conversation_id': conversation_id,
            'sender': my_username,
            'sender_id': my_uid,
            'text': text,
            'image': image_url, 
            'file': file_url,  
            'created_at': firestore.SERVER_TIMESTAMP,
            'is_deleted': False,
            'reactions': {}
        })
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_POST
@firebase_login_required
def delete_message(request, message_id):
    try:
        db.collection('messages').document(message_id).update({
            'is_deleted': True
        })
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@firebase_login_required
def add_contact(request):
    my_username = request.session.get('username')
    my_uid = request.session.get('firebase_user_uid')
    search_query = request.POST.get('search_user', '').strip()
    
    if not search_query:
        messages.error(request, "Username tidak boleh kosong.")
        return redirect('chat:chat_list')
    
    if search_query == my_username:
        messages.error(request, "Anda tidak dapat menambahkan diri sendiri.")
        return redirect('chat:chat_list')
        
    try:
        contact_ref = db.collection('users').where('username', '==', search_query).limit(1).stream()
        contact_exists = False
        contact_uid = None
        for doc in contact_ref:
            contact_exists = True
            contact_uid = doc.id
            break
        
        if not contact_exists:
            messages.error(request, "Pengguna tidak ditemukan di sistem.")
            return redirect('chat:chat_list')
        
        query = db.collection('conversations') \
                  .where('conversation_type', '==', 'private') \
                  .where('participants', 'array_contains', my_uid) \
                  .stream()

        existing_conv_id = None
        for doc in query:
            conv_data = doc.to_dict()
            if contact_uid in conv_data.get('participants', []):
                existing_conv_id = doc.id
                break

        if existing_conv_id:
            messages.info(request, f"Obrolan dengan {search_query} sudah ada.")
            return redirect('chat:conversation_detail', pk=existing_conv_id)
        
        new_ref = db.collection('conversations').document()
        new_ref.set({
            'name': '',
            'conversation_type': 'private',
            'participants': [my_uid, contact_uid],
            'created_by': my_uid,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'group_avatar': ''
        })
        
        messages.success(request, f"Berhasil menambahkan {search_query}!")
        return redirect('chat:conversation_detail', pk=new_ref.id)
        
    except Exception as e:
        messages.error(request, f"Terjadi error: {str(e)}")
        return redirect('chat:chat_list')


@firebase_login_required
def add_member_ajax(request, conversation_id):
    try:
        conv_ref = db.collection('conversations').document(conversation_id)
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            return JsonResponse({'status': 'error', 'message': 'Grup tidak ditemukan.'}, status=404)
        
        conv_data = conv_doc.to_dict()
        if conv_data.get('conversation_type') != 'group':
            return JsonResponse({'status': 'error', 'message': 'Percakapan bukan grup.'}, status=400)
        
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                selected_user_ids = data.get('selected_users', [])
                
                if not selected_user_ids:
                    return JsonResponse({'status': 'error', 'message': 'Pilih minimal satu anggota.'}, status=400)
                
                current_participants = conv_data.get('participants', [])
                updated_participants = list(set(current_participants + selected_user_ids))
                
                conv_ref.update({
                    'participants': updated_participants,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                return JsonResponse({'status': 'success', 'message': 'Anggota berhasil ditambahkan!'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
                
        current_participants = conv_data.get('participants', [])
        all_users_docs = db.collection('users').stream()
        
        users_list = []
        for doc in all_users_docs:
            uid = doc.id
            if uid not in current_participants:
                u_data = doc.to_dict()
                display_name = u_data.get('username')
                users_list.append({
                    'id': uid,
                    'display_name': display_name,
                    'avatar_url': u_data.get('avatar') or f"https://ui-avatars.com/api/?name={display_name}&background=764ba2&color=fff"
                })
                
        return JsonResponse({'status': 'success', 'users': users_list})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Database Error: {str(e)}"}, status=500)


@firebase_login_required
def delete_conversation(request, pk):
    my_uid = request.session.get('firebase_user_uid')
    try:
        conv_ref = db.collection('conversations').document(pk)
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            messages.error(request, "Percakapan tidak ditemukan.")
            return redirect('chat:chat_list')
        
        conv_data = conv_doc.to_dict()
        if my_uid not in conv_data.get('participants', []):
            messages.error(request, "Anda tidak memiliki akses untuk menghapus percakapan ini.")
            return redirect('chat:chat_list')
        
        # Hapus semua pesan yang terasosiasi dengan conversation ini
        messages_ref = db.collection('messages').where('conversation_id', '==', pk).stream()
        for doc in messages_ref:
            db.collection('messages').document(doc.id).delete()
            
        # Hapus percakapan itu sendiri
        conv_ref.delete()
        
        messages.success(request, "Percakapan berhasil dihapus.")
    except Exception as e:
        messages.error(request, f"Gagal menghapus percakapan: {str(e)}")
        
    return redirect('chat:chat_list')
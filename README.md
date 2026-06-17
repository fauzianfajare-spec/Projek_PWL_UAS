# 🗨️ OWI Chat - Aplikasi Chat Real-time

Aplikasi chat modern yang memungkinkan pengguna untuk berkomunikasi secara real-time dengan fitur private chat, group chat, sharing media, dan lebih banyak lagi.

## ✨ Fitur Utama

- 👥 **User Authentication** - Registrasi dan login yang aman
- 💬 **Private Chat** - Chat pribadi one-to-one dengan pengguna lain
- 👨‍👩‍👧‍👦 **Group Chat** - Buat dan bergabung dengan grup chat
- 📸 **Media Sharing** - Bagikan foto dan file di chat
- ⏱️ **Real-time Updates** - Pesan yang dikirim dan diterima secara instant
- 👤 **User Profile** - Profil pengguna dengan avatar dan bio
- 🔍 **User Search** - Cari pengguna untuk mulai chat
- ✅ **Emoji Reactions** - Beri reaksi pada pesan (ready untuk dikembangkan)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone/Extract Repository**
   ```bash
   cd c:\Users\ASUS\KULIAH\CODE\OwiChat
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Database**
   ```bash
   python manage.py migrate
   ```

4. **Create Test Data** (Optional)
   ```bash
   python setup_test_data.py
   ```
   
   **Test Accounts:**
   - Admin: username=`admin`, password=`admin123`
   - Alice: username=`alice`, password=`password123`
   - Bob: username=`bob`, password=`password123`
   - Charlie: username=`charlie`, password=`password123`
   - Diana: username=`diana`, password=`password123`

5. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

6. **Access Application**
   - Open browser: http://localhost:8000/
   - Admin Panel: http://localhost:8000/admin/

## 📁 Project Structure

```
OwiChat/
├── owichat/              # Project settings
│   ├── settings.py       # Django settings
│   ├── urls.py           # URL routing
│   ├── asgi.py           # ASGI configuration
│   └── wsgi.py           # WSGI configuration
│
├── chat/                 # Chat app
│   ├── models.py         # Database models
│   ├── views.py          # Views
│   ├── urls.py           # URL routing
│   └── admin.py          # Admin config
│
├── users/                # Users app
│   ├── models.py         # User profile models
│   ├── views.py          # Views
│   ├── urls.py           # URL routing
│   ├── signals.py        # Signal handlers
│   └── admin.py          # Admin config
│
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── users/            # User-related templates
│   └── chat/             # Chat-related templates
│
├── static/               # Static files
│   ├── css/style.css     # Main stylesheet
│   └── js/main.js        # Main JavaScript
│
└── requirements.txt      # Dependencies
```

## 🔗 URL Routes

### Authentication
- `GET /users/login/` - Login page
- `POST /users/login/` - Process login
- `GET /users/register/` - Register page
- `POST /users/register/` - Process registration
- `GET /users/logout/` - Logout

### Users
- `GET /users/<username>/` - View user profile
- `GET /users/edit-profile/` - Edit profile
- `POST /users/edit-profile/` - Save profile changes
- `GET /users/search-users/` - Search users

### Chat
- `GET /` - Chat list
- `GET /conversation/<id>/` - View conversation
- `POST /new/` - Start new conversation
- `POST /create-group/` - Create group
- `GET /api/messages/<id>/` - Get messages
- `POST /api/send/` - Send message
- `POST /api/delete-message/<id>/` - Delete message

## 💻 Database Models

### UserProfile
- `user` - OneToOneField ke User
- `phone` - Nomor telepon
- `bio` - Biografi
- `avatar` - Foto profil
- `is_online` - Status online
- `last_seen` - Waktu terakhir dilihat
- `created_at` - Waktu pembuatan

### Conversation
- `name` - Nama percakapan (untuk grup)
- `conversation_type` - 'private' atau 'group'
- `participants` - ManyToMany ke User
- `created_by` - User yang membuat
- `group_avatar` - Avatar grup
- `created_at` - Waktu pembuatan
- `updated_at` - Waktu update

### Message
- `conversation` - ForeignKey ke Conversation
- `sender` - ForeignKey ke User
- `text` - Isi pesan
- `image` - Gambar (optional)
- `file` - File (optional)
- `created_at` - Waktu pembuatan
- `edited_at` - Waktu edit
- `is_deleted` - Apakah dihapus

### MessageReaction
- `message` - ForeignKey ke Message
- `user` - ForeignKey ke User
- `emoji` - Emoji reaction
- `created_at` - Waktu pembuatan

## 🎨 Frontend Features

### Pages
1. **Login Page** - Form login dengan styling modern
2. **Register Page** - Form registrasi dengan validasi
3. **Chat List** - Daftar semua percakapan
4. **Chat Room** - Area chat dengan pesan dan input
5. **User Profile** - Profil pengguna
6. **Edit Profile** - Form edit profil
7. **User Search** - Pencarian pengguna
8. **Create Group** - Form pembuatan grup

### Styling
- Modern gradient design (purple theme)
- Responsive layout
- Smooth animations
- Mobile-friendly interface

## 🔧 Teknologi yang Digunakan

- **Backend**: Django 6.0.5
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript (jQuery)
- **Real-time**: Django Channels
- **API**: Django REST Framework
- **Image Handling**: Pillow
- **Icons**: Font Awesome 6.4.0

## 📝 Fitur yang Bisa Dikembangkan

- [ ] WebSocket real-time messaging
- [ ] Emoji reactions dengan counter
- [ ] Message reactions summary
- [ ] Typing indicators
- [ ] Message read receipts
- [ ] User online status
- [ ] Call/Video call integration
- [ ] Message encryption
- [ ] File storage ke cloud
- [ ] Push notifications
- [ ] Dark mode theme
- [ ] Message search functionality
- [ ] Pinned messages
- [ ] Message threads/replies
- [ ] User blocking feature

## 🤝 Contribution

Untuk berkontribusi:

1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

Project ini gratis untuk digunakan.

## 👥 Team

**Kelompok OWI**
- Pengembang Web Lanjut

---

**Dibuat dengan ❤️ untuk kemudahan berkomunikasi**
"# Projek_PWL_UAS"  
"# Projek_PWL_UAS" 

// Load conversations on page load
$(document).ready(function() {
    loadConversations();
    
    // Auto-refresh conversations every 3 seconds
    setInterval(loadConversations, 3000);
});

function loadConversations() {
    $.ajax({
        url: '/api/conversations/',
        type: 'GET',
        success: function(data) {
            updateConversationList(data);
        }
    });
}

function updateConversationList(conversations) {
    const chatList = $('.chat-list');
    chatList.empty();
    
    if (conversations.length === 0) {
        chatList.html('<p class="no-chats">Tidak ada chat. Mulai percakapan baru!</p>');
        return;
    }
    
    conversations.forEach(conv => {
        const html = `
            <a href="/conversation/${conv.id}/" class="chat-item">
                <div class="chat-avatar">
                    <img src="${conv.avatar_url}" alt="${conv.name}">
                </div>
                <div class="chat-info">
                    <h4 class="chat-name">${conv.name}</h4>
                    <p class="chat-preview">${conv.last_message || 'Tidak ada pesan'}</p>
                </div>
                <div class="chat-time">${conv.last_message_time || ''}</div>
            </a>
        `;
        chatList.append(html);
    });
}

// Real-time auto-scroll to bottom
function scrollChatToBottom() {
    const container = $('#messagesContainer');
    if (container.length) {
        setTimeout(() => {
            container.scrollTop(container[0].scrollHeight);
        }, 100);
    }
}

// Load messages when page loads
$(document).ready(function() {
    scrollChatToBottom();
});

// Adjust textarea height based on content
$('.message-input').on('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Format time display
function formatTime(date) {
    const now = new Date();
    const messageDate = new Date(date);
    
    if (messageDate.toDateString() === now.toDateString()) {
        return messageDate.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    } else {
        return messageDate.toLocaleDateString('id-ID');
    }
}

// Add emoji picker (optional)
const emojiMap = {
    '😊': '😊', '❤️': '❤️', '😂': '😂', 
    '🔥': '🔥', '👍': '👍', '😭': '😭'
};

// Setup lazy loading for images
function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => imageObserver.observe(img));
    }
}

$(document).ready(setupLazyLoading);

// Notification handler
function showNotification(title, options = {}) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, options);
    }
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

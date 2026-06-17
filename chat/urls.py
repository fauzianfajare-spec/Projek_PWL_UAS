from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('conversation/<str:pk>/', views.conversation_detail, name='conversation_detail'),
    path('start/<str:user_id>/', views.start_conversation, name='start_conversation'),
    path('group/create/', views.create_group, name='create_group'),
    path('group/leave/<str:pk>/', views.leave_group, name='leave_group'),
    path('leave-group/<str:pk>/', views.leave_group, name='leave_group'),
    path('conversation/<str:conversation_id>/add-member/', views.add_member_ajax, name='add_member'),
    path('group/<str:conversation_id>/add-member-ajax/', views.add_member_ajax, name='add_member_ajax'),

    
    # Path untuk memproses tambah teman via offcanvas
    path('add-contact/', views.add_contact, name='add_contact'),
    
    # API endpoints
    path('api/messages/<str:conversation_id>/', views.get_messages, name='get_messages'),
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/delete-message/<str:message_id>/', views.delete_message, name='delete_message'),
]
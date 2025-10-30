from django.urls import path
from . import views
app_name = 'messaging'
 
urlpatterns = [
    path('lobby/', views.lobby, name='lobby'),
    path('chat/<str:recipient_username>/', views.chat, name='chat'),
    path('create-message/', views.create_message, name='create-message'),
    path("stream-chat-messages/<str:recipient_username>/", views.stream_chat_messages, name='stream-chat-messages'),
]
from django.urls import path
from . import views
app_name = 'messaging'
 
urlpatterns = [
    path('lobby/', views.lobby, name='lobby'),
    path('chat/<int:chat_room_id>/', views.chat, name='chat'),
    path('create-message/', views.create_message, name='create-message'),
    path("poll-chat-messages/<int:chat_room_id>/", views.poll_chat_messages, name="poll_chat_messages"),

]
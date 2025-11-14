from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from user_info.models import UserInfo
from .models import Message, ChatRoom
from django.utils.dateformat import format as dj_format

@login_required
def lobby(request):
    all_users = User.objects.all()

    if request.method == "POST":
        usernames = request.POST.getlist("participants")
        if not usernames:
            messages.error(request, "Please select at least one user.")
            return redirect("messaging:lobby")

        participants = list(User.objects.filter(username__in=usernames)) + [request.user]

        # check for existing chat with same participants
        existing_chats = ChatRoom.objects.annotate(num_participants=Count('participants')).filter(num_participants=len(participants))
        for chat in existing_chats:
            chat_users = list(chat.participants.all())
            if set(chat_users) == set(participants):
                return redirect("messaging:chat", chat_room_id=chat.id)

        chat_room = ChatRoom.objects.create()
        chat_room.participants.set(participants)
        chat_room.save()
        return redirect("messaging:chat", chat_room_id=chat_room.id)

    current_chats = ChatRoom.objects.filter(participants=request.user)

    users_with_names = []
    for u in all_users:
        try:
            uinfo = UserInfo.objects.get(username=u.username)
            dn = uinfo.display_name or u.username
        except UserInfo.DoesNotExist:
            dn = u.username
        users_with_names.append({
            "username": u.username,
            "display_name": dn,
            "user_obj": u
        })

    return render(request, "lobby.html", {
        "all_users": all_users,
        "current_chats": current_chats,
        "users_with_names": users_with_names
    })


@login_required
def chat(request, chat_room_id):
    chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
    if request.user not in chat_room.participants.all():
        return HttpResponse("You are not a participant in this chat.", status=403)

    all_messages = list(chat_room.messages.order_by("timestamp"))
    display_names = {}
    for user in chat_room.participants.all():
        try:
            uinfo = UserInfo.objects.get(username=user.username)
            display_names[user.username] = uinfo.display_name or user.username
        except UserInfo.DoesNotExist:
            display_names[user.username] = user.username

    participants = []
    for u in chat_room.participants.exclude(id=request.user.id):
        participants.append({
            "user": u,
            "username": u.username,
            "display_name": display_names.get(u.username, u.username)
        })

    return render(request, "chat.html", {
        "username": display_names.get(request.user.username, request.user.username),
        "chat_room": chat_room,
        "messages": all_messages,
        "participants": participants,
    })


@login_required
def create_message(request):
    if request.method == "POST":
        chat_room_id = request.POST.get("chat_room_id")
        content = request.POST.get("content", "").strip()
        if not content:
            return JsonResponse({"success": False, "errors": {"content": "Message cannot be empty"}})

        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        Message.objects.create(
            sender=request.user,
            chat_room=chat_room,
            content=content
        )
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "errors": {"method": "Invalid request"}})


@login_required
def poll_chat_messages(request, chat_room_id):
    """AJAX polling endpoint for chat messages"""
    chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
    last_id = int(request.GET.get("after", 0))
    messages_qs = chat_room.messages.filter(id__gt=last_id).order_by("id")
    new_messages = []

    for msg in messages_qs:
        try:
            uinfo = UserInfo.objects.get(username=msg.sender.username)
            display_name = uinfo.display_name or msg.sender.username
        except UserInfo.DoesNotExist:
            display_name = msg.sender.username

        new_messages.append({
            "id": msg.id,
            "sender": msg.sender.username,
            "display_name": display_name,
            "content": msg.content,
            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({"messages": new_messages})

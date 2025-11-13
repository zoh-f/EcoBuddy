from django.shortcuts import render

# Create your views here.
from datetime import datetime
import asyncio
 
from typing import AsyncGenerator
from django.shortcuts import render, redirect
from django.http import HttpRequest, StreamingHttpResponse, HttpResponse
from . import models
from django.db import models
from django.contrib.auth.models import User
import json
import random
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from user_dashboard.models import Profile
from .models import Message, ChatRoom
from django.contrib import messages
from django.db.models import Q, Count
import time

 
@login_required
def lobby(request):
    if request.method == "POST":
        usernames_str = request.POST.get("usernames", "")  # string
        usernames = [u.strip() for u in usernames_str.split(",") if u.strip()]

        if not usernames:
            messages.error(request, "Please enter at least one username to start chat.")
            return redirect("messaging:lobby")

        # Include self in participants
        participants = list(User.objects.filter(username__in=usernames)) + [request.user]
        participant_ids = sorted([u.id for u in participants])

        # Get rooms that have the same number of participants
        existing_rooms = ChatRoom.objects.annotate(num_participants=Count('participants')).filter(
            num_participants=len(participant_ids)
        )

        # Find a room where the participant IDs match exactly
        for room in existing_rooms:
            room_ids = sorted(list(room.participants.values_list('id', flat=True)))
            if room_ids == participant_ids:
                chat_room = room
                break
        else:
            # No existing room, create a new one
            chat_room = ChatRoom.objects.create()
            chat_room.participants.set(participants)
        chat_room.participants.set(participants)
        chat_room.save()

        return redirect("messaging:chat", chat_room_id=chat_room.id)

    return render(request, "lobby.html")


@login_required
def chat(request, chat_room_id):
    chat_room = get_object_or_404(ChatRoom, id=chat_room_id)

    if request.user not in chat_room.participants.all():
        return HttpResponse("You are not a participant in this chat.", status=403)

    all_messages = list(chat_room.messages.order_by("timestamp"))
    other_participants = chat_room.participants.exclude(id=request.user.id)

    return render(request, "chat.html", {
        "username": request.user.username,
        "chat_room": chat_room,
        "messages": all_messages,
        "participants": other_participants,
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
def start_chat(request):
    if request.method == "GET":
        recipient_username = request.GET.get('recipient_username', '').strip()
        return redirect('messaging:chat', recipient_username=recipient_username)

 
@login_required
async def stream_chat_messages(request, chat_room_id):
    user = request.user
    last_id = 0
    KEEP_ALIVE_INTERVAL = 25
    last_keepalive = time.time()

    chat_room = await asyncio.to_thread(lambda: get_object_or_404(ChatRoom, id=chat_room_id))

    async def event_stream():
        nonlocal last_id, last_keepalive
        while True:
            # send keep-alive
            if time.time() - last_keepalive > KEEP_ALIVE_INTERVAL:
                yield ": keep-alive\n\n"
                last_keepalive = time.time()

            # fetch new messages
            new_messages = await asyncio.to_thread(
                lambda: list(
                    chat_room.messages.filter(id__gt=last_id)
                    .order_by("id")
                    .values("id", "sender__username", "content", "timestamp")
                )
            )

            for msg in new_messages:
                yield f"data: {json.dumps(msg)}\n\n"
                last_id = msg["id"]

            await asyncio.sleep(0.5)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

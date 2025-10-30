from django.shortcuts import render

# Create your views here.
from datetime import datetime
import asyncio
 
from typing import AsyncGenerator
from django.shortcuts import render, redirect
from django.http import HttpRequest, StreamingHttpResponse, HttpResponse
from . import models
import json
import random
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from user_dashboard.models import Profile
from .models import Message
from django.contrib import messages
from django.db.models import Q

 
@login_required
def lobby(request):
    if request.method == "POST":
        recipient_username = request.POST.get("recipient_username", "").strip()
        print(f"DEBUG recipient_username = '{recipient_username}'")

        # Print all usernames in the DB
        print("DEBUG all usernames:", list(Profile.objects.values_list("user__username", flat=True)))

        if not recipient_username:
            messages.error(request, "Please enter a username to start chat.")
            return redirect('messaging:lobby')

        try:
            recipient_profile = Profile.objects.get(user__username=recipient_username)
        except Profile.DoesNotExist:
            messages.error(request, f"No user found with username '{recipient_username}'.")
            return redirect('messaging:lobby')

        return redirect('messaging:chat', recipient_username=recipient_profile.user.username)

    return render(request, 'lobby.html')

@login_required
@login_required
def chat(request, recipient_username):
    recipient_profile = get_object_or_404(Profile, user__username=recipient_username)

    # Fetch messages separately
    messages_from_user = Message.objects.filter(sender=request.user, recipient=recipient_profile.user)
    messages_to_user = Message.objects.filter(sender=recipient_profile.user, recipient=request.user)

    # Merge and sort in Python
    all_messages = list(messages_from_user) + list(messages_to_user)
    all_messages.sort(key=lambda m: m.timestamp)  # or 'created_at' depending on your field

    return render(request, 'chat.html', {
        'username': request.user.username,
        'recipient': recipient_profile.user.username,
        'messages': all_messages
    })
 
@login_required
def create_message(request):
    if request.method == "POST":
        recipient_username = request.POST.get("recipient_username", "").strip()
        content = request.POST.get("content", "").strip()

        if not content:
            return JsonResponse({"success": False, "errors": {"content": "Message cannot be empty"}})

        # Lookup recipient via profile
        recipient_profile = get_object_or_404(Profile, user__username=recipient_username)

        Message.objects.create(
            sender=request.user,
            recipient=recipient_profile.user,
            content=content
        )

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "errors": {"method": "Invalid request"}})

@login_required
def start_chat(request):
    if request.method == "GET":
        recipient_username = request.GET.get('recipient_username', '').strip()
        return redirect('messaging:chat', recipient_username=recipient_username)

 
async def stream_chat_messages(request, recipient_username):
    user = request.user
    recipient = await asyncio.to_thread(
        lambda: get_object_or_404(Profile, user__username=recipient_username).user
    )

    async def get_existing_messages() -> AsyncGenerator[str, None]:
        messages = await asyncio.to_thread(
            lambda: list(
                models.Message.objects.filter(
                    (models.Q(sender=user, recipient=recipient) |
                     models.Q(sender=recipient, recipient=user))
                ).order_by("timestamp").values("id", "sender__username", "content")
            )
        )
        for message in messages:
            yield f"data: {json.dumps(message)}\n\n"

    async def get_last_message_id() -> int:
        last_message = await asyncio.to_thread(
            lambda: models.Message.objects.filter(
                (models.Q(sender=user, recipient=recipient) |
                 models.Q(sender=recipient, recipient=user))
            ).order_by("-id").first()
        )
        return last_message.id if last_message else 0

    async def event_stream():
        last_id = 0
        while True:
            # Fetch messages for this chat that are newer than last_id
            new_messages = await asyncio.to_thread(
                lambda: list(
                    models.Message.objects.filter(
                        Q(sender=user, recipient=recipient) |
                        Q(sender=recipient, recipient=user),
                        id__gt=last_id
                    ).order_by("id").values("id", "sender__username", "content")
                )
            )

            for msg in new_messages:
                yield f"data: {json.dumps(msg)}\n\n"
                last_id = msg["id"]

            await asyncio.sleep(0.5)  # small delay to avoid DB spam

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
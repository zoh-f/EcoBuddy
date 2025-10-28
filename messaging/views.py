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
def chat(request, recipient_username):
    recipient_profile = get_object_or_404(Profile, user__username=recipient_username)

    # fetch all messages between current user and recipient
    messages = Message.objects.filter(
        sender=request.user, recipient=recipient_profile.user
    ).union(
        Message.objects.filter(sender=recipient_profile.user, recipient=request.user)
    ).order_by('timestamp')

    return render(request, 'chat.html', {
        'username': request.user.username,
        'recipient': recipient_profile.user.username,
        'messages': messages
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

 
async def stream_chat_messages(request: HttpRequest) -> StreamingHttpResponse:
    """
    Streams chat messages to the client as we create messages.
    """
    async def event_stream():
        """
        We use this function to send a continuous stream of data
        to the connected clients.
        """
        async for message in get_existing_messages():
            yield message
 
        last_id = await get_last_message_id()
 
        # Continuously check for new messages
        while True:
            new_messages = models.Message.objects.filter(id__gt=last_id).order_by('created_at').values(
                'id', 'author__name', 'content'
            )
            async for message in new_messages:
                yield f"data: {json.dumps(message)}\n\n"
                last_id = message['id']
            await asyncio.sleep(0.1)  # Adjust sleep time as needed to reduce db queries.
 
    async def get_existing_messages() -> AsyncGenerator:
        messages = models.Message.objects.all().order_by('created_at').values(
            'id', 'author__name', 'content'
        )
        async for message in messages:
            yield f"data: {json.dumps(message)}\n\n"
 
    async def get_last_message_id() -> int:
        last_message = await models.Message.objects.all().alast()
        return last_message.id if last_message else 0
 
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
 
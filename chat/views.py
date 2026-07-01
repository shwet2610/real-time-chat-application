from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
import os
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponse

from .models import ChatRoom, Message, Profile



# def prepare_chatrooms(chatrooms, current_user):
#     """
#     Har chatroom ke saath extra data attach karega:
#     - other_user
#     - last_message
#     - unread_count

#     Important:
#     Unread count sirf current_user ke received unread messages ka hoga.
#     """
#     for room in chatrooms:
#         if room.user1_id == current_user.id:
#             room.other_user = room.user2
#         else:
#             room.other_user = room.user1

#         room.last_message = Message.objects.filter(
#             room=room
#         ).select_related("sender", "receiver").order_by("-created_at").first()

#         room.unread_count = Message.objects.filter(
#             room=room,
#             receiver_id=current_user.id,
#             is_read=False
#         ).exclude(
#             sender_id=current_user.id
#         ).count()

#     return chatrooms

def is_user_online(user):
    profile = Profile.objects.filter(user=user).first()

    if not profile or not profile.last_seen:
        return False

    return profile.last_seen >= timezone.now() - timedelta(seconds=90)

MAX_VOICE_NOTE_SIZE = 6 * 1024 * 1024

ALLOWED_VOICE_EXTENSIONS = [
    ".webm", ".ogg", ".mp3", ".wav", ".m4a"
]


def validate_voice_note(uploaded_file):
    if not uploaded_file:
        return True, ""

    extension = os.path.splitext(uploaded_file.name)[1].lower()

    if extension not in ALLOWED_VOICE_EXTENSIONS:
        return False, "Only voice note audio files are allowed."

    if uploaded_file.size > MAX_VOICE_NOTE_SIZE:
        return False, "Voice note should be less than 6 MB."

    return True, ""


def format_voice_duration(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = 0

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return f"{minutes}:{remaining_seconds:02d}"

def get_safe_file_url(file_field):
    try:
        if file_field and file_field.name:
            return file_field.url
    except ValueError:
        return ""

    return ""

def get_last_message_preview(message, current_user):
    if not message:
        return "No messages yet"

    if message.deleted_for_everyone:
        return "This message was deleted"

    if message.message:
        return message.message

    if message.voice_data or message.voice_note:
        return "🎙️ Voice message"

    return "No messages yet"


def get_last_message_preview(message, current_user):
    if not message:
        return "No messages yet"

    if message.deleted_for_everyone:
        return "This message was deleted"

    if message.message:
        return message.message

    if message.media_file:
        if message.media_type == "image":
            return "📷 Photo"

        return f"📎 {message.media_name}"

    return "No messages yet"


def get_message_status(message, current_user):
    if message.sender != current_user:
        return ""

    if message.seen_at:
        return "Seen"

    if message.delivered_at:
        return "Delivered"

    return "Sent"


def get_message_text_for_user(message, current_user):
    if message.deleted_for_everyone:
        return "This message was deleted"

    return message.message


def serialize_message(message, current_user=None):
    local_time = timezone.localtime(message.created_at)

    reply_data = None

    if message.reply_to:
        reply_data = {
            "id": message.reply_to.id,
            "message": get_message_text_for_user(message.reply_to, current_user),
            "sender_username": message.reply_to.sender.username,
        }

    status_text = ""

    if current_user:
        status_text = get_message_status(message, current_user)

    return {
        "id": message.id,
        "message_id": message.id,
        "room_id": message.room.id,

        "message": get_message_text_for_user(message, current_user),
        "original_message": message.message,

        "sender_id": message.sender.id,
        "receiver_id": message.receiver.id,
        "sender_username": message.sender.username,
        "receiver_username": message.receiver.username,

        "created_at": local_time.strftime("%I:%M %p"),

        "is_edited": message.is_edited,
        "is_deleted_for_everyone": message.deleted_for_everyone,

        "delivered_at": timezone.localtime(message.delivered_at).strftime("%I:%M %p") if message.delivered_at else "",
        "seen_at": timezone.localtime(message.seen_at).strftime("%I:%M %p") if message.seen_at else "",
        "status_text": status_text,

        "has_voice": bool(message.voice_data) or bool(get_safe_file_url(message.voice_note)),
        "voice_url": f"/voice/{message.id}/" if message.voice_data else get_safe_file_url(message.voice_note),
        "voice_duration": message.voice_duration,
        "voice_duration_text": format_voice_duration(message.voice_duration),

        "reply_to": reply_data,
    }



def prepare_chatrooms(chatrooms, current_user):
    prepared_rooms = []

    for room in chatrooms:
        if room.user1 == current_user:
            other_user = room.user2
        else:
            other_user = room.user1

        room.other_user = other_user

        room.last_message = room.messages.exclude(
            deleted_for=current_user
        ).order_by("-created_at").first()

        room.unread_count = Message.objects.filter(
            room=room,
            receiver=current_user,
            is_read=False,
            deleted_for_everyone=False
        ).exclude(
            deleted_for=current_user
        ).count()

        room.other_user_is_online = is_user_online(other_user)

        prepared_rooms.append(room)

    return prepared_rooms


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect("login")

    return render(request, "chat/register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid username or password.")
        return redirect("login")

    return render(request, "chat/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home_view(request):
    chatrooms = ChatRoom.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related("user1", "user2").order_by("-updated_at")

    chatrooms = prepare_chatrooms(chatrooms, request.user)

    return render(request, "chat/home.html", {
        "chatrooms": chatrooms
    })


@login_required
def users_view(request):
    search_query = request.GET.get("q", "").strip()
    users = User.objects.none()

    if search_query:
        users = User.objects.exclude(id=request.user.id).filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    return render(request, "chat/users.html", {
        "users": users,
        "search_query": search_query
    })


@login_required
def start_chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself.")
        return redirect("users")

    if request.user.id < other_user.id:
        user1 = request.user
        user2 = other_user
    else:
        user1 = other_user
        user2 = request.user

    room, created = ChatRoom.objects.get_or_create(
        user1=user1,
        user2=user2
    )

    return redirect("chat_room", room_id=room.id)


@login_required
def chat_room_view(request, room_id):
    room = get_object_or_404(
        ChatRoom.objects.select_related("user1", "user2"),
        id=room_id
    )

    if request.user.id not in [room.user1_id, room.user2_id]:
        messages.error(request, "You are not allowed to open this chat.")
        return redirect("home")

    if request.user == room.user1:
        other_user = room.user2
    else:
        other_user = room.user1

    other_user_is_online = is_user_online(other_user)

    chatrooms_query = ChatRoom.objects.filter(
        user1=request.user
    ) | ChatRoom.objects.filter(
        user2=request.user
    )

    chatrooms_query = chatrooms_query.select_related(
        "user1",
        "user2",
        "user1__profile",
        "user2__profile"
    ).order_by("-updated_at")

    chatrooms = prepare_chatrooms(chatrooms_query, request.user)

    now_time = timezone.now()

    Message.objects.filter(
        room=room,
        receiver=request.user,
        delivered_at__isnull=True,
        deleted_for_everyone=False
    ).exclude(
        deleted_for=request.user
    ).update(
        delivered_at=now_time
    )

    messages_list = Message.objects.filter(
        room=room
    ).exclude(
        deleted_for=request.user
    ).select_related(
        "sender",
        "receiver",
        "room",
        "reply_to",
        "reply_to__sender"
    ).order_by("created_at")

    for msg in messages_list:
        msg.display_message = get_message_text_for_user(msg, request.user)
        msg.status_text = get_message_status(msg, request.user)
        msg.voice_duration_text = format_voice_duration(msg.voice_duration)

    return render(request, "chat/chat_room.html", {
        "room": room,
        "other_user": other_user,
        "other_user_is_online": other_user_is_online,
        "messages_list": messages_list,
        "chatrooms": chatrooms,
    })


@login_required
@require_POST
def send_message_api(request, room_id):
    try:
        room = ChatRoom.objects.select_related("user1", "user2").get(id=room_id)

        if request.user.id not in [room.user1_id, room.user2_id]:
            return JsonResponse({
                "success": False,
                "error": "Not allowed"
            }, status=403)

        message_text = request.POST.get("message", "").strip()
        reply_to_id = request.POST.get("reply_to_id", "").strip()

        voice_note = request.FILES.get("voice_note")
        voice_duration = request.POST.get("voice_duration", "0")

        if not message_text and not voice_note:
            return JsonResponse({
                "success": False,
                "error": "Please type a message or record a voice note."
            }, status=400)

        is_valid_voice, voice_error = validate_voice_note(voice_note)

        if not is_valid_voice:
            return JsonResponse({
                "success": False,
                "error": voice_error
            }, status=400)

        try:
            voice_duration = int(float(voice_duration))
        except (TypeError, ValueError):
            voice_duration = 0

        if request.user.id == room.user1_id:
            receiver = room.user2
        else:
            receiver = room.user1

        reply_to_message = None

        if reply_to_id:
            reply_to_message = Message.objects.filter(
                id=reply_to_id,
                room=room
            ).select_related("sender").first()

        delivered_time = None

        if is_user_online(receiver):
            delivered_time = timezone.now()

        message = Message.objects.create(
            room=room,
            sender=request.user,
            receiver=receiver,
            reply_to=reply_to_message,
            message=message_text,
            is_read=False,
            delivered_at=delivered_time
        )

        if voice_note:
            message.voice_data = voice_note.read()
            message.voice_mime_type = voice_note.content_type or "audio/webm"
            message.voice_file_name = voice_note.name
            message.voice_duration = voice_duration
            message.save()

        room.save()

        message = Message.objects.select_related(
            "sender",
            "receiver",
            "room",
            "reply_to",
            "reply_to__sender"
        ).get(id=message.id)

        data = serialize_message(message, request.user)
        data["event_type"] = "new_message"

        channel_layer = get_channel_layer()

        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "chat_message",
                    "data": data,
                }
            )

        return JsonResponse({
            "success": True,
            "message": data
        })

    except ChatRoom.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Room not found"
        }, status=404)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


    

@login_required
@require_GET
def chat_messages_api(request, room_id):
    try:
        room = ChatRoom.objects.get(id=room_id)

        if request.user.id not in [room.user1_id, room.user2_id]:
            return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

        after_id = request.GET.get("after_id", "0")

        try:
            after_id = int(after_id)
        except ValueError:
            after_id = 0

        messages_list = Message.objects.filter(
            room=room,
            id__gt=after_id
        ).exclude(
            deleted_for=request.user
        ).select_related(
            "sender",
            "receiver",
            "room",
            "reply_to",
            "reply_to__sender"
        ).order_by("created_at")

        return JsonResponse({
            "success": True,
            "messages": [serialize_message(msg, request.user) for msg in messages_list]
        })

    except ChatRoom.DoesNotExist:
        return JsonResponse({"success": False, "error": "Room not found"}, status=404)

@login_required
@require_POST
def edit_message_api(request, room_id, message_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user.id not in [room.user1_id, room.user2_id]:
        return JsonResponse({
            "success": False,
            "error": "Not allowed"
        }, status=403)

    message = get_object_or_404(Message, id=message_id, room=room)

    if message.sender != request.user:
        return JsonResponse({
            "success": False,
            "error": "You can edit only your own message."
        }, status=403)

    if message.voice_note:
        return JsonResponse({
            "success": False,
            "error": "Voice messages cannot be edited."
        }, status=400)

    if message.deleted_for_everyone:
        return JsonResponse({
            "success": False,
            "error": "Deleted message cannot be edited."
        }, status=400)

    new_message_text = request.POST.get("message", "").strip()

    if not new_message_text:
        return JsonResponse({
            "success": False,
            "error": "Message cannot be empty."
        }, status=400)

    message.message = new_message_text
    message.is_edited = True
    message.edited_at = timezone.now()
    message.save()

    message = Message.objects.select_related(
        "sender",
        "receiver",
        "room",
        "reply_to",
        "reply_to__sender"
    ).get(id=message.id)

    data = serialize_message(message, request.user)
    data["event_type"] = "message_updated"

    channel_layer = get_channel_layer()

    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.id}",
            {
                "type": "message_updated",
                "data": data,
            }
        )

    return JsonResponse({
        "success": True,
        "message": data
    })
# @login_required
# @require_POST
# def edit_message_api(request, room_id, message_id):
#     try:
#         room = ChatRoom.objects.get(id=room_id)

#         if request.user.id not in [room.user1_id, room.user2_id]:
#             return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

#         message = Message.objects.select_related(
#             "sender",
#             "receiver",
#             "room",
#             "reply_to",
#             "reply_to__sender"
#         ).get(id=message_id, room=room)

#         if message.sender_id != request.user.id:
#             return JsonResponse({"success": False, "error": "You can edit only your own message"}, status=403)

#         new_text = request.POST.get("message", "").strip()

#         if new_text == "":
#             return JsonResponse({"success": False, "error": "Empty message"}, status=400)
        
#         if message.deleted_for_everyone:
#             return JsonResponse({
#                 "success": False,
#                 "error": "Deleted message cannot be edited."
#             }, status=400)

#         message.message = new_text
#         message.is_edited = True
#         message.edited_at = timezone.now()
#         message.save()

#         data = serialize_message(message)
#         data = serialize_message(message, request.user)
#         data["event_type"] = "message_updated"

#         channel_layer = get_channel_layer()

#         if channel_layer is not None:
#             async_to_sync(channel_layer.group_send)(
#                 f"chat_{room.id}",
#                 {
#                     "type": "message_updated",
#                     "data": data,
#                 }
#             )

#         return JsonResponse({"success": True, "message": data})

#     except ChatRoom.DoesNotExist:
#         return JsonResponse({"success": False, "error": "Room not found"}, status=404)

#     except Message.DoesNotExist:
#         return JsonResponse({"success": False, "error": "Message not found"}, status=404)


@login_required
@require_POST
def heartbeat_api(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    profile.is_online = True
    profile.last_seen = timezone.now()
    profile.save()

    return JsonResponse({"success": True})


@login_required
@require_GET
def user_status_api(request, user_id):
    profile = Profile.objects.filter(user_id=user_id).first()

    is_online = False
    last_seen = None

    if profile and profile.last_seen:
        last_seen = timezone.localtime(profile.last_seen).strftime("%I:%M %p")

        if profile.last_seen >= timezone.now() - timedelta(seconds=90):
            is_online = True

    return JsonResponse({
        "success": True,
        "is_online": is_online,
        "last_seen": last_seen,
    })

@login_required
def chat_list_api(request):
    chatrooms = ChatRoom.objects.filter(
        user1=request.user
    ) | ChatRoom.objects.filter(
        user2=request.user
    )

    chatrooms = chatrooms.select_related(
        "user1",
        "user2",
        "user1__profile",
        "user2__profile"
    ).order_by("-updated_at")

    rooms_data = []

    for room in chatrooms:
        if room.user1 == request.user:
            other_user = room.user2
        else:
            other_user = room.user1

        profile, created = Profile.objects.get_or_create(user=other_user)

        last_message = room.messages.exclude(
            deleted_for=request.user
        ).order_by("-created_at").first()

        unread_count = Message.objects.filter(
            room=room,
            receiver=request.user,
            is_read=False,
            deleted_for_everyone=False
        ).exclude(
            deleted_for=request.user
        ).count()

        is_online = is_user_online(other_user)

        # if last_message:
        #     if last_message.deleted_for_everyone:
        #         last_message_text = "This message was deleted"
        #     else:
        #         # last_message_text = last_message.message
        #         last_message_text = get_last_message_preview(last_message, request.user)
        # else:
        #     last_message_text = "No messages yet"
        last_message_text = get_last_message_preview(last_message, request.user)

        profile_picture_url = ""

        if profile.profile_picture:
            profile_picture_url = profile.profile_picture.url

        rooms_data.append({
            "room_id": room.id,
            "other_user_id": other_user.id,
            "other_username": other_user.username,
            "avatar": other_user.username[:1].upper(),
            "profile_picture_url": profile_picture_url,
            "is_online": is_online,
            "last_message": last_message_text,
            "last_sender_id": last_message.sender.id if last_message else None,
            "last_time": timezone.localtime(last_message.created_at).strftime("%I:%M %p") if last_message else "",
            "unread_count": unread_count,
            "chat_url": f"/chat/{room.id}/",
            "profile_url": f"/profile/{other_user.id}/",
        })

    return JsonResponse({
        "success": True,
        "rooms": rooms_data,
    })

# @login_required
# def chat_list_api(request):
#     chatrooms = ChatRoom.objects.filter(
#         user1=request.user
#     ) | ChatRoom.objects.filter(
#         user2=request.user
#     )

#     chatrooms = chatrooms.select_related(
#         "user1",
#         "user2",
#         "user1__profile",
#         "user2__profile"
#     ).order_by("-updated_at")

#     rooms_data = []

#     for room in chatrooms:
#         if room.user1 == request.user:
#             other_user = room.user2
#         else:
#             other_user = room.user1

#         last_message = room.messages.order_by("-created_at").first()

#         unread_count = Message.objects.filter(
#             room=room,
#             receiver=request.user,
#             is_read=False
#         ).count()

#         # same logic jo chat header me use ho raha hai
#         is_online = False

#         if hasattr(other_user, "profile") and other_user.profile.last_seen:
#             if other_user.profile.last_seen >= timezone.now() - timedelta(seconds=90):
#                 is_online = True

#         rooms_data.append({
#             "room_id": room.id,
#             "other_user_id": other_user.id,
#             "other_username": other_user.username,
#             "avatar": other_user.username[:1].upper(),
#             "is_online": is_online,
#             "last_message": last_message.message if last_message else "No messages yet",
#             "last_sender_id": last_message.sender.id if last_message else None,
#             "last_time": timezone.localtime(last_message.created_at).strftime("%I:%M %p") if last_message else "",
#             "unread_count": unread_count,
#             "chat_url": f"/chat/{room.id}/",
#         })

#     return JsonResponse({
#         "success": True,
#         "rooms": rooms_data,
#     })

@login_required
def profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    profile, created = Profile.objects.get_or_create(user=profile_user)

    profile_is_online = is_user_online(profile_user)

    last_seen_text = "Not available"

    if profile.last_seen:
        last_seen_text = timezone.localtime(profile.last_seen).strftime("%d %b %Y, %I:%M %p")

    return render(request, "chat/profile.html", {
        "profile_user": profile_user,
        "profile": profile,
        "profile_is_online": profile_is_online,
        "last_seen_text": last_seen_text,
    })


@login_required
def edit_profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        bio = request.POST.get("bio", "").strip()
        profile_picture = request.FILES.get("profile_picture")

        profile.full_name = full_name
        profile.bio = bio

        if profile_picture:
            profile.profile_picture = profile_picture

        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("profile_view", user_id=request.user.id)

    return render(request, "chat/edit_profile.html", {
        "profile": profile,
    })

@login_required
@require_POST
def delete_message_api(request, room_id, message_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user.id not in [room.user1_id, room.user2_id]:
        return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

    message = get_object_or_404(Message, id=message_id, room=room)

    delete_type = request.POST.get("delete_type", "").strip()

    if delete_type == "me":
        message.deleted_for.add(request.user)

        return JsonResponse({
            "success": True,
            "delete_type": "me",
            "message_id": message.id,
        })

    if delete_type == "everyone":
        if message.sender != request.user:
            return JsonResponse({
                "success": False,
                "error": "You can delete only your own message for everyone."
            }, status=403)

        message.deleted_for_everyone = True
        message.deleted_for_everyone_at = timezone.now()
        message.save()

        data = {
            "event_type": "message_deleted",
            "delete_type": "everyone",
            "message_id": message.id,
            "room_id": room.id,
            "message": "This message was deleted",
        }

        channel_layer = get_channel_layer()

        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "message_deleted",
                    "data": data,
                }
            )

        return JsonResponse({
            "success": True,
            "delete_type": "everyone",
            "message_id": message.id,
            "message": "This message was deleted",
        })

    return JsonResponse({
        "success": False,
        "error": "Invalid delete type."
    }, status=400)

@login_required
@require_POST
def mark_seen_api(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user.id not in [room.user1_id, room.user2_id]:
        return JsonResponse({"success": False, "error": "Not allowed"}, status=403)

    now_time = timezone.now()

    messages_to_update = Message.objects.filter(
        room=room,
        receiver=request.user,
        seen_at__isnull=True,
        deleted_for_everyone=False
    ).exclude(
        deleted_for=request.user
    )

    message_ids = list(messages_to_update.values_list("id", flat=True))

    messages_to_update.update(
        is_read=True,
        delivered_at=now_time,
        seen_at=now_time
    )

    if message_ids:
        channel_layer = get_channel_layer()

        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "message_status_updated",
                    "data": {
                        "event_type": "message_status_updated",
                        "message_ids": message_ids,
                        "status_text": "Seen",
                    }
                }
            )

    return JsonResponse({
        "success": True,
        "message_ids": message_ids,
        "status_text": "Seen",
    })

# @staff_member_required
# def admin_dashboard_view(request):
#     now_time = timezone.now()
#     online_limit = now_time - timedelta(seconds=90)

#     total_users = User.objects.count()
#     total_profiles = Profile.objects.count()
#     total_chats = ChatRoom.objects.count()
#     total_messages = Message.objects.count()

#     voice_messages_query = Message.objects.filter(
#         voice_note__isnull=False
#     ).exclude(
#         voice_note=""
#     )

#     total_voice_messages = voice_messages_query.count()
#     active_users = Profile.objects.filter(last_seen__gte=online_limit).count()

#     profiles = Profile.objects.select_related("user").order_by("-created_at")[:12]

#     recent_voice_messages = voice_messages_query.select_related(
#         "sender",
#         "receiver",
#         "room"
#     ).order_by("-created_at")[:10]

#     recent_chats = ChatRoom.objects.select_related(
#         "user1",
#         "user2"
#     ).annotate(
#         message_count=Count("messages")
#     ).order_by("-updated_at")[:10]

#     recent_messages = Message.objects.select_related(
#         "sender",
#         "receiver",
#         "room"
#     ).order_by("-created_at")[:12]

#     return render(request, "chat/admin_dashboard.html", {
#         "total_users": total_users,
#         "total_profiles": total_profiles,
#         "total_chats": total_chats,
#         "total_messages": total_messages,
#         "total_voice_messages": total_voice_messages,
#         "active_users": active_users,
#         "profiles": profiles,
#         "recent_voice_messages": recent_voice_messages,
#         "recent_chats": recent_chats,
#         "recent_messages": recent_messages,
#     })


@staff_member_required
def admin_dashboard_view(request):
    now_time = timezone.now()
    today_start = timezone.localtime(now_time).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    online_limit = now_time - timedelta(seconds=90)

    voice_messages_query = Message.objects.filter(
    voice_data__isnull=False
    )

    total_users = User.objects.count()
    total_staff_users = User.objects.filter(is_staff=True).count()
    total_profiles = Profile.objects.count()
    total_chats = ChatRoom.objects.count()
    total_messages = Message.objects.count()
    total_voice_messages = voice_messages_query.count()

    active_users = Profile.objects.filter(
        last_seen__gte=online_limit
    ).count()

    today_new_users = User.objects.filter(
        date_joined__gte=today_start
    ).count()

    today_messages = Message.objects.filter(
        created_at__gte=today_start
    ).count()

    today_voice_messages = voice_messages_query.filter(
        created_at__gte=today_start
    ).count()

    edited_messages = Message.objects.filter(
        is_edited=True
    ).count()

    deleted_for_everyone_messages = Message.objects.filter(
        deleted_for_everyone=True
    ).count()

    profiles_with_photo = Profile.objects.filter(
        profile_picture__isnull=False
    ).exclude(
        profile_picture=""
    ).count()

    profiles_with_bio = Profile.objects.exclude(
        bio=""
    ).count()

    profiles = Profile.objects.select_related(
        "user"
    ).order_by("-created_at")[:12]

    online_profiles = Profile.objects.filter(
        last_seen__gte=online_limit
    ).select_related(
        "user"
    ).order_by("-last_seen")[:10]

    recent_voice_messages = voice_messages_query.select_related(
        "sender",
        "receiver",
        "room"
    ).order_by("-created_at")[:10]

    recent_chats = ChatRoom.objects.select_related(
        "user1",
        "user2"
    ).annotate(
        message_count=Count("messages")
    ).order_by("-updated_at")[:10]

    top_chat_rooms = ChatRoom.objects.select_related(
        "user1",
        "user2"
    ).annotate(
        message_count=Count("messages")
    ).order_by("-message_count")[:8]

    top_active_users = User.objects.annotate(
        sent_count=Count("sent_messages"),
        received_count=Count("received_messages")
    ).order_by("-sent_count")[:8]

    recent_messages = Message.objects.select_related(
        "sender",
        "receiver",
        "room"
    ).order_by("-created_at")[:12]

    return render(request, "chat/admin_dashboard.html", {
        "total_users": total_users,
        "total_staff_users": total_staff_users,
        "total_profiles": total_profiles,
        "total_chats": total_chats,
        "total_messages": total_messages,
        "total_voice_messages": total_voice_messages,
        "active_users": active_users,
        "today_new_users": today_new_users,
        "today_messages": today_messages,
        "today_voice_messages": today_voice_messages,
        "edited_messages": edited_messages,
        "deleted_for_everyone_messages": deleted_for_everyone_messages,
        "profiles_with_photo": profiles_with_photo,
        "profiles_with_bio": profiles_with_bio,
        "profiles": profiles,
        "online_profiles": online_profiles,
        "recent_voice_messages": recent_voice_messages,
        "recent_chats": recent_chats,
        "top_chat_rooms": top_chat_rooms,
        "top_active_users": top_active_users,
        "recent_messages": recent_messages,
    })

@login_required
@require_POST
def clear_chat_api(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user.id not in [room.user1_id, room.user2_id]:
        return JsonResponse({
            "success": False,
            "error": "Not allowed"
        }, status=403)

    messages_to_clear = Message.objects.filter(
        room=room
    ).exclude(
        deleted_for=request.user
    )

    cleared_count = messages_to_clear.count()

    for msg in messages_to_clear.iterator():
        msg.deleted_for.add(request.user)

    return JsonResponse({
        "success": True,
        "cleared_count": cleared_count
    })

@login_required
def account_settings_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()

        if form_type == "profile":
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            full_name = request.POST.get("full_name", "").strip()
            bio = request.POST.get("bio", "").strip()
            profile_picture = request.FILES.get("profile_picture")

            if not username:
                messages.error(request, "Username is required.")
                return redirect("account_settings")

            username_exists = User.objects.filter(
                username=username
            ).exclude(
                id=request.user.id
            ).exists()

            if username_exists:
                messages.error(request, "This username is already taken.")
                return redirect("account_settings")

            request.user.username = username
            request.user.email = email
            request.user.save()

            profile.full_name = full_name
            profile.bio = bio

            if profile_picture:
                profile.profile_picture = profile_picture

            profile.save()

            messages.success(request, "Account details updated successfully.")
            return redirect("account_settings")

        if form_type == "password":
            password_form = PasswordChangeForm(request.user, request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)

                messages.success(request, "Password changed successfully.")
                return redirect("account_settings")

            messages.error(request, "Please fix the password errors below.")

    return render(request, "chat/account_settings.html", {
        "profile": profile,
        "password_form": password_form,
    })

@login_required
def voice_message_view(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    if request.user.id not in [message.sender_id, message.receiver_id]:
        return HttpResponse("Not allowed", status=403)

    if message.deleted_for_everyone:
        return HttpResponse("Voice message deleted", status=404)

    if request.user in message.deleted_for.all():
        return HttpResponse("Voice message deleted for you", status=404)

    if message.voice_data:
        response = HttpResponse(
            bytes(message.voice_data),
            content_type=message.voice_mime_type or "audio/webm"
        )

        response["Content-Disposition"] = f'inline; filename="{message.voice_file_name or "voice.webm"}"'
        return response

    if message.voice_note and message.voice_note.name:
        try:
            return HttpResponse(
                message.voice_note.read(),
                content_type="audio/webm"
            )
        except ValueError:
            return HttpResponse("Voice file not found", status=404)

    return HttpResponse("Voice not found", status=404)
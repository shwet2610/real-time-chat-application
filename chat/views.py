from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import ChatRoom, Message



def prepare_chatrooms(chatrooms, current_user):
    """
    Har chatroom ke saath extra data attach karega:
    - other_user
    - last_message
    - unread_count

    Important:
    Unread count sirf current_user ke received unread messages ka hoga.
    """
    for room in chatrooms:
        if room.user1_id == current_user.id:
            room.other_user = room.user2
        else:
            room.other_user = room.user1

        room.last_message = Message.objects.filter(
            room=room
        ).select_related("sender", "receiver").order_by("-created_at").first()

        room.unread_count = Message.objects.filter(
            room=room,
            receiver_id=current_user.id,
            is_read=False
        ).exclude(
            sender_id=current_user.id
        ).count()

    return chatrooms

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

    if request.user != room.user1 and request.user != room.user2:
        messages.error(request, "You are not allowed to access this chat.")
        return redirect("home")

    if request.user == room.user1:
        other_user = room.user2
    else:
        other_user = room.user1

    # Chat open hote hi received unread messages read ho jayenge
    Message.objects.filter(
    room=room,
    receiver_id=request.user.id,
    is_read=False
     ).exclude(
    sender_id=request.user.id
     ).update(is_read=True)

    # Normal POST fallback. Agar JavaScript disable ho, tab bhi message save hoga.
    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()

        if message_text:
            Message.objects.create(
                room=room,
                sender=request.user,
                receiver=other_user,
                message=message_text
            )

            room.save()
            return redirect("chat_room", room_id=room.id)

    messages_list = Message.objects.filter(
        room=room
    ).select_related("sender", "receiver").order_by("created_at")

    chatrooms = ChatRoom.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related("user1", "user2").order_by("-updated_at")

    chatrooms = prepare_chatrooms(chatrooms, request.user)

    return render(request, "chat/chat_room.html", {
        "room": room,
        "other_user": other_user,
        "messages_list": messages_list,
        "chatrooms": chatrooms
    })












# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.models import User
# from django.contrib.auth import authenticate, login, logout
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.db.models import Q

# from .models import ChatRoom, Message


# def register_view(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         email = request.POST.get("email")
#         password = request.POST.get("password")
#         confirm_password = request.POST.get("confirm_password")

#         if password != confirm_password:
#             messages.error(request, "Passwords do not match.")
#             return redirect("register")

#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Username already exists.")
#             return redirect("register")

#         if User.objects.filter(email=email).exists():
#             messages.error(request, "Email already exists.")
#             return redirect("register")

#         User.objects.create_user(
#             username=username,
#             email=email,
#             password=password
#         )

#         messages.success(request, "Account created successfully. Please login.")
#         return redirect("login")

#     return render(request, "chat/register.html")


# def login_view(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         password = request.POST.get("password")

#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             login(request, user)
#             return redirect("home")

#         messages.error(request, "Invalid username or password.")
#         return redirect("login")

#     return render(request, "chat/login.html")


# def logout_view(request):
#     logout(request)
#     return redirect("login")


# @login_required
# def home_view(request):
#     chatrooms = ChatRoom.objects.filter(
#         Q(user1=request.user) | Q(user2=request.user)
#     ).order_by("-updated_at")

#     return render(request, "chat/home.html", {
#         "chatrooms": chatrooms
#     })


# @login_required
# def users_view(request):
#     search_query = request.GET.get("q", "").strip()
#     users = User.objects.none()

#     if search_query:
#         users = User.objects.exclude(id=request.user.id).filter(
#             Q(username__icontains=search_query) |
#             Q(email__icontains=search_query)
#         )

#     return render(request, "chat/users.html", {
#         "users": users,
#         "search_query": search_query
#     })


# @login_required
# def start_chat_view(request, user_id):
#     other_user = get_object_or_404(User, id=user_id)

#     if other_user == request.user:
#         messages.error(request, "You cannot chat with yourself.")
#         return redirect("users")

#     # Important:
#     # Room hamesha same order me banega, taaki duplicate room na bane.
#     if request.user.id < other_user.id:
#         user1 = request.user
#         user2 = other_user
#     else:
#         user1 = other_user
#         user2 = request.user

#     room, created = ChatRoom.objects.get_or_create(
#         user1=user1,
#         user2=user2
#     )

#     return redirect("chat_room", room_id=room.id)


# @login_required
# def chat_room_view(request, room_id):
#     room = get_object_or_404(ChatRoom, id=room_id)

#     # Security check:
#     # Sirf wahi user chat room open kar sakta hai jo is room ka part hai.
#     if request.user != room.user1 and request.user != room.user2:
#         messages.error(request, "You are not allowed to access this chat.")
#         return redirect("home")

#     if request.user == room.user1:
#         other_user = room.user2
#     else:
#         other_user = room.user1

#     # Jab user chat open kare, uske received unread messages read ho jayenge.
#     Message.objects.filter(
#         room=room,
#         receiver=request.user,
#         is_read=False
#     ).update(is_read=True)

#     if request.method == "POST":
#         message_text = request.POST.get("message")

#         if message_text:
#             Message.objects.create(
#                 room=room,
#                 sender=request.user,
#                 receiver=other_user,
#                 message=message_text
#             )

#             # updated_at update karne ke liye
#             room.save()

#             return redirect("chat_room", room_id=room.id)

#     messages_list = Message.objects.filter(room=room).order_by("created_at")

#     chatrooms = ChatRoom.objects.filter(
#         Q(user1=request.user) | Q(user2=request.user)
#     ).order_by("-updated_at")

#     return render(request, "chat/chat_room.html", {
#         "room": room,
#         "other_user": other_user,
#         "messages_list": messages_list,
#         "chatrooms": chatrooms
#     })
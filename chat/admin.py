from django.contrib import admin
from .models import Profile, ChatRoom, Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "is_online", "last_seen", "created_at")
    search_fields = ("user__username", "user__email", "full_name")


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "created_at", "updated_at")
    search_fields = ("user1__username", "user2__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "receiver", "message", "is_read", "created_at")
    search_fields = ("sender__username", "receiver__username", "message")
    list_filter = ("is_read", "created_at")
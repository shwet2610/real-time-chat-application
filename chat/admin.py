# from django.contrib import admin
# from .models import Profile, ChatRoom, Message


# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ("user", "full_name", "is_online", "last_seen", "created_at")
#     search_fields = ("user__username", "user__email", "full_name")
#     list_filter = ("is_online", "created_at")


# class MessageInline(admin.TabularInline):
#     model = Message
#     extra = 0
#     can_delete = False

#     fields = ("sender", "receiver", "message", "is_read", "created_at")
#     readonly_fields = ("sender", "receiver", "message", "is_read", "created_at")

#     ordering = ("created_at",)

#     def has_add_permission(self, request, obj=None):
#         return False


# @admin.register(ChatRoom)
# class ChatRoomAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "chat_between",
#         "total_messages",
#         "last_message",
#         "created_at",
#         "updated_at",
#     )

#     search_fields = (
#         "user1__username",
#         "user2__username",
#         "messages__message",
#     )

#     list_filter = (
#         "created_at",
#         "updated_at",
#     )

#     ordering = ("-updated_at",)

#     inlines = [MessageInline]

#     def chat_between(self, obj):
#         return f"{obj.user1.username} ↔ {obj.user2.username}"

#     chat_between.short_description = "Chat Between"

#     def total_messages(self, obj):
#         return obj.messages.count()

#     total_messages.short_description = "Total Messages"

#     def last_message(self, obj):
#         last_msg = obj.messages.order_by("-created_at").first()
#         if last_msg:
#             return f"{last_msg.sender.username}: {last_msg.message[:60]}"
#         return "No messages"

#     last_message.short_description = "Last Message"


# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "room",
#         "sender",
#         "receiver",
#         "short_message",
#         "is_read",
#         "created_at",
#     )

#     search_fields = (
#         "message",
#         "sender__username",
#         "receiver__username",
#         "room__user1__username",
#         "room__user2__username",
#     )

#     list_filter = (
#         "sender",
#         "receiver",
#         "is_read",
#         "created_at",
#     )

#     ordering = ("-created_at",)

#     def short_message(self, obj):
#         return obj.message[:80]

#     short_message.short_description = "Message"



from django.contrib import admin
from .models import Profile, ChatRoom, Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "is_online", "last_seen", "created_at")
    search_fields = ("user__username", "user__email", "full_name")
    list_filter = ("is_online", "created_at")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False

    fields = ("sender", "receiver", "message", "is_read", "created_at")
    readonly_fields = ("sender", "receiver", "message", "is_read", "created_at")

    ordering = ("created_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "chat_between",
        "total_messages",
        "last_message",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user1__username",
        "user2__username",
        "messages__message",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    ordering = ("-updated_at",)

    inlines = [MessageInline]

    def chat_between(self, obj):
        return f"{obj.user1.username} ↔ {obj.user2.username}"

    chat_between.short_description = "Chat Between"

    def total_messages(self, obj):
        return obj.messages.count()

    total_messages.short_description = "Total Messages"

    def last_message(self, obj):
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return f"{last_msg.sender.username}: {last_msg.message[:60]}"
        return "No messages"

    last_message.short_description = "Last Message"
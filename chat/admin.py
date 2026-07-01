# # from django.contrib import admin
# # from .models import Profile, ChatRoom, Message


# # @admin.register(Profile)
# # class ProfileAdmin(admin.ModelAdmin):
# #     list_display = ("user", "full_name", "is_online", "last_seen", "created_at")
# #     search_fields = ("user__username", "user__email", "full_name")
# #     list_filter = ("is_online", "created_at")


# # class MessageInline(admin.TabularInline):
# #     model = Message
# #     extra = 0
# #     can_delete = False

# #     fields = ("sender", "receiver", "message", "is_read", "created_at")
# #     readonly_fields = ("sender", "receiver", "message", "is_read", "created_at")

# #     ordering = ("created_at",)

# #     def has_add_permission(self, request, obj=None):
# #         return False


# # @admin.register(ChatRoom)
# # class ChatRoomAdmin(admin.ModelAdmin):
# #     list_display = (
# #         "id",
# #         "chat_between",
# #         "total_messages",
# #         "last_message",
# #         "created_at",
# #         "updated_at",
# #     )

# #     search_fields = (
# #         "user1__username",
# #         "user2__username",
# #         "messages__message",
# #     )

# #     list_filter = (
# #         "created_at",
# #         "updated_at",
# #     )

# #     ordering = ("-updated_at",)

# #     inlines = [MessageInline]

# #     def chat_between(self, obj):
# #         return f"{obj.user1.username} ↔ {obj.user2.username}"

# #     chat_between.short_description = "Chat Between"

# #     def total_messages(self, obj):
# #         return obj.messages.count()

# #     total_messages.short_description = "Total Messages"

# #     def last_message(self, obj):
# #         last_msg = obj.messages.order_by("-created_at").first()
# #         if last_msg:
# #             return f"{last_msg.sender.username}: {last_msg.message[:60]}"
# #         return "No messages"

# #     last_message.short_description = "Last Message"


# # @admin.register(Message)
# # class MessageAdmin(admin.ModelAdmin):
# #     list_display = (
# #         "id",
# #         "room",
# #         "sender",
# #         "receiver",
# #         "short_message",
# #         "is_read",
# #         "created_at",
# #     )

# #     search_fields = (
# #         "message",
# #         "sender__username",
# #         "receiver__username",
# #         "room__user1__username",
# #         "room__user2__username",
# #     )

# #     list_filter = (
# #         "sender",
# #         "receiver",
# #         "is_read",
# #         "created_at",
# #     )

# #     ordering = ("-created_at",)

# #     def short_message(self, obj):
# #         return obj.message[:80]

# #     short_message.short_description = "Message"



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

from django.contrib import admin
from django.utils.html import format_html

from .models import Profile, ChatRoom, Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "short_bio",
        "profile_picture_preview",
        "is_online",
        "last_seen",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "full_name",
        "bio",
    )

    list_filter = (
        "is_online",
        "created_at",
        "last_seen",
    )

    readonly_fields = (
        "profile_picture_preview",
        "created_at",
    )

    def short_bio(self, obj):
        if obj.bio:
            return obj.bio[:60]
        return "No bio"

    short_bio.short_description = "Bio"

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;" />',
                obj.profile_picture.url
            )

        return "No photo"

    profile_picture_preview.short_description = "Profile Photo"


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False

    fields = (
        "sender",
        "receiver",
        "message",
        "voice_preview",
        "voice_duration",
        "is_read",
        "delivered_at",
        "seen_at",
        "created_at",
    )

    readonly_fields = (
        "sender",
        "receiver",
        "message",
        "voice_preview",
        "is_read",
        "delivered_at",
        "seen_at",
        "created_at",
    )

    ordering = ("created_at",)

    def has_add_permission(self, request, obj=None):
        return False

    def voice_preview(self, obj):
        if obj.voice_data:
            return format_html(
            '<audio controls style="width:180px;"><source src="/voice/{}/"></audio>',
            obj.id
        )

        if obj.voice_note and obj.voice_note.name:
            return format_html(
            '<audio controls style="width:180px;"><source src="{}"></audio>',
            obj.voice_note.url
        )

        return "-"

    voice_preview.short_description = "Voice Note"


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
        "messages__media_name",
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

        if not last_msg:
            return "No messages"

        if last_msg.deleted_for_everyone:
            return "This message was deleted"

        if last_msg.message:
            return f"{last_msg.sender.username}: {last_msg.message[:60]}"
        
        if last_msg.voice_note:
            return f"{last_msg.sender.username}: Voice message"

        # if last_msg.media_file:
        #     return f"{last_msg.sender.username}: {last_msg.media_name}"

        return "No messages"

    last_message.short_description = "Last Message"
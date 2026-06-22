import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import Profile


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get("event_type")

        if event_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_indicator",
                    "data": {
                        "event_type": "typing",
                        "user_id": self.user.id,
                        "username": self.user.username,
                        "is_typing": data.get("is_typing", False),
                    }
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def message_updated(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def message_status_updated(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class UserActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"

        await self.update_online_status()

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user") and self.user.is_authenticated:
            await self.update_last_seen()

            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    @database_sync_to_async
    def update_online_status(self):
        profile, created = Profile.objects.get_or_create(user=self.user)
        profile.is_online = True
        profile.last_seen = timezone.now()
        profile.save()

    @database_sync_to_async
    def update_last_seen(self):
        profile, created = Profile.objects.get_or_create(user=self.user)
        profile.last_seen = timezone.now()
        profile.save()


# import json

# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.contrib.auth.models import User
# from django.utils import timezone

# from .models import ChatRoom, Message, Profile


# class UserActivityConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope["user"]

#         if self.user.is_anonymous:
#             await self.close()
#             return

#         self.user_group_name = f"user_{self.user.id}"

#         await self.channel_layer.group_add(
#             self.user_group_name,
#             self.channel_name
#         )

#         await self.accept()

#         # await self.set_online_status(True)
#         await self.update_last_seen()

#     @database_sync_to_async
#     def update_last_seen(self):
#         profile, created = Profile.objects.get_or_create(user=self.user)
#         profile.last_seen = timezone.now()
#         profile.save()

#     async def message_updated(self, event):
#         await self.send(text_data=json.dumps(event["data"]))

#     async def disconnect(self, close_code):
#         if hasattr(self, "user") and self.user.is_authenticated:
#             await self.set_online_status(False)

#             await self.channel_layer.group_discard(
#                 self.user_group_name,
#                 self.channel_name
#             )

#     async def receive(self, text_data):
#         pass

#     async def chat_notification(self, event):
#         await self.send(text_data=json.dumps(event["data"]))

#     @database_sync_to_async
#     def set_online_status(self, status):
#         profile, created = Profile.objects.get_or_create(user=self.user)
#         profile.is_online = status
#         profile.last_seen = timezone.now()
#         profile.save()


# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope["user"]
#         self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
#         self.room_group_name = f"chat_{self.room_id}"

#         if self.user.is_anonymous:
#             await self.close()
#             return

#         allowed = await self.user_can_access_room()

#         if not allowed:
#             await self.close()
#             return

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         if hasattr(self, "room_group_name"):
#             await self.channel_layer.group_discard(
#                 self.room_group_name,
#                 self.channel_name
#             )

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#         except json.JSONDecodeError:
#             return

#         message_text = data.get("message", "").strip()

#         if message_text == "":
#             return

#         saved_message = await self.save_message(message_text)

#         if not saved_message:
#             return

#         # Same chat room me sender + receiver dono ko message bhejo
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "data": saved_message,
#             }
#         )

#         # Receiver agar home/sidebar par hai to notification ke liye
#         await self.channel_layer.group_send(
#             f"user_{saved_message['receiver_id']}",
#             {
#                 "type": "chat_notification",
#                 "data": saved_message,
#             }
#         )

#     async def chat_message(self, event):
#         await self.send(text_data=json.dumps(event["data"]))

#     @database_sync_to_async
#     def user_can_access_room(self):
#         try:
#             room = ChatRoom.objects.get(id=self.room_id)
#             return self.user.id == room.user1_id or self.user.id == room.user2_id
#         except ChatRoom.DoesNotExist:
#             return False

#     @database_sync_to_async
#     def save_message(self, message_text):
#         try:
#             room = ChatRoom.objects.select_related("user1", "user2").get(id=self.room_id)
#             sender = User.objects.get(id=self.user.id)

#             if sender.id == room.user1_id:
#                 receiver = room.user2
#             elif sender.id == room.user2_id:
#                 receiver = room.user1
#             else:
#                 return None

#             message = Message.objects.create(
#                 room=room,
#                 sender=sender,
#                 receiver=receiver,
#                 message=message_text,
#                 is_read=False
#             )

#             # Chat room ka updated_at update karne ke liye
#             room.save()

#             receiver_unread_count = Message.objects.filter(
#                 room=room,
#                 receiver=receiver,
#                 is_read=False
#             ).exclude(sender=receiver).count()

#             local_time = timezone.localtime(message.created_at)

#             return {
#                 "room_id": room.id,
#                 "message_id": message.id,
#                 "message": message.message,
#                 "sender_id": sender.id,
#                 "receiver_id": receiver.id,
#                 "sender_username": sender.username,
#                 "receiver_username": receiver.username,
#                 "created_at": local_time.strftime("%I:%M %p"),
#                 "receiver_unread_count": receiver_unread_count,
#             }

#         except Exception as e:
#             print("Message save error:", e)
#             return None
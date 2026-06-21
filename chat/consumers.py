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

#         await self.channel_layer.group_add(
#             "online_status",
#             self.channel_name
#         )

#         await self.set_user_online(self.user.id)

#         await self.channel_layer.group_send(
#             "online_status",
#             {
#                 "type": "status_update",
#                 "user_id": self.user.id,
#                 "is_online": True,
#             }
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         if not self.user.is_anonymous:
#             await self.set_user_offline(self.user.id)

#             await self.channel_layer.group_send(
#                 "online_status",
#                 {
#                     "type": "status_update",
#                     "user_id": self.user.id,
#                     "is_online": False,
#                 }
#             )

#             await self.channel_layer.group_discard(
#                 self.user_group_name,
#                 self.channel_name
#             )

#             await self.channel_layer.group_discard(
#                 "online_status",
#                 self.channel_name
#             )

#     async def status_update(self, event):
#         await self.send(text_data=json.dumps({
#             "kind": "status_update",
#             "user_id": event["user_id"],
#             "is_online": event["is_online"],
#         }))

#     async def chat_notification(self, event):
#         await self.send(text_data=json.dumps({
#             "kind": "chat_notification",
#             "room_id": event["room_id"],
#             "message": event["message"],
#             "sender_id": event["sender_id"],
#             "receiver_id": event["receiver_id"],
#             "sender_username": event["sender_username"],
#             "created_at": event["created_at"],
#             "unread_count": event["unread_count"],
#         }))

#     @database_sync_to_async
#     def set_user_online(self, user_id):
#         Profile.objects.update_or_create(
#             user_id=user_id,
#             defaults={
#                 "is_online": True,
#                 "last_seen": timezone.now()
#             }
#         )

#     @database_sync_to_async
#     def set_user_offline(self, user_id):
#         Profile.objects.update_or_create(
#             user_id=user_id,
#             defaults={
#                 "is_online": False,
#                 "last_seen": timezone.now()
#             }
#         )


# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
#         self.room_group_name = f"chat_{self.room_id}"
#         self.user = self.scope["user"]

#         if self.user.is_anonymous:
#             await self.close()
#             return

#         is_allowed = await self.check_user_in_room(self.room_id, self.user.id)

#         if not is_allowed:
#             await self.close()
#             return

#         await self.mark_room_messages_read(self.room_id, self.user.id)

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         message_text = data.get("message", "").strip()

#         if not message_text:
#             return

#         message_data = await self.save_message(
#             self.room_id,
#             self.user.id,
#             message_text
#         )

#         # Chat room me live message show karne ke liye
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "message_id": message_data["message_id"],
#                 "message": message_data["message"],
#                 "sender_id": message_data["sender_id"],
#                 "receiver_id": message_data["receiver_id"],
#                 "sender_username": message_data["sender_username"],
#                 "created_at": message_data["created_at"],
#             }
#         )

#         # Receiver ke home/sidebar ko live update karne ke liye
#         await self.channel_layer.group_send(
#             f"user_{message_data['receiver_id']}",
#             {
#                 "type": "chat_notification",
#                 "room_id": message_data["room_id"],
#                 "message": message_data["message"],
#                 "sender_id": message_data["sender_id"],
#                 "receiver_id": message_data["receiver_id"],
#                 "sender_username": message_data["sender_username"],
#                 "created_at": message_data["created_at"],
#                 "unread_count": message_data["receiver_unread_count"],
#             }
#         )

#         # Sender side preview update karne ke liye
#         await self.channel_layer.group_send(
#             f"user_{message_data['sender_id']}",
#             {
#                 "type": "chat_notification",
#                 "room_id": message_data["room_id"],
#                 "message": message_data["message"],
#                 "sender_id": message_data["sender_id"],
#                 "receiver_id": message_data["receiver_id"],
#                 "sender_username": message_data["sender_username"],
#                 "created_at": message_data["created_at"],
#                 "unread_count": 0,
#             }
#         )

#     async def chat_message(self, event):
#         if int(event["receiver_id"]) == int(self.user.id):
#             await self.mark_single_message_read(
#                 event["message_id"],
#                 self.user.id
#             )

#         await self.send(text_data=json.dumps({
#             "message_id": event["message_id"],
#             "message": event["message"],
#             "sender_id": event["sender_id"],
#             "receiver_id": event["receiver_id"],
#             "sender_username": event["sender_username"],
#             "created_at": event["created_at"],
#         }))

#     @database_sync_to_async
#     def check_user_in_room(self, room_id, user_id):
#         return ChatRoom.objects.filter(
#             id=room_id,
#             user1_id=user_id
#         ).exists() or ChatRoom.objects.filter(
#             id=room_id,
#             user2_id=user_id
#         ).exists()

#     @database_sync_to_async
#     def mark_room_messages_read(self, room_id, user_id):
#         Message.objects.filter(
#             room_id=room_id,
#             receiver_id=user_id,
#             is_read=False
#         ).exclude(
#             sender_id=user_id
#         ).update(is_read=True)

#     @database_sync_to_async
#     def mark_single_message_read(self, message_id, user_id):
#         Message.objects.filter(
#             id=message_id,
#             receiver_id=user_id,
#             is_read=False
#         ).exclude(
#             sender_id=user_id
#         ).update(is_read=True)

#     @database_sync_to_async
#     def save_message(self, room_id, sender_id, message_text):
#         room = ChatRoom.objects.select_related("user1", "user2").get(id=room_id)
#         sender = User.objects.get(id=sender_id)

#         if sender.id == room.user1_id:
#             receiver = room.user2
#         else:
#             receiver = room.user1

#         message = Message.objects.create(
#             room=room,
#             sender=sender,
#             receiver=receiver,
#             message=message_text,
#             is_read=False
#         )

#         room.save()

#         receiver_unread_count = Message.objects.filter(
#             room=room,
#             receiver=receiver,
#             is_read=False
#         ).exclude(
#             sender=receiver
#         ).count()

#         local_time = timezone.localtime(message.created_at)

#         return {
#             "room_id": room.id,
#             "message_id": message.id,
#             "message": message.message,
#             "sender_id": sender.id,
#             "receiver_id": receiver.id,
#             "sender_username": sender.username,
#             "created_at": local_time.strftime("%I:%M %p"),
#             "receiver_unread_count": receiver_unread_count,
#         }



import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone

from .models import ChatRoom, Message, Profile


class UserActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        await self.set_online_status(True)

    async def disconnect(self, close_code):
        if hasattr(self, "user") and self.user.is_authenticated:
            await self.set_online_status(False)

            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        pass

    async def chat_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def set_online_status(self, status):
        profile, created = Profile.objects.get_or_create(user=self.user)
        profile.is_online = status
        profile.last_seen = timezone.now()
        profile.save()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        if self.user.is_anonymous:
            await self.close()
            return

        allowed = await self.user_can_access_room()

        if not allowed:
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
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = data.get("message", "").strip()

        if message_text == "":
            return

        saved_message = await self.save_message(message_text)

        if not saved_message:
            return

        # Same chat room me sender + receiver dono ko message bhejo
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "data": saved_message,
            }
        )

        # Receiver agar home/sidebar par hai to notification ke liye
        await self.channel_layer.group_send(
            f"user_{saved_message['receiver_id']}",
            {
                "type": "chat_notification",
                "data": saved_message,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def user_can_access_room(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return self.user.id == room.user1_id or self.user.id == room.user2_id
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message_text):
        try:
            room = ChatRoom.objects.select_related("user1", "user2").get(id=self.room_id)
            sender = User.objects.get(id=self.user.id)

            if sender.id == room.user1_id:
                receiver = room.user2
            elif sender.id == room.user2_id:
                receiver = room.user1
            else:
                return None

            message = Message.objects.create(
                room=room,
                sender=sender,
                receiver=receiver,
                message=message_text,
                is_read=False
            )

            # Chat room ka updated_at update karne ke liye
            room.save()

            receiver_unread_count = Message.objects.filter(
                room=room,
                receiver=receiver,
                is_read=False
            ).exclude(sender=receiver).count()

            local_time = timezone.localtime(message.created_at)

            return {
                "room_id": room.id,
                "message_id": message.id,
                "message": message.message,
                "sender_id": sender.id,
                "receiver_id": receiver.id,
                "sender_username": sender.username,
                "receiver_username": receiver.username,
                "created_at": local_time.strftime("%I:%M %p"),
                "receiver_unread_count": receiver_unread_count,
            }

        except Exception as e:
            print("Message save error:", e)
            return None
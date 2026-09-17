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



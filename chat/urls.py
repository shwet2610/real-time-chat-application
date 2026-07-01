from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),

    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("users/", views.users_view, name="users"),

    path("start-chat/<int:user_id>/", views.start_chat_view, name="start_chat"),
    path("chat/<int:room_id>/", views.chat_room_view, name="chat_room"),

    path("chat/<int:room_id>/send/", views.send_message_api, name="send_message_api"),
    path("chat/<int:room_id>/messages/", views.chat_messages_api, name="chat_messages_api"),
    path("api/chats/", views.chat_list_api, name="chat_list_api"),

    path("profile/<int:user_id>/", views.profile_view, name="profile_view"),
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),

    path("chat/<int:room_id>/delete/<int:message_id>/", views.delete_message_api, name="delete_message_api"),
    path("chat/<int:room_id>/mark-seen/", views.mark_seen_api, name="mark_seen_api"),
    # path("chat/<int:room_id>/send/", views.send_message_api, name="send_message_api"),
    # path("chat/<int:room_id>/messages/", views.chat_messages_api, name="chat_messages_api"),
    path("chat/<int:room_id>/edit/<int:message_id>/", views.edit_message_api, name="edit_message_api"),

    path("presence/heartbeat/", views.heartbeat_api, name="heartbeat_api"),
    path("presence/user/<int:user_id>/", views.user_status_api, name="user_status_api"),

    path("settings/", views.account_settings_view, name="account_settings"),
    path("chat/<int:room_id>/clear/", views.clear_chat_api, name="clear_chat_api"),
    path("voice/<int:message_id>/", views.voice_message_view, name="voice_message"),

    path("app-admin/dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
]
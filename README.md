# Real-Time Chat Application

A real-time private chat application built using **Python, Django, SQL Server, Django Channels, and WebSocket**.

## Project Overview

This project allows users to register, login, search other users by username or email, start private conversations, and send messages instantly without refreshing the page. All user data, chat rooms, messages, unread message status, and online/offline status are stored in SQL Server.

## Features

* User Registration and Login
* Username/Email based user search
* Private one-to-one chat rooms
* Real-time messaging using WebSocket
* Message history stored in SQL Server
* Unread message count
* Online/Offline user status
* Clean and responsive UI
* Django Admin support

## Tech Stack

* Python
* Django
* Django Channels
* WebSocket
* SQL Server
* HTML
* CSS
* JavaScript

## Database Tables

The project stores data in SQL Server using Django ORM.

Main tables:

* `auth_user` - stores user authentication data
* `chat_profile` - stores user profile, online status, and last seen
* `chat_chatroom` - stores private chat rooms between two users
* `chat_message` - stores messages, sender, receiver, read status, and timestamp

## How It Works

1. User registers or logs in.
2. User searches another user by username or email.
3. A private chat room is created between both users.
4. When a message is sent, JavaScript sends it through WebSocket.
5. Django Channels receives the message in the consumer.
6. The message is saved in SQL Server.
7. The message is sent instantly to the receiver without page refresh.

## WebSocket and Django Channels

Django normally works on the HTTP request-response cycle. For real-time communication, this project uses Django Channels and WebSocket.

WebSocket keeps a live connection open between the browser and the server. This allows messages to appear instantly without reloading the page.

Django Channels allows Django to handle WebSocket connections using ASGI.

## Project Setup

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_LINK
cd realtime_chat_app
```

### 2. Create virtual environment

```bash
python -m venv venv
```

### 3. Activate virtual environment

For Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure SQL Server database

Create a database in SQL Server:

```sql
CREATE DATABASE RealtimeChatDB;
```

Update database settings in `config/settings.py` according to your SQL Server configuration.

### 6. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create superuser

```bash
python manage.py createsuperuser
```

### 8. Run the project

```bash
python manage.py runserver
```

Open in browser:

```text
http://127.0.0.1:8000/
```

## Important Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Future Improvements

* Group chat
* Message delete option
* Typing indicator
* Profile picture upload
* Email verification
* Deployment with production database and Redis



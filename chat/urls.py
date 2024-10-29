# urls.py
from django.urls import path
from .views import StartChat, send_message

urlpatterns = [
    path('startChat/', StartChat, name='StartChat'),
    path('conversacion/', send_message, name='conversacion')
    # otras rutas...
]
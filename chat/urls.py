# urls.py
from django.urls import path
from .views import StartChat

urlpatterns = [
    path('startChat/', StartChat, name='StartChat'),
    # path('conversacion/', iniciar_chat, name='conversacion')
    # otras rutas...
]
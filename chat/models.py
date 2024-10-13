from django.db import models

# Create your models here.
class UserChat(models.Model):
    user_id = models.CharField(max_length=255, unique=True)  # ID de usuario de Telegram
    chat_id = models.CharField(max_length=255, unique=True)  # ID del chat
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación

    def __str__(self):
        return f"UserChat(user_id={self.user_id}, chat_id={self.chat_id})"
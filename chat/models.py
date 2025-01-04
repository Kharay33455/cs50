from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Chat(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user_1 = models.IntegerField()
    user_2 = models.IntegerField()


    def __str__(self):
        return f'Chat obj between users with id {self.user_1} and {self.user_2}'

class ChatUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    has_new_message = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} chat user obj'

    
class Message(models.Model):
    message = models.TextField()
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(ChatUser, on_delete =models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    media = models.ImageField(upload_to='chat/', blank=True, null=True)
    is_read = models.BooleanField(default= False)


    def __str__(self):
        return f'Message from {self.user} at {self.created} to {self.chat}'

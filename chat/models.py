from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# a single chat between 2 users
class Chat(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # storing chat user IDs and not the object themselves
    user_1 = models.IntegerField()
    user_2 = models.IntegerField()

    def __str__(self):
        return f'Chat obj between users with id {self.user_1} and {self.user_2}'

# a chat user thay can be involeved in a chat
class ChatUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # check if user has unread messages, notify them on front end UI
    has_new_message = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} chat user obj'

# a single message
class Message(models.Model):
    message = models.TextField() # the text if any.. Can be emptyh string
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE) # associated chat
    user = models.ForeignKey(ChatUser, on_delete =models.CASCADE) # message sender
    created = models.DateTimeField(auto_now_add=True) # when message was created
    updated = models.DateTimeField(auto_now=True) # last time message was updated
    media = models.ImageField(upload_to='chat/', blank=True, null=True) # media attached to message, if any
    is_read = models.BooleanField(default= False) # check if message is read


    def __str__(self):
        return f'Message from {self.user} at {self.created} to {self.chat}'

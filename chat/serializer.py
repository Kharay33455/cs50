from rest_framework import serializers
from .models import *

class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"

class CommunityMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityMessage
        fields = "__all__"
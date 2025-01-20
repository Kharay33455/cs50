import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import *
from .serializer import *
from .views import _serialize_message
import base64
from django.core.files.base import ContentFile
import random


class ChatConsumer(WebsocketConsumer):
    """
        On initial request, validate user before allowing connection to be accepted
    """
    #on intial request
    def connect(self):

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        # validate user
        
        # accept connection
        self.accept()

        # send response
        self.send(text_data=json.dumps({
            'type':'connection_established',
            'message':'You are connected'
        }))
    
    def receive(self, text_data):
        # get message
        text_data_json = json.loads(text_data)
        message = str(text_data_json['form']['message'])
        if message.strip() == "":
            message = None
        try:
            
            base64_image = text_data_json['form']['image']
            if base64_image.startswith('data:image'):
                base64_image = base64_image.split(';base64,')[1]
            img_name = random.randint(1111111111111,999999999999999)
            data = ContentFile(base64.b64decode(base64_image), name= 'image' + str(img_name) + '.jpg')
        except AttributeError:
            data = None
        # get message sender id
        user_id = int(self.scope['user'].id)
        sender = User.objects.get(id = user_id)
        # extract chat ID
        chat_id = int(self.scope['url_route']['kwargs']['room_name'])
        try:
            _chat = Chat.objects.get(id = chat_id)
        except Chat.DoesNotExist:
            self.close()
        _requesting_user = self.scope['user']
        if _chat.user_1 == _requesting_user.id or _chat.user_2 == _requesting_user.id:
            print('here')
            base = self.scope['headers']
            print(base)
            host = ''
            for _ in base:
                if _[0] == b'origin':
                    host = _[1].decode('utf-8')
                    break
            chat_user = ChatUser.objects.get(user = sender)
            if message != None or data != None:
                new_message = Message.objects.create(message = message, chat = _chat, user = chat_user, media = data)
                print(MessageSerializer(new_message).data)
                _serialized_data = _serialize_message(user = _requesting_user, base = host,  message= new_message)
                _chat.user_1_has_read = False
                _chat.user_2_has_read = False
                _chat.save()
                print(_serialized_data)
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type':'chat_message',
                        'message' : _serialized_data
                    }
                )
                print('Event broadcasted')
        
    def chat_message(self, event):
        message = event['message']
        # get user to check if message being broadcast to them was sent by them
        user = self.scope['user']
        chat_user = ChatUser.objects.get(user = user)
        if chat_user.id != message['user']:
            message['from'] = True
        else:
            message['from'] = False
        print(message)
        chat = Chat.objects.get(id =  int(message['chat']))
        if user.id == chat.user_1:
            chat.user_1_has_read = True
        if user.id == chat.user_2:
            chat.user_2_has_read = True
        chat.save()
        self.send(json.dumps({
            'type':'new_message',
            'message' : message
        }))
# major imports
import json # to load and sump json
from channels.generic.websocket import WebsocketConsumer # web consumer object to inherit classes from
from asgiref.sync import async_to_sync # make asynt 
# customs
from .models import *
from .serializer import *
from .views import _serialize_message
# to decode mesia
import base64
# create content type
from django.core.files.base import ContentFile
# random module to generate names at random
import random

# chat consummer for web socket
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

        # accept connection
        self.accept()

        # send response
        self.send(text_data=json.dumps({
            'type':'connection_established',
            'message':'You are connected'
        }))
    
    def receive(self, text_data):
        # get data sent from front end
        text_data_json = json.loads(text_data)
        # message 
        message = str(text_data_json['form']['message'])
        if message.strip() == "":
            message = None
        # try to decode image or set to none if not available
        try:
            
            base64_image = text_data_json['form']['image']
            if base64_image.startswith('data:image'):
                base64_image = base64_image.split(';base64,')[1]
            img_name = random.randint(1111111111111,999999999999999)
            data = ContentFile(base64.b64decode(base64_image), name= 'image' + str(img_name) + '.jpg')
        except AttributeError:
            data = None
        # send message
        sender = self.scope['user']
        # extract chat ID
        chat_id = int(self.scope['url_route']['kwargs']['room_name'])
        try:
            _chat = Chat.objects.get(id = chat_id)
        except Chat.DoesNotExist:
            self.close()
        _requesting_user = self.scope['user']
        # make sure user is in the conversation before attempting to create message
        if _chat.user_1 == _requesting_user.id or _chat.user_2 == _requesting_user.id:
            # get host address from header dictionary
            base = self.scope['headers']
            host = ''
            for _ in base:
                if _[0] == b'origin':
                    host = _[1].decode('utf-8')
                    break
            chat_user = ChatUser.objects.get(user = sender)
            # if message is valid, create.
            if message != None or data != None:
                new_message = Message.objects.create(message = message, chat = _chat, user = chat_user, media = data)
                print(MessageSerializer(new_message).data)
                _serialized_data = _serialize_message(user = _requesting_user, base = host,  message= new_message)
                # set up alert both users of new message
                _chat.user_1_has_read = False
                _chat.user_2_has_read = False
                _chat.save()
                # broadcast to group
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type':'chat_message',
                        'message' : _serialized_data
                    }
                )
        
    def chat_message(self, event):
        message = event['message']
        # get user to check if message being broadcast to them was sent by them
        user = self.scope['user']
        chat_user = ChatUser.objects.get(user = user)
        if chat_user.id != message['user']:
            message['from'] = True
        else:
            message['from'] = False
        # get chat to mark all users currently in connection as read
        chat = Chat.objects.get(id =  int(message['chat']))
        if user.id == chat.user_1:
            chat.user_1_has_read = True
        if user.id == chat.user_2:
            chat.user_2_has_read = True
        chat.save()
        # send response
        self.send(json.dumps({
            'type':'new_message',
            'message' : message
        }))
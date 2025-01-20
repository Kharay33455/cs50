import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import *
from .serializer import *
from .views import _serialize_message

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
        message = text_data_json['message']
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
            base = str(self.scope['headers'][1][1]) 
            base = base[2:-1]
            print(base)
            chat_user = ChatUser.objects.get(user = sender)
            new_message = Message.objects.create(message = message, chat = _chat, user = chat_user)
            _serialized_data = _serialize_message(user = _requesting_user, base = base,  message= new_message)

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
        self.send(json.dumps({
            'type':'new_message',
            'message' : message
        }))
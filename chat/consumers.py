# major imports
import json # to load and sump json
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer # web consumer object to inherit classes from
from asgiref.sync import async_to_sync, sync_to_async # make asynt 
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
#import channel layer
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from django.db.models import Q

# chat consummer for web socket
class ChatConsumer(AsyncWebsocketConsumer):
    """
        On initial request, validate user before allowing connection to be accepted
    """
    #on intial request
    async def connect(self):

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # accept connection
        await self.accept()
        unread = sync_to_async(get_msg_count)(self.scope['user'])
        # send response
        await self.send(text_data=json.dumps({
            'type':'connection_established',
            'message':'You are connected',
            'unread':unread
        }))

    
    async def receive(self, text_data):
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

            _chat = await database_sync_to_async(Chat.objects.get)(id = chat_id)
        
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
            chat_user = await database_sync_to_async(ChatUser.objects.get)(user = sender)
            # if message is valid, create.
            if message != None or data != None:
                new_message = await database_sync_to_async(Message.objects.create)(message = message, chat = _chat, user = chat_user, media = data)
                
                # boradcast chat id to chat list consumer of other user after creation
                
                #get receiver id
                if sender.id == _chat.user_1:
                    receiver_id = int(_chat.user_2)
                else:
                    receiver_id = int(_chat.user_1)
                receiver = f'user_{sender.id}'
                
                # sene message to that user consumer

                
                await self.channel_layer.group_send(
                    f"user_{receiver_id}",
                    {
                        'type':'new_message_signal',
                        'chat_id' : _chat.id
                    }
                )
                
                _serialized_data = await database_sync_to_async(_serialize_message)(user = _requesting_user, base = host,  message= new_message)
                # set up alert both users of new message
                _chat.user_1_has_read = False
                _chat.user_2_has_read = False
                await database_sync_to_async(_chat.save)()
                # broadcast to group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type':'chat_message',
                        'message' : _serialized_data
                    }
                )
        
    async def chat_message(self, event):
        message = event['message']
        # get user to check if message being broadcast to them was sent by them
        user = self.scope['user']
        chat_user = await database_sync_to_async(ChatUser.objects.get)(user = user)
        if chat_user.id != message['user']:
            message['from'] = True
        else:
            message['from'] = False
        # get chat to mark all users currently in connection as read
        chat = await database_sync_to_async(Chat.objects.get)(id =  int(message['chat']))
        if user.id == chat.user_1:
            chat.user_1_has_read = True
        if user.id == chat.user_2:
            chat.user_2_has_read = True
        await database_sync_to_async(chat.save)()
        # send response
        await self.send(json.dumps({
            'type':'new_message',
            'message' : message
        }))


class ChatListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        self.room_group_name = f"user_{user.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(self.room_group_name)
        # get chat user object
        unread = await sync_to_async(get_msg_count)(user)
        await self.send(text_data=json.dumps({
            'type' : 'msg_count',
            'count' : unread
        }))
        # get

        await self.send(text_data=json.dumps({
            'type' : 'connected',
            'message':'You have been connected'
        }))


    async def receive(self, text_data, event):

        print(event)
        data =  json.loads(text_data)
        print(data)

        
    async def new_message_signal(self, event):
        print(self.room_group_name)
        unread = await sync_to_async(get_msg_count)(self.scope['user'])
        event['unread'] = unread
        print(unread)
        await self.send(text_data=json.dumps(event))

def get_msg_count(user_obj):
    _chat_user, created = ChatUser.objects.get_or_create(user = user_obj) # get chat user
    chats = Chat.objects.filter(Q(user_1 = _chat_user.id) | Q(user_2 = _chat_user.id))
    unread = 0
    for c in chats:
        if c.user_1 == _chat_user.id and not c.user_1_has_read:
            unread+=1
        if c.user_2 == _chat_user.id and not c.user_2_has_read:
            unread +=1
    return unread
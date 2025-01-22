# major imports
import json # to load and sump json
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer # web consumer object to inherit classes from
from asgiref.sync import async_to_sync, sync_to_async # make asynt 
# customs
from .models import *
from .serializer import *
from .views import _serialize_message, process_time
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
from base.models import *


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

        # confirm user is a member of this chat
        user = self.scope['user']
        chat = await database_sync_to_async(Chat.objects.get)(id = self.room_name)
        
        if user.id == chat.user_1:
            user_id = chat.user_1
            chat.user_1_has_read = True
        elif user.id == chat.user_2:
            user_id = chat.user_2
            chat.user_2_has_read = True
        else:
            self.close()
        
        await database_sync_to_async(chat.save)()

        await self.channel_layer.group_send(
            f'user_{user_id}',
            {
                'type':'new_message_signal'
            }
        )

        
        # accept connection
        await self.accept()
        ## mark chat as read

        # send response
        await self.send(text_data=json.dumps({
            'type':'connection_established',
            'message':'You are connected',
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
                receiver = f'user_{receiver_id}'
                
                # sene message to that user consumer

                
                await self.channel_layer.group_send(
                    receiver,
                    {
                        'type':'new_message_signal',
                        'chat_id' : _chat.id
                    }
                )
                
                _serialized_data = await database_sync_to_async(_serialize_message)(user = _requesting_user, base = host,  message= new_message)
                # set up alert both users of new message
                if _requesting_user.id == _chat.user_1:
                    _chat.user_2_has_read = False
                else:
                    _chat.user_1_has_read = False
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
        print(message)
        # get user to check if message being broadcast to them was sent by them
        user = self.scope['user']
        chat_user = await database_sync_to_async(ChatUser.objects.get)(user = user)
        if chat_user.id != message['user']:
            message['from'] = True
        else:
            message['from'] = False
        # get chat to mark all users currently in connection as read
        chat = await database_sync_to_async(Chat.objects.get)(id =  int(message['chat']))
        await sync_to_async(print)(chat.user_2)
        if user.id == chat.user_1:
            print('read by user', user.id)
            user_id = user.id
            chat.user_1_has_read = True
        if user.id == chat.user_2:
            user_id = user.id
            print('read by user', user.id)
            chat.user_2_has_read = True
            
        await database_sync_to_async(chat.save)()

        await self.channel_layer.group_send(
            f'user_{user_id}',
            {
                'type':'new_message_signal'
            }
        )
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
        """Get message count"""
        # get chat user object
        _ = await sync_to_async(get_msg_count)(user)
        await self.send(text_data=json.dumps({
            'type' : 'new_message_signal',
            'unread' : _['unread'],
            'unread_ids': _['unread_ids']
        }))
        # notifications count
        notifications = await sync_to_async(Notification.objects.filter)(associated_user = user, is_seen = False)
        notif_count = await sync_to_async (len)(notifications)
        await self.send(text_data=json.dumps({
            'type': 'notif_count',
            'notif_count' : notif_count
        }))

        # get

        await self.send(text_data=json.dumps({
            'type' : 'connected',
            'message':'You have been connected'
        }))


    async def receive(self, text_data):
        user = self.scope['user']
        data =  json.loads(text_data)
        if data['message'] == 'get_notif_count':
            print('jere')
            await self.channel_layer.group_send(
                f'user_{user.id}',
                {
                    'type':data['message'],
                    'message':'get_notif_count'
                }
            )

        
    async def new_message_signal(self, event):

        print(self.room_group_name)
        _ = await sync_to_async(get_msg_count)(self.scope['user'])
        event['unread'] = _['unread']
        event['unread_ids'] = _['unread_ids']
        await self.send(text_data=json.dumps(event))

    async def get_notif_count(self, event):
        user = self.scope['user']
        # notifications count
        notifications = await sync_to_async(Notification.objects.filter)(associated_user = user, is_seen = False)
        notif_count = await sync_to_async (len)(notifications)
        await self.send(text_data=json.dumps({
            'type': 'notif_count',
            'notif_count' : notif_count
        }))
        




def get_msg_count(user_obj):
    chats = Chat.objects.filter(Q(user_1 = user_obj.id) | Q(user_2 = user_obj.id))
    unread = 0
    unread_id = []
    for c in chats:
        if c.user_1 == user_obj.id and not c.user_1_has_read:
            unread+=1
            message = Message.objects.filter(chat = c).last()
            unread_id.append({'chat_id': c.id, 'last_text':message.message, 'time': process_time(message.created)})
        if c.user_2 == user_obj.id and not c.user_2_has_read:
            unread+=1
            message = Message.objects.filter(chat = c).last()
            unread_id.append({'chat_id': c.id, 'last_text':message.message, 'time': process_time(message.created)})
    return_dict = {}
    return_dict['unread'] = unread
    return_dict['unread_ids'] = unread_id
    print(unread_id)
    return return_dict

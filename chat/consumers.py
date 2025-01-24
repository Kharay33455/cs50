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
            host = await sync_to_async(get_host)(self)
           
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
            user_id = user.id
            chat.user_1_has_read = True
        if user.id == chat.user_2:
            user_id = user.id
            chat.user_2_has_read = True
            
        await database_sync_to_async(chat.save)()

        await self.channel_layer.group_send(
            f'user_{user_id}',
            {
                'type':'new_message_signal',
                'chat_id' : int(message['chat'])
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
        
        """
            Get message count
        """
        _ = await sync_to_async(get_msg_count)(user)
        await self.send(text_data=json.dumps({
            'type' : 'new_message_signal',
            'unread' : _['unread'],
            'unread_ids': _['unread_ids']
        }))

        """
            Get notification count
        """
        notifications = await database_sync_to_async(Notification.objects.filter)(associated_user = user, is_seen = False)
        notif_count = await sync_to_async (len)(notifications)
        await self.send(text_data=json.dumps({
            'type': 'notif_count',
            'notif_count' : notif_count
        }))

        """
            Get community messages
        """
        comms = await database_sync_to_async(get_comm_messages)(user)
        await self.send(text_data=json.dumps({
            'type':'comm_signal',
            'message': comms
        }))

        await self.send(text_data=json.dumps({
            'type' : 'connected',
            'message':'You have been connected'
        }))


    async def receive(self, text_data):
        user = self.scope['user']
        data =  json.loads(text_data)
        if data['message'] == 'get_notif_count':
            await self.channel_layer.group_send(
                f'user_{user.id}',
                {
                    'type':data['message'],
                    'message':'get_notif_count'
                }
            )
        if data['message'] == 'search':
            await self.channel_layer.group_send(
                f'user_{user.id}',
                {
                    'type' : data['message'],
                    'message' : data['value']
                }
            )

        
    async def new_message_signal(self, event):

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
    async def new_comm_msg(self, event):
        await self.send(text_data=json.dumps(event))

    # search function
    async def search(self, event):
        if event['message'] == "":
            context = []
        else:
            community = await database_sync_to_async(Community.objects.filter)(name__contains = event['message'])
            context = await sync_to_async(construct_community)(community, self)
        await self.send(text_data=json.dumps({
            'type' : event['type'],
            'message' : context
        }))
    


        

"""Group chat community sockets"""
class CommunityChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # validate
        comm_id = self.scope['url_route']['kwargs']['comm_id']
        user = self.scope['user']
        if await sync_to_async(validate)(user=user, comm_id=comm_id):
            self.room_group_name = f'comm_{comm_id}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            await sync_to_async(print)('Socket now open')

    # send new community messages
    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data['text'].strip()
        image = data['image']
        if image != None:
            if image.startswith('data:image'):
                image = image.split(';base64,')[1]
            image_name = 'media' + str(random.randint(1111111111,9999999999999)) +'.jpg'
            image = ContentFile(base64.b64decode(image), image_name)
        if text == '':
            text = None
        else:
            text = data['text']
        if text != None or image != None:

            comm_id = self.scope['url_route']['kwargs']['comm_id']
            # get user
            user = self.scope['user']
            _comm = await database_sync_to_async(Community.objects.get)(id = int(comm_id))
            chat_user = await database_sync_to_async(ChatUser.objects.get)(user = user)
            new_comm_message = await database_sync_to_async(CommunityMessage.objects.create)(message = text, sender = chat_user, media = image, community = _comm )
            if image == None:
                media = None
            else:
                media = get_host(self) + '/media/' +str(new_comm_message.media)
            _person = await database_sync_to_async(Person.objects.get)(user = user)
            if _person.pfp:
                person_pfp = get_host(self) +'/media/'+ str(_person.pfp)
            else:
                person_pfp = None

            comm_msg_dict = {'community' : comm_id, 'created' : str(new_comm_message.created), 'id' : new_comm_message.id, 'media' : media, 'message' : new_comm_message.message, 'sender' : _person.display_name, 'sender_pfp' : person_pfp, 'time_sent' :  process_time(new_comm_message.created), 'same' : user}
            # send message to all members active
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':'new_comm_msg',
                    'message': comm_msg_dict,
                    
                    })
            # send alert to all users
            pcs = await database_sync_to_async(PersonCommunity.objects.filter)(community = _comm)
            pcs = await sync_to_async(list)(pcs)
            for pc in pcs:
                user_id = await database_sync_to_async(get_user_from_pc)(pc)
                await self.channel_layer.group_send(
                    f'user_{user_id}',
                    {
                        'type':'new_comm_msg',
                        'message' : {'comm_id' : _comm.id, 'last_text': new_comm_message.message, 'time' : process_time(new_comm_message.created)}
                    }
                )

    # broadcast to all active users
    async def new_comm_msg(self, event):
        if event['message']['same'] == self.scope['user']:
            event['message']['same'] = True
        else:
            event['message']['same'] = False 
        
        await self.send(json.dumps(event['message']))


def validate(user, comm_id):
        person = Person.objects.get(user = user)
        # get community and check if user is a member
        community = Community.objects.get(id = int(comm_id))
        if PersonCommunity.objects.get(person = person , community = community):
            return True
        else:
            return False



"""
    Private messages count. Gets all unread messages, the last text and the time send and alerts front end async
"""
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
    return return_dict


"""
    Community messages count. Gets all unread messages, the last text and the time send and alerts front end async
"""
def get_comm_messages(user_obj):
    _person = Person.objects.get(user = user_obj)
    pcommunities = PersonCommunity.objects.filter(person = _person)
    comms = []
    for _ in pcommunities:
        return_dict = {}
        last_text = CommunityMessage.objects.filter(community = _.community).last()
        if last_text == None:
            return_dict['last_text'] = 'No Messages'
            return_dict['time'] = ''
            return_dict['comm_id'] = _.community.id
        else:    
            return_dict['last_text'] = last_text.message
            return_dict['time'] = process_time(last_text.created)
            return_dict['comm_id'] = _.community.id
        comms.append(return_dict)
    return comms
def get_host(self):
    base = self.scope['headers']
    host = ''
    for _ in base:
        if _[0] == b'origin':
            host = _[1].decode('utf-8')
            break
    return host 



# serialize community
def construct_community(community_list, self):
    return_list = []
    for _ in community_list:
        return_dict = {} # store temporary values
        return_dict['name'] = _.name
        return_dict['is_private'] = _.is_private
        return_dict['creator'] = _.creator.display_name
        if _.pfp:
            host = get_host(self)
            return_dict['pfp'] = host + '/media/' + str(_.pfp)
        else:
            return_dict['pfp'] = None
        return_dict['comm_id'] = _.id
        # append to list
        return_list.append(return_dict)
    
    return return_list

def get_user_from_pc(pc):
    return pc.person.user.id

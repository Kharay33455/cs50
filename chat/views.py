from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializer import *
from .models import *
from base.models import Person, Community, PersonCommunity, Post
from base.serializers import PersonSerializer
from base.views import add_base
from datetime import datetime
from django.middleware.csrf import get_token


# Create your views here.
def get_today():
    today = datetime.today()
    _return = str(today)[:10]
    return _return

# process time
def process_time(time, true_time = False):
    time = str(time)
    get_today()
    date = time[:10]
    time = time[11:16]
    if true_time == True:
        return time
    if date != get_today():
        time = 'Yesterday'
    return time

# base api for chat section
@api_view(['GET'])
def chat(request):
    # check for authentication
    if request.user.is_authenticated:
        # set chat user to read
        chat_user = ChatUser.objects.get(user = request.user)
        chat_user.has_new_message = False
        chat_user.save()
        # get all chats where user is initiator or the person a chat connection is being initiated with
        _chats = Chat.objects.filter(user_1 = request.user.id)
        __chats = Chat.objects.filter(user_2 = request.user.id)
        # list to store all chat objects
        chats = []
        def get_chats(chat_set):
            _other_user = Person.objects.get(user= User.objects.get(id = chat_set['other']))
            __other_user = PersonSerializer(_other_user)
            other_user = __other_user.data
            if _other_user.pfp:

                other_user['pfp'] = add_base(request, other_user['pfp'])
            chat_set['chat']['time'] = process_time(chat_set['chat']['last_text_time'])
            _chat_ = {'chat': chat_set['chat'], 'other_user':other_user}
            chats.append(_chat_)
        #get user id to user in serialize chat fucntion
        user_id = request.user.id
        # serialize chats
        def serialize_chat(chat):
            try:
                print(chat)
                # get all messages associated with the chat to find the last chat
                _message = Message.objects.filter(chat = chat).order_by("-created").first()
                # serialize chat
                _chat = ChatSerializer(chat)
                _chat_ = _chat.data
                # append last message and the time it was sent
            
                _chat_['last_text'] = _message.message
                _chat_['last_text_time'] = str(_message.created)
                if user_id == chat.user_1:
                    _chat_['is_read'] = chat.user_1_has_read
                else:
                    _chat_['is_read'] = chat.user_2_has_read
            except Exception as e:
                print(e)

            return _chat_

        if _chats:
        # loop through all chat objects and serialize
            for c in _chats:

                _chat = {'chat': serialize_chat(c), 'other': c.user_2}
                get_chats(_chat)

        if __chats:
            for c in __chats:
                _chat = {'chat': serialize_chat(c), 'other': c.user_1}
                get_chats(_chat)

        # construct return response
        context = {}
        # sort chats by time. Showing the latest first
        context['chats'] = sorted(chats, key=lambda x : x['chat']['last_text_time'], reverse=True)

        # append user profile picture
        _person = Person.objects.get(user = request.user)
        if _person.pfp:
            context['pfp'] = add_base(request , "/media/"+ str(_person.pfp))
        else:
            context['pfp'] = 'None'    
        context['csrf'] = get_token(request)    
        return Response(context, status = 200)
    else:
        return Response({'err':'Sign in to see your messages'},status=301)

# message_s function to prepare chat for front end
def message_s(request, messages):
    # dictionaty to store results
    context = {}
    message_list = []
    # loop through al message objects in the query set
    for m in messages:
        # serialize message
        _message = MessageSerializer(m)
        _message_ = _message.data
        # filter message from and message to
        if m.user.user == request.user:
            _message_['from'] = False
        else:
            _message_['from'] = True
        # check for media, if one is avaiable, run add_base() to add the host to url
        if m.media:
            _message_['media'] = add_base(request, _message_['media'])
        # get the tine created for the mesage
        _message_['time'] = process_time(_message_['created'], true_time=True)
        message_list.append(_message_)
    context['messages'] = message_list
    # get csrf to send new messages securely
    context['csrf'] = get_token(request)

    return context

# function for take in an id of a chat and return all its messages in a query set
def get_all_messages(chat_id, user_id):
    chat = Chat.objects.get(id = chat_id)
    """Get requesting user id and change their has_read bool field to true"""
    # get user id check for user in chat object and sety has read to true

    # set requesting user chat is read bool field to true.
    if user_id == chat.user_1:
        chat.user_1_has_read = True
        other_user_id = chat.user_2
    else:
        chat.user_2_has_read = True
        other_user_id = chat.user_1
    # save chat
    chat.save()
    _dict = {}
    # get all messages associated with the chat and return json
    messages = Message.objects.filter(chat = chat)
    _dict['messages'] = messages
    _dict['other_user_id'] = other_user_id
    return _dict


# show chats 
@api_view(['GET'])
def show_chat(request):
    # get chat ID from request object and use it to get the chat object
    chat_id = request.GET.get('id')
    # get all messages for this chat id and store in query set
    messages = get_all_messages(chat_id=chat_id ,user_id=request.user.id)
    # run the message_s() function. It takes messages and request and returns 
    context = message_s(request, messages['messages'])
    context['other_user_id'] = messages['other_user_id']
    return Response(context, status=200)


# api for processing new messages sent
@api_view(['GET', 'POST'])
def send_message(request):
    if not request.user.is_authenticated:
        return Response({'err':'Sign in to continue'}, status=301)
    # get text and strip of white spaces
    text = str(request.data['caption'])
    text = text.strip()
    # check if text is an empty string
    if text == '':
        text = None
    # check for photo and append, if none, return none as image
    if request.FILES.get('image'):
        image = request.FILES.get('image')
    else:
        image = None
    # if both image and text is null, then it's not a valid message.
    if text == None and image == None:
        return Response({'msg':'No valid message'}, status= 201) 
    # if all is well, get chat and create new message
    chat_id = request.data['id']
    chat = Chat.objects.get(id = chat_id)
    chat_user = ChatUser.objects.get(user = request.user)
    message = Message.objects.create(message = text, media = image, chat = chat, user = chat_user)
    message.save()
    "Get other user and change their has_new_message field to True"
    # get other user Id and alert other user of their new message
    if request.user.id == chat.user_1:
        other_user_id = chat.user_2
        chat.user_2_has_read = False
    else:
        chat.user_1_has_read = False
        other_user_id = chat.user_1
    chat.save() # save chat
    # get chat object and set has_new_message to True
    other_user = ChatUser.objects.get(user = User.objects.get(id = other_user_id))
    other_user.has_new_message = True
    other_user.save()

    _message_list = Message.objects.filter(chat = chat)
    context =  message_s(request, _message_list)
    return Response(context, status=200)


# create a new post
@api_view(['GET', 'POST'])
def new_post(request):
    print('here')
    # make sure user is signed in. If not, redirect to login
    if request.user.is_authenticated:
        # get person
        person = Person.objects.get(user = request.user)
        # create dictionary to return as json
        context = {}
        community_list = []
        # if theyre sobmiting a post
        if request.method == "POST":
            # validate date
            post = str(request.data['post'])
            i = 1
            image_list = []
            # get all images and append to image_list
            while(i < 5):
                file = request.FILES.get(f'image{i}')
                if file:
                    image_list.append(file)
                i += 1
            # get community id image was sent to
            try:
                comm_id = int(request.data['commId'])
            except:
                # if user has somehow sent id thats somehow not valid           
                return Response({"err":'No community selected.'}, status=201)
            # alert program if images are avaolable
            with_image = False
            if image_list:
                with_image = True
            # if there are no images and text, don't allow process continue
            if with_image == False and post.strip() == "":
                return Response({"err":'Cannot make an empty post.'}, status=201)

            # create new post if all validation passed

            # get community to send post to
            community = Community.objects.get(id = comm_id)
            if str(request.data['isPrivate']) == 'true':
                is_private = True
            else:
                is_private = False
            #create post
            new_post_obj = Post.objects.create(op = request.user, post = post, community = community, isPrivate = is_private)
            i = 1
            # append all media
            for media in image_list:
                if i ==1:
                    new_post_obj.media1 = media
                if i == 2:
                    new_post_obj.media2 = media
                if i == 3:
                    new_post_obj.media3 = media
                if i == 4:
                    new_post_obj.media4 = media
                i += 1
            # save new post and get id to redirce tuser to post from frontend
            new_post_obj.save()
            post_id = new_post_obj.id

            return Response({"post_id":post_id}, status=200)
        # if it's just a get request, return all communities user can post to
        else:
            _pcs = PersonCommunity.objects.filter(person = person)
            for _ in _pcs:
                community_list.append({'name': _.community.name, 'comm_id':_.community.id})
                
            context['comm_info'] = community_list
            # append csrf to allow user submit their post request
            csrf = get_token(request)
            context['csrf'] = csrf
            return Response(context, status=200)
        
    else:
        # redirect to login with error
        return Response({'err':'Sign in to create a new post'}, status=301)
    

# new chat function
@api_view(['GET'])
def new_chat(request):
    # confirm authentication
    if not request.user.is_authenticated:
        return Response({'err':'Sign in to start chat'}, status=301)
    """Check if chat between requesting user and requested user exist"""
    # get id of requested user from request.get dictionary and requesting user Id, store as user 1 and user 2.
    user1 = int(request.GET.get('user1'))
    user2 = request.user.id
    # store id of chat in this variable
    chat_id = None
    # try to get id of chat between the two users and store in chat_id variable
    try:
        chat_id = Chat.objects.get(user_1 = user1, user_2 = user2).id
    except Chat.DoesNotExist:
        try:
            chat_id = Chat.objects.get(user_1 = user2, user_2 = user1).id
        except Chat.DoesNotExist:
            new_chat, created = Chat.objects.get_or_create(user_1 = user1, user_2 = user2)
            new_chat.save()
            chat_id = new_chat.id
    """Get other user display name and profile picture"""
    _user1 =User.objects.get(id = user1)
    _person = Person.objects.get(user = _user1)
    context = {}
    # append display name and pfp of other user to append to chat
    context['other_display_name'] = _person.display_name
    if _person.pfp:
        context['other_pfp'] = add_base(request, "/media/"+ str(_person.pfp))
    else:
        context['other_pfp'] = None
    context['id'] = chat_id
    # return chat id to front end to navigate to chat
    return Response(context, status=200)

# delete a chat
@api_view(['POST'])
def delete_chat(request):
    # get chat id
    chat_id = request.data['chatId']
    try:

        # get chat
        chat = Chat.objects.get(id = chat_id)
        # confirm user deleting chat is chat member
        if request.user.id != chat.user_1 and request.user.id != chat.user_2:
            return Response(status= 400)
        # now delete chat and inform front end of success
        print(chat)
        chat.delete()
        return Response(status = 204)
    except Chat.DoesNotExist:
        return Response(status=204)
    

# get all comms related to user
@api_view(['GET'])
def community_chats(request):
    _person = Person.objects.get(user = request.user) # person making request
    _pc = PersonCommunity.objects.filter(person = _person) # object to get all user's communities

    context = {}
    comm_list = []
    for _ in _pc:
        # get community last text
        community = _.community
        if community.pfp:
            comm_pfp = add_base(request, '/media/' + str(community.pfp))
        else:
            comm_pfp = None
        # get last message
        print(comm_pfp)
        _message = CommunityMessage.objects.filter(community = community).last()
        if _message:
            if _message.message:
                _message = str(_message.message)
                if len(_message) > 100:
                    _message = _message[0:100] + '...'
            else:
                _message = 'Photo'
        else:
            _message = 'Silent Night'
        comm_list.append({ 'community_pfp' : comm_pfp ,'community_name' : _.community.name, 'community_is_private' : _.community.is_private, 'community_id' : _.community.id, 'community_last_text' : _message})
    context['comm_list'] = comm_list
    return Response(context, status=200)

# all chat messages
@api_view(['GET', 'POST'])
def get_messages_for_community(request):
    _comm_id = int(request.GET.get('commId'))
    _community = Community.objects.get(id = _comm_id)
    # requesting user
    _person = Person.objects.get(user = request.user)
    # make sure they're part of the community they're requesting messages for
    try:
        _pc = PersonCommunity.objects.get(person = _person, community = _community)
    except PersonCommunity.DoesNotExist:
        context = {'err':'You\'re not a member of this community'}
        return Response(context, status=403)
    _chat_user_obj = ChatUser.objects.get(user =  request.user)
    # if method is post, make new message
    if request.method == 'POST':
        text = str(request.data['text']).strip()
        image = None
        print(request.FILES.get('image'))
        if request.FILES.get('image'):
            image = request.FILES.get('image')
        if text == "":
            text = None
        # only create message if it's valid
        if text != None or image != None:
            print('Saving')
            CommunityMessage.objects.create(message = text, sender = _chat_user_obj, community = _community, media = image)

    """Get all messages belonging to that community"""
    message_list = []
    messages = CommunityMessage.objects.filter(community = _community)
    context = {}
    for _ in messages:
        __ = CommunityMessageSerializer(_)
        _chat_user = _.sender
        _sender = Person.objects.get(user = _chat_user.user)
        ___ = __.data
        # check if user is message sender
        if _.sender == _chat_user_obj:
            ___['same'] = True
        else:
            ___['same'] = False
        # append user profile picture if any
        if _sender.pfp:
            ___['sender_pfp'] = add_base( request, '/media/' + str(_sender.pfp))
        else:
            ___['sender_pfp'] = "None"
        # sender display name
        ___['sender'] =_sender.display_name
        # time frmatted to hour and minute
        ___['time_sent'] = process_time(_.created)
        # append message media if available
        if _.media:
            ___['media'] = add_base(request, str(___['media']))

        
        message_list.append(___)
    context['msg_list'] = message_list
    context['csrf'] = get_token(request)
    context['community_details'] = {'community_name' : _community.name}

    return Response(context, status=200)

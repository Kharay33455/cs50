from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializer import *
from .models import *
from base.models import Person, Community, PersonCommunity, Post
from base.serializers import PersonSerializer
from base.views import add_base
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
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
        
        # serialize chats
        def serialize_chat(chat):
            # get all messages associated with the chat to find the last chat
            _message = Message.objects.filter(chat = chat).order_by("-created").first()
            # serialize chat
            _chat = ChatSerializer(chat)
            _chat_ = _chat.data
            # append last message and the time it was sent
            _chat_['last_text'] = _message.message
            _chat_['last_text_time'] = str(_message.created)

            return _chat_

        # loop through all chat objects and serialize
        for c in _chats:
            _chat = {'chat': serialize_chat(c), 'other': c.user_2}
            get_chats(_chat)
        
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

# show chats 
@api_view(['GET'])
def show_chat(request):
    # get chat ID from request object and use it to get the chat object
    chat_id = request.GET.get('id')
    chat = Chat.objects.get(id = chat_id)
    # get all messages associated with the chat and return json
    messages = Message.objects.filter(chat = chat)
    # run the message_s() function. It takes messages and request and returns 
    context = message_s(request, messages)
    return Response(context, status=200)


# api for processing new messages sent
@api_view(['GET', 'POST'])
def send_message(request):
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

            #create post
            new_post_obj = Post.objects.create(op = request.user, post = post, community = community)
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
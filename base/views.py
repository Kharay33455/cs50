from django.shortcuts import render
# Create your views here.
from rest_framework import serializers, permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from .serializers import *
from .models import *
from django.contrib.auth import login, logout, authenticate
import string
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.db import IntegrityError
from chat.models import ChatUser


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint to allow viewing and editing User model"""
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

def get_all_from_person(request, person):
    context = {}
    serializer = PersonSerializer(person)
    user = person.user
    context = serializer.data
    context['name'] = user.username
    if context['pfp']:
        context['pfp'] = add_base(request, context['pfp'])
    context['post']= []


    # fetch and serialize user's post
    posts = Post.objects.filter(op = user).order_by('-posted')
    for post in posts:
        _post = PostSerializer(post)
        # Loop through all medias and append base url.
        i = 1
        _context = _post.data
        _context['post_id'] = post.id
        allegiance, created = Allegiance.objects.get_or_create(user = request.user, post = post)
        _context['allege'] = allegiance.allegiance
        _context['is_shared'] = allegiance.shared
        _context['comment_count'] = len(Comment.objects.filter(post = post))
        post.comments = _context['comment_count']
        post.save()
        community_obj = post.community
        _context['community_name'] = community_obj.name
        _context['community'] = community_obj.id
        _context["community_is_private"] = community_obj.is_private
        while(i < 5):
            #append absolute uri to media. Remove first element as it is also a slash
            #absolute uri = localhost:8000/
            # media uri - /media_uri
            media_uri = _context[f'media{i}']
            if _context[f'media{i}']:
                _context[f'media{i}'] = add_base(request, media_uri)                
                # increase counter
                
            i += 1
        context['post'].append(_context)
    return context
    

@api_view(['GET'])
def get_person(request):
    if request.user.is_authenticated:
        # check if user is requesting their profile or another user's profile
        if request.GET.get('userId'):
            user = User.objects.get(id = str(request.GET.get('userId')))
            if user == request.user:
                return Response({'msg':'Same user'}, status=302)
            _person = Person.objects.get(user = user)
        else:
            _person = Person.objects.get(user= request.user)
        
        context = get_all_from_person(request=request, person=_person)
        if context == None:
            context = {}
        context['csrf'] = get_token(request)    
        return Response(context, status=200)
    else:
        context = {}
        context['err'] = 'Sign in to continue'
        return Response(context, status=301)


def thousands(num):
    num = int(num)
    if num > 999:
        num = str(round(num/1000, 2))
        return f'{num}K'
    else:
        return str(num)
    
def add_base(request, string):
    base_url =  str(request.build_absolute_uri('/'))
    string = base_url + str(string[1:])
    return string

    
@api_view(['GET'])
def base(request):
    posts = Post.objects.all().order_by('?')
    context = {'posts':[], 'user_data': {}}
    user_pfp = "None"
    if request.user.is_authenticated:
        context['user_data']['id'] = request.user.id
        person = Person.objects.get(user = request.user)
        # Append pfp if avaivable
        if person.pfp:
            user_pfp = str(person.pfp)
            if user_pfp != "None":
                user_pfp = add_base(request, "/media/" + user_pfp)
        

    # store signed in user profile picture in context dictionary under user_data
    context['user_data']['pfp'] = user_pfp

    for post in posts[:25]:
        p = PostSerializer(post)
        _post = p.data
        # get op id. WE have edited it to name in down this function.
        _post['op_id'] = _post['op']
        _post['post_id'] = post.id
        # get post allegiance
        if request.user.is_authenticated:
            allege_obj, created = Allegiance.objects.get_or_create(user = request.user, post = post)
            _post['allege'] = allege_obj.allegiance
            _post['is_shared'] = allege_obj.shared
        comments = Comment.objects.filter(post = post)
        _post['comments'] = len(comments)
        post.comments = _post['comments']
        post.save()
        post_community = Community.objects.get(id = _post['community'])
        _post['community_name'] = post_community.name
        _post['community_is_private'] = post_community.is_private
        context['posts'].append(_post)

    for c in context['posts']:
        i = 1
        while (i < 5):
            if c[f'media{i}']:
                c[f'media{i}'] = add_base(request, c[f'media{i}'])
            i += 1
        person = Person.objects.get(user = c['op'])
        c['op'] = person.user.username
        c['display'] = person.display_name
        c['likes'] = thousands(c['likes'])
        c['frowns'] = thousands(c['frowns'])
        c['ghost_likes'] = thousands(c['ghost_likes'])
        c['comments'] = thousands(c['comments'])
        c['shares'] = thousands(c['shares'])
        if person.pfp:
            c['oppfp'] = add_base(request, "/media/"+str(person.pfp))
        if len(c['post']) > 150:
            c['post'] = c['post'][0:150] + "..."
    return Response(context, status=200)


def bases(request):
    post = Post.objects.first()
    return render(request, 'base/index.html', {'post': post})

def check_bad_data(data):
    strings = string.ascii_lowercase + string.ascii_uppercase+ string.digits
    for a in data:
        if a not in strings:
            return 1
    if len(str(data)) > 30:
        return 1
    return 0


@api_view(['GET','POST'])
def login_request(request):

    if request.method == 'POST':
        username = request.data.get('name')
        password = request.data.get('pass')
        if check_bad_data(username) == 1:
            context = {'err':'bad data'}
            return Response(context, status=400)
        
        user = authenticate(request, username=username, password = password)
        if user is not None:
            login(request, user)
            _person = Person.objects.get(user = user)
            person = PersonSerializer(_person)
            context = person.data
            context['display'] = username
            context['msg'] = 'success'
            user = PersonSerializer()
            return Response(context , status=200)
        else:
            # In case of invalid credentials, tell user and reappend new csrf token
            return Response({'err': 'Invalid username or passoword'}, status=401)
    else:
        # They have just visited the log in screen for the first time. Append csrf token to send back their request
        csrf = get_token(request)
        context = {}
        context['csrf'] = csrf
        return Response(context, status=200)

@api_view(['GET'])
def logout_request(request):
    logout(request)
    return Response({'msg':'Logged out'}, status=200)


# get allegainces for users to post. Likes, shares, etc
@api_view(['GET'])
def allegiances(request):
    # get allegaince sent to server from user via api
    allege = request.GET.get('allege')
    # check if they're authenticated or theyre not trying to change allegaince, just view it.
    if request.user.is_authenticated or allege == 'none' or allege == 'load':
        # get post
        post_id = request.GET.get('postID')
        post = Post.objects.get(id = int(post_id))
        # get allegiance for authenticated users
        if request.user.is_authenticated:
            current_allegiance, created = Allegiance.objects.get_or_create(user = request.user, post = post)
        # check if theyre reacting to the psot
        if allege == 'like' or allege == 'frown' or allege == 'ghost':
            # get the notifications sent to post owner for the requesting user's previous reaction to post
            # all users can only keep one reaction per post
            _nofifs = Notification.objects.filter(type__in = ['liked-post', 'disliked-post' , 'ghost-liked'], id_item = post_id, person__in = Person.objects.filter(user__in = [request.user , post.op]))
            # if they have reacted to post earlier, delete it
            for _ in _nofifs:
                _.delete()
            person =  Person.objects.get(user = request.user )
            # create new notification for the new alegiance
            if allege == 'like':
                type = 'liked-post'
                message = 'liked your post.'
            if allege == 'frown':
                type = 'disliked-post'
                message = 'disliked your post'
            if allege == 'ghost':
                type = 'ghost-liked'
                message = ', you have a ghost.'
                person = Person.objects.get(user = post.op)
            # if they are reacting to their own post, no need to inform them
            if request.user != post.op:
                Notification.objects.get_or_create(type=type, message = message, person = person, associated_user = post.op, id_item = post_id)
            # set their new allegiance
            current_allegiance.allegiance = allege
        # check if this is a share, not just a like
        if allege == 'share':
            # if it is shared already, unshare and delete notifications to post owner about their sharing
            if current_allegiance.shared:
                current_allegiance.shared = False
                _ = Notification.objects.filter(type = 'shared', id_item = post_id )
                for __ in _:
                    __.delete()
            # if they have never shared this post, share it and alert post owner their post was just shared
            else:
                current_allegiance.shared = True
                if request.user != post.op:
                    a, created = Notification.objects.get_or_create(type='shared', message = "shared your post", person = Person.objects.get(user = request.user), associated_user = post.op, id_item = post_id)

        # if there's been a change in allegiance, save new changes            
        if allege != 'load' and allege != 'none':
            current_allegiance.save()
        
        # count all allegiances for post from all users
        _likes = len(Allegiance.objects.filter(post = post, allegiance = 'like'))
        post.likes = _likes
        _frowns = len(Allegiance.objects.filter(post = post, allegiance = 'frown'))
        post.frowns = _frowns
        _ghosts = len(Allegiance.objects.filter(post = post, allegiance = 'ghost'))
        post.ghost_likes = _ghosts
        _shares = len(Allegiance.objects.filter(post = post, shared = True))
        post.shares = _shares
        # if this is just a user viewing post, increase post interactions
        if allege == 'none':
            post.interactions += 1
        # save post
        post.save()
        # if the user is authenticated
        if request.user.is_authenticated:
            context = {"msg":"LIKED","likes":_likes, "frowns":_frowns, "ghosts":_ghosts, "shares":_shares, 'is_shared' : current_allegiance.shared, 'interactions' : post.interactions , 'allege_now' : current_allegiance.allegiance}
        # if they're not authenticated but are viewing post data
        else:
            context = {"msg":"LIKED","likes":_likes, "frowns":_frowns, "ghosts":_ghosts, "shares":_shares, 'interactions' : post.interactions }
        return Response(context, status=200)            
    # if they're not authenticated, return redirect response.
    else:
        return Response({'err:Sign in to continue'}, status=301)
    
@api_view(['GET'])
@csrf_exempt
def extend_post(request):
    if request.user.is_authenticated:

        post_id = request.GET.get('postId')
        post = Post.objects.get(id = post_id)
        allegiance, created = Allegiance.objects.get_or_create(user = request.user, post = post)
        _poster = Person.objects.get(user = post.op)
        _poster_ = PersonSerializer(_poster)
        poster = _poster_.data
        p = PostSerializer(post)
        _post = p.data
        context = {}
        context['post'] = _post
        context['post']['allege'] = allegiance.allegiance
        context['post']['is_shared'] = allegiance.shared
        context['post']['op_username'] = _poster.user.username
        context['post']['op_display_name'] = _poster.display_name
        if _poster.pfp:
            context['post']['op_pfp'] = add_base(request, poster['pfp'])

        i = 1
        while i < 5:
            if context['post'][f'media{i}']:
                context['post'][f'media{i}'] = add_base(request, "/"+context['post'][f'media{i}'])
            i += 1
        _person =  Person.objects.get(user = request.user)
        _person_ = PersonSerializer(_person)
        person = _person_.data
        if _person.pfp:
            context['user_pfp'] = add_base(request , person['pfp'])
        else:
            context['user_pfp'] = "None"
        context['community_name'] = Community.objects.get(id = int(context['post']['community'])).name
        return Response(context, status = 200)
    else:
        return Response(status=301)

@csrf_exempt
@api_view(['GET'])
def add_comment(request):
    comment = request.GET.get('comment')
    post_id = request.GET.get('postId')
    post = Post.objects.get(id = post_id) 
    def get_all_comments():
        comments = Comment.objects.filter(post = post).order_by('-created')
        comment_list = []
        comment_count = len(comments)
        post.comments = comment_count
        post.save()
        for comment in comments:
            _comment = CommentSerializer(comment)
            _comment_ = _comment.data
            _comment_['user_name'] = comment.user.username
            person = Person.objects.get(user = comment.user)
            _comment_['display_name'] = person.display_name
            _comment_['date'] = comment.created.date()
            _comment_['time'] = comment.created.time().strftime("%H:%M")
            if person.pfp:
                _comment_['pfp'] = add_base(request, "/media/" + str(person.pfp))
            comment_list.append(_comment_)
        return_dict = {'comment_count' : comment_count, 'comment_list' : comment_list}
        
        return return_dict

    def get_all():
        content = get_all_comments()
        context['comments'] = content['comment_list']
        context['comment_count'] = content['comment_count']

    # dict to store response
    context = {}
    if str(comment).strip() == "":
        # get all comments and add to dict as comments
        get_all()        
        return Response(context, status=200)
    comment = Comment.objects.create(user = request.user, post = post, comment = comment)
    if request.user != post.op:
        Notification.objects.create(type='commented', message ="commented on your post", person = Person.objects.get(user = request.user), associated_user = post.op, id_item = post_id)
    get_all()
    return Response(context, status=200)

def serialize(request, comm_obj_list):
    _list = []
    for i in comm_obj_list:

        _comm_obj_list = PersonCommunitySerializer(i)
        _comm_obj_list_ = _comm_obj_list.data
        community_dets = i.community
        _comm_obj_list_['creator'] = community_dets.creator.user.username
        _comm_obj_list_['name'] = community_dets.name
        _comm_obj_list_['is_private'] = community_dets.is_private
        _comm_obj_list_['member_count'] = len(PersonCommunity.objects.filter(community = community_dets))
        try:
            _joined = JoinRequest.objects.get(user = request.user, community = i.community )
            _comm_obj_list_['requested'] = True
        except:
            _comm_obj_list_['requested'] = False
        _list.append(_comm_obj_list_)
    return _list



@api_view(['GET'])
def community(request):
    if request.user.is_authenticated:
        which = request.GET.get('which')
        lat = request.GET.get('lat')
        long = request.GET.get('long')
        dist = request.GET.get('dist')
        __person =  Person.objects.get(user = request.user)
        context = {}
        if which == 'mine':
            comm_objs = PersonCommunity.objects.filter(person = __person).order_by('?')

        if which == 'near':
            __person.long = long
            __person.lat = lat
            __person.save()
            persons_long = Person.objects.filter(long__lt = float(long) + float(dist)).filter(long__gt = float(long) -float(dist))
            persons_lat = Person.objects.filter(lat__lt = float(lat) + float(dist)).filter(lat__gt = float(lat) -float(dist))
            persons = persons_lat & persons_long
            query_set = []
            communities = []
            _communities = PersonCommunity.objects.filter(person = __person)
            for c in _communities:
                communities.append(c.community)
            for person in persons:
                comm_obj = PersonCommunity.objects.filter(person = person)
                for _comm_obj in comm_obj:
                    if _comm_obj.community not in communities:
                        if _comm_obj not in query_set:
                            query_set.append(_comm_obj)
                            communities.append(_comm_obj.community)

            comm_objs = query_set
            if float(dist) < 400 and float(dist) > -400:
                context['dist'] = float(dist) * 2
            else:
                context['dist'] = float(dist)
        context['communities'] = serialize(request, comm_objs)
        if __person.pfp:
            __person_ = PersonSerializer(__person)
            _person = __person_.data
            context['pfp'] =  add_base(request, _person['pfp'])
        else:
            context['pfp'] = "None"
        return Response(context, status=200)
    else:
        return Response({'err':'Sign in to view communities'}, status=301)

@api_view(['GET'])
def get_post_by_community(request):
    community_id = request.GET.get('id')
    _community = Community.objects.get(id = community_id)
    person = Person.objects.get(user = request.user)
    _person = PersonSerializer(person)
    _person_ = _person.data
    posts = Post.objects.filter(community = _community).order_by("-posted")
    post_list = []
    for post in posts:
        _allege, created = Allegiance.objects.get_or_create(post = post, user = request.user)
        _op = Person.objects.get(user = post.op)
        __op = PersonSerializer(_op)
        _op_ = __op.data
        _post = PostSerializer(post)
        _post_ = _post.data
        _post_['is_shared'] = _allege.shared
        if _op.pfp:
            _post_['oppfp'] = add_base(request, _op_['pfp'])
        else:
            _post_['oppfp'] = "None"
        _post_['display'] = _op.display_name
        _post_['op'] = _op.user.username
        _post_['allege'] = _allege.allegiance
        _post_['op_id'] = _op.user.id
        ## append base to all media
        i = 1
        while i < 5:
            if _post_[f'media{i}']:
                _post_[f'media{i}'] = add_base(request, _post_[f'media{i}'])
            i += 1
        post_list.append(_post_)
    context = {}
    context['post_list'] = post_list
    context['length'] = len(post_list)
    _com_dets = {}
    _com_dets['community_is_private'] = _community.is_private
    _com_dets['community_name'] = _community.name

    context['community_details'] = _com_dets
    if _person_['pfp']:
        context['user_pfp'] = add_base(request, _person_['pfp'])
    else:
        context['user_pfp'] = 'None'
    
    # pass user id of current user
    context['user_id'] = request.user.id
    # check if user is mod of community
    _person = Person.objects.get(user = request.user)
    _pc = PersonCommunity.objects.get(person = _person, community = _community)
    context['isMod'] = _pc.isMod
    return Response(context, status=200)


@api_view(['GET'])
def get_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(associated_user = request.user).order_by('-time')
        notif_list = []
        for notif in notifications:
            person = notif.person
            _person = PersonSerializer(person)
            _person_ = _person.data
            _notif = NotificationSerializer(notif)
            _notif_ = _notif.data
            if person.pfp:
                _notif_['oppfp'] = add_base(request, _person_['pfp'])
            _notif_['user'] = _person_['display_name']
            _notif_['user_id'] = _person_['id']
            if notif.type == "commented" or notif.type == "liked-post" or notif.type == "ghost-liked" or notif.type == "disliked-post" or notif.type == "shared":
                post = Post.objects.get(id = _notif_['id_item'])
                _notif_['post_id'] = post.id
                _notif_['post'] = post.post
            if notif.type == "liked-comment":
                _comment = Comment.objects.get(id = _notif_['id'])
                _notif_['post'] = _comment.comment
                _notif_['post_id'] = _comment.post.id
            try:            
                if len(_notif_['post']) > 150:
                    _notif_['post'] = _notif_['post'][:150] + "..."
            except:
                pass
            
            notif_list.append(_notif_)
        context = {}
        context['notif'] = notif_list
        _person__ = PersonSerializer(Person.objects.get(user = request.user))
        person_data = _person__.data
        if person_data['pfp']:
            context['pfp'] = add_base(request, person_data['pfp'])
        else:
            context['pfp'] = 'None'
        return Response(context, status=200)
    else:
        # redirect to login with error message for not authenticated users
        return Response({'err':'Sign in to view your notifications'},status=301)
@api_view(['GET'])
def join_community(request):
    """
    _person = Person.objects.get(user = request.user)
    long = _person.long
    lat = _person.lat
    dist = 25.0
    persons_long = Person.objects.filter(long__lt = float(long) + float(dist)).filter(long__gt = float(long) -float(dist))
    persons_lat = Person.objects.filter(lat__lt = float(lat) + float(dist)).filter(lat__gt = float(lat) -float(dist))
    persons = persons_lat & persons_long
    query_set = []
    communities = []
    _communities = PersonCommunity.objects.filter(person = _person)
    for c in _communities:
        communities.append(c.community)
    for person in persons:
        comm_obj = PersonCommunity.objects.filter(person = person)
        for _comm_obj in comm_obj:
            if _comm_obj.community not in communities:
                if _comm_obj not in query_set:
                    query_set.append(_comm_obj)
                    communities.append(_comm_obj.community)
    comm_objs = query_set
    context = {}
    context['communities'] = serialize(comm_obj_list= comm_objs) 
    if _person.pfp:
        context['pfp'] = add_base(request, '/media/'+ str(_person.pfp))
    else:
        context['pfp'] = "None"
    context['dist'] = 25.01
    """

    community_id = request.GET.get('communityId')
    community_obj = Community.objects.get(id = int(community_id))
    person = Person.objects.get(user = request.user)
    if community_obj.is_private == True:
        JoinRequest.objects.get_or_create(user = request.user, community = community_obj)
        return Response(status=202)
    else:
        PersonCommunity.objects.get_or_create(person = person, community = community_obj)
        return Response(status=200)

@api_view(['GET'])
def community_request(request):
    person = Person.objects.get(user = request.user)
    comm_id = request.GET.get('id')
    community_obj = Community.objects.get(id = comm_id )
    rel = PersonCommunity.objects.get(person = person, community = community_obj)
    # make sure only mods can access data
    if rel.isMod == False:
        return Response({'err':"you're not mod"}, status= 403)

    #accept or reject request
    item_id = int(request.GET.get('itemId'))
    action = int(request.GET.get('action'))
    try:
        join_req  = JoinRequest.objects.get(id = item_id)
        user = User.objects.get(id = join_req.user.id)
        _community = join_req.community
        person = Person.objects.get(user = user)
        if action == 0:
             #accept
            
            
            PersonCommunity.objects.get_or_create(person = person, community = _community)
            join_req.delete()

            #notify user
            Notification.objects.get_or_create(type = "accepted-join", message = f", your request to join {_community.name} was accepted.", person = person, associated_user = user )

        if action == 1:
            # decline
            join_req.delete()
            # notify user
            Notification.objects.get_or_create(type = "rejected-join", message = f", your request to join {_community.name} was rejected.", person = person, associated_user = user )

    except Exception as e:
        Error.objects.create(error = e)
    


    _join_requests = JoinRequest.objects.filter(community = community_obj)
    _join_list = []
    for _ in _join_requests:
        __ = JoinRequestSerializer(_)
        ___ = __.data
        ___['username'] = User.objects.get(id = ___['user'] ).username
        _join_list.append(___)
    context = {}
    context['join_requests'] = _join_list
    return Response(context, status= 200)

# register new users
@api_view(['POST'])
def register_request(request):
    # get data from form
    form_data = request.data
    username = str(form_data['name']).strip()
    pass1 = str(form_data['pass']).strip()
    pass2 = str(form_data['pass2']).strip()
    display_name = str(form_data['displayName']).strip()

    # validate bad data on username 
    if check_bad_data(username) == 1:
        return Response({'err':f'Invalid username "{username}". Username can only contain letters and numbers and cannot exceed 30 characters.'}, status=403)
    
    # check both passwords match
    if pass1 != pass2:
        return Response({'err':'Error. Passwords did not match'}, status=403)
    
    # confim password is long enough
    if len(pass1) < 8:
        return Response({'err':'Password must contain at least 8 characters.'}, status=403)
    
    # make sure user has provided a display name
    if display_name == "":
        return Response({'err':'Display name cannot be blank'}, status=403)

    # try to create a new user with form data
    try:
        # create new user
        new_user = User.objects.create(username = username, password = pass1)
        new_user.save()
        # create new person and Chat user object for users provided it doesn't already somehow exist
        # person
        Person.objects.get_or_create(user = new_user, display_name = display_name)


        # chat user
        ChatUser.objects.get_or_create(user = new_user)

        # authenticate and log in user
        login(request, new_user)
        return Response({'msg': 'Success', 'id': new_user.id}, status= 200)
    # return error if user with that username already exists 
    except IntegrityError as e:
       return Response({'err':'A user with this username already exist. Sign in instead.'}, status=403)
    # Handle unplanned error
    except Exception as e:
        error = f'Program ran into runtime error while trying to create user with {form_data}'
        Error.objects.create(error = error)
        return Response({'err': 'An unexpected error has occured. Reload app and try again.'},  status=403)
    

# update person info from bio
@api_view(['GET', 'POST'])
def update_person(request):
    #dictionary to return 
    context = {}
    # check what data is being changed
    which = str(request.data['which']).strip()
    _person = Person.objects.get(user = request.user)
    # change data
    if which == 'bio':
        try:
            new_bio = str(request.data['bio']).strip()
            # get person, change their bio and save.
        
            _person.bio = new_bio
        except:
            return Response(status=400)
    if which == 'pfp':
        try:
        
            new_pfp = request.FILES.get('pfp')
            _person.pfp = new_pfp
        except Exception as e:
            Error.objects.create(error = e)
    if which == 'displayName':
        new_display_name = str(request.data['displayName']).strip()
        _person.display_name = new_display_name
    # save
    _person.save()
    if which == 'pfp':
        context['pfp'] = add_base(request, '/media/' + str(_person.pfp))
    context['msg'] = 'person was updated succesfully'
    # tell user save was successful
    return Response(context, status=200)
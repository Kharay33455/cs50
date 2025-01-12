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

# function to get details about person from person object
def get_all_from_person(request, person):
    context = {}
    serializer = PersonSerializer(person)
    user = person.user
    context = serializer.data
    context['name'] = user.username
    if context['pfp']:
        context['pfp'] = add_base(request, context['pfp'])
    context['post']= []

    # get all posts shared by person
    allegs = Allegiance.objects.filter(user = user, shared = True)

    posts = []
    for _ in allegs:
        if not _.post.isPrivate:
            posts.append(_.post)

    # fetch and serialize user's post
    _posts = Post.objects.filter(op = user, isPrivate = False)
    for _p in _posts:
        if _p not in posts:
            posts.append(_p)
    
    # merge users's post with shared posts
    
    for post in posts:
        original_poster = Person.objects.get(user = post.op)
        _post = PostSerializer(post)
        # Loop through all medias and append base url.
        i = 1
        _context = _post.data
        _context['op_display_name'] = original_poster.display_name
        _context['op_user_name'] = original_poster.user.username
        _context['op_user_id'] = original_poster.user.id
        if original_poster.pfp:
            _context['op_pfp'] = add_base(request, '/media/' + str(original_poster.pfp))
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
    print(context)
    context['post'] = sorted(context['post'], key = lambda x: x['posted'], reverse=True)
    print('\n\n\n\n\n\n\n\n')
    print(context)
    return context
    
# function to return json about person.
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
        # return dictionary. Context is None if no matching posts exists, return an empty dictionary instead
        context = get_all_from_person(request=request, person=_person)
        if context == None:
            context = {}
        # get csrf token to pass request with
        context['csrf'] = get_token(request) 
        # user id to help track user to post id relationship on frontend   
        context['request_id'] = request.user.id
        return Response(context, status=200)
    else:
        # If user isnt signed in, redirect them to login
        context = {}
        context['err'] = 'Sign in to continue'
        return Response(context, status=301)

# function to format number count.
def thousands(num):
    num = int(num)
    if num > 999:
        num = str(round(num/1000, 2))
        return f'{num}K'
    else:
        return str(num)

# append host url to image to allow them be queried from outside app
def add_base(request, string):
    base_url =  str(request.build_absolute_uri('/'))
    string = base_url + str(string[1:])
    return string

    
# home screen view
@api_view(['GET'])
def base(request):
    # get all posts
    posts = Post.objects.filter(isPrivate = False).order_by('?')
    # dictionary to store posts
    context = {'posts':[], 'user_data': {}}
    #  get user pfp if available
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
        # get post allegiance if user is signed in
        if request.user.is_authenticated:
            allege_obj, created = Allegiance.objects.get_or_create(user = request.user, post = post)
            _post['allege'] = allege_obj.allegiance
            _post['is_shared'] = allege_obj.shared
        # get all comments, count and save to post.comments
        comments = Comment.objects.filter(post = post)
        _post['comments'] = len(comments)
        post.comments = _post['comments']
        post.save()
        # get post community, append name and privacy to return objects
        post_community = Community.objects.get(id = _post['community'])
        _post['community_name'] = post_community.name
        _post['community_is_private'] = post_community.is_private
        context['posts'].append(_post)

    # generate extra data for post
    for c in context['posts']:
        i = 1
        # append all media
        while (i < 5):
            if c[f'media{i}']:
                c[f'media{i}'] = add_base(request, c[f'media{i}'])
            i += 1
        # get post owner
        person = Person.objects.get(user = c['op'])
        # append all details
        c['op'] = person.user.username
        c['display'] = person.display_name
        c['likes'] = thousands(c['likes'])
        c['frowns'] = thousands(c['frowns'])
        c['ghost_likes'] = thousands(c['ghost_likes'])
        c['comments'] = thousands(c['comments'])
        c['shares'] = thousands(c['shares'])
        # if person ha profile picture, append profile picture
        if person.pfp:
            c['oppfp'] = add_base(request, "/media/"+str(person.pfp))
        # truncate post and only return the first 150 values
        if len(c['post']) > 150:
            c['post'] = c['post'][0:150] + "..."
    # return json
    return Response(context, status=200)

# testing static config
def bases(request):

    return render(request, 'base/index.html')

# check bad data in username. ONly accepts alphanumric values
def check_bad_data(data):
    strings = string.ascii_lowercase + string.ascii_uppercase+ string.digits
    for a in data:
        if a not in strings:
            return 1
    # make sure username is also under 30 characters
    if len(str(data)) > 30:
        return 1
    return 0


# login request
@api_view(['GET','POST'])
def login_request(request):
    # check if method is post
    if request.method == 'POST':
        # get details sent to backend from frontend
        username = request.data.get('name')
        password = request.data.get('pass')
        # run the check data function, return error if data is bad
        if check_bad_data(username) == 1:
            context = {'err':'bad data'}
            return Response(context, status=400)
        # if not,try to authenticate user
        user = authenticate(request, username=username, password = password)
        # on succes, login user, ge their details and return
        if user is not None:
            login(request, user)
            _person = Person.objects.get(user = user)
            person = PersonSerializer(_person)
            context = person.data
            context['display'] = username
            context['msg'] = 'success'
            user = PersonSerializer()
            return Response(context , status=200)
        # alert user of invalid password
        else:
            # In case of invalid credentials, tell user and reappend new csrf token
            return Response({'err': 'Invalid username or passoword'}, status=401)
    else:
        # They have just visited the log in screen for the first time. Append csrf token to send back their request
        csrf = get_token(request)
        context = {}
        context['csrf'] = csrf
        return Response(context, status=200)

# log out request
@api_view(['GET'])
def logout_request(request):
    # make sure their session is still valid to avoid errors
    if request.user.is_authenticated:
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
    
# Extend post
@api_view(['GET'])
def extend_post(request):
    # check if user is authenticated
    if request.user.is_authenticated:
        # get data sent with request
        post_id = request.GET.get('postId')
        # get psot, alleguance for signed in user and details of the post owner
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
        # append their dp only if they have one
        if _poster.pfp:
            context['post']['op_pfp'] = add_base(request, poster['pfp'])

        # append all media
        i = 1
        while i < 5:
            if context['post'][f'media{i}']:
                context['post'][f'media{i}'] = add_base(request, "/"+context['post'][f'media{i}'])
            i += 1
        _person =  Person.objects.get(user = request.user)
        _person_ = PersonSerializer(_person)
        person = _person_.data
        # user profile picture if available
        if _person.pfp:
            context['user_pfp'] = add_base(request , person['pfp'])
        else:
            context['user_pfp'] = "None"
        context['community_name'] = Community.objects.get(id = int(context['post']['community'])).name
        context['user_id'] = request.user.id
        # return context dictionary as json
        return Response(context, status = 200)
    else:
        # if they're not signed in, redirect to login
        return Response(status=301)

# add comments
@api_view(['GET'])
def add_comment(request):
    # incase of a request to comment without authenticated
    if request.user.is_authenticated == False:
        return Response(status=400)
    # get comment and psot id from user
    comment = request.GET.get('comment')
    post_id = request.GET.get('postId')
    post = Post.objects.get(id = post_id) 
    

    # function to get all comments associted with a post
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

    # function to get all comments and append it to context dictionary
    def get_all():
        content = get_all_comments()
        context['comments'] = content['comment_list']
        context['comment_count'] = content['comment_count']

    # dict to store response
    context = {}
    # user sent empty string as comment
    if str(comment).strip() == "":
        # get all comments and add to dict as comments
        get_all()        
        return Response(context, status=200)
    # create new comment
    comment = Comment.objects.create(user = request.user, post = post, comment = comment)
    # if commenter is not post owenr, notify post owner of comment to their post
    if request.user != post.op:
        Notification.objects.create(type='commented', message ="commented on your post", person = Person.objects.get(user = request.user), associated_user = post.op, id_item = post_id)
    get_all()
    return Response(context, status=200)

# fucntion to prepare community objects for front end from community object array
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
        if community_dets.pfp:
            _comm_obj_list_['pfp'] = add_base(request, '/media/'+ str(community_dets.pfp))
        else:
            _comm_obj_list_['pfp'] = None
        # check if user requesting community page has sent a join request to this commuity that remains unaprroed.
        # This is to alert the front end of the request and prevent theem from sending another
        try:
            _joined = JoinRequest.objects.get(user = request.user, community = i.community )
            _comm_obj_list_['requested'] = True
        except:
            _comm_obj_list_['requested'] = False
        # add object tt list
        _list.append(_comm_obj_list_)
    return _list


# community api request 
@api_view(['GET'])
def community(request):
    # checking for authentication
    if request.user.is_authenticated:
        # get all data passed with request
        which = request.GET.get('which') # decide if you want to see your communities or communities near you

        # location of user. Gotten from expo 
        lat = request.GET.get('lat')
        long = request.GET.get('long')

         # value of range to search for new communities
        dist = request.GET.get('dist')

        #get person object and use it to filter communities belinging to that perosn if which is mine
        __person =  Person.objects.get(user = request.user)
        context = {}
        if which == 'mine':
            comm_objs = PersonCommunity.objects.filter(person = __person).order_by('?')

        # if they are requesting communities around them, get all users close to them within the range of request
        # displau coomunities those users are in that user isn't in
        if which == 'near':
            __person.long = long
            __person.lat = lat
            __person.save()
            # find all persons within range of longitue of user plus or minus distance... DO same for lat
            persons_long = Person.objects.filter(long__lt = float(long) + float(dist)).filter(long__gt = float(long) -float(dist))
            persons_lat = Person.objects.filter(lat__lt = float(lat) + float(dist)).filter(lat__gt = float(lat) -float(dist))
            
            # get players that fall inn both category. IE: long and lat is close to user
            persons = persons_lat & persons_long
            # get all communities associated with all users matching query
            query_set = []
            communities = []
            # get all communities user belongs to
            _communities = PersonCommunity.objects.filter(person = __person)
            for c in _communities:
                communities.append(c.community)
            # loop throught close by users
            for person in persons:
                # get all communities close to person
                comm_obj = PersonCommunity.objects.filter(person = person)
                # loop through communities and check user isn't already a memner. If they're not, append to list storing community
                for _comm_obj in comm_obj:
                    if _comm_obj.community not in communities:
                        if _comm_obj not in query_set:
                            query_set.append(_comm_obj)
                            communities.append(_comm_obj.community)

            comm_objs = query_set
            # increase unless you're over 360... IE: globe covered.
            if float(dist) < 400 and float(dist) > -400:
                context['dist'] = float(dist) * 2
            else:
                context['dist'] = float(dist)
        # return community as object
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

# get community posts
@api_view(['GET'])
def get_post_by_community(request):
    context = {}
    # get community id from request object and get community
    community_id = int( request.GET.get('id'))
    _community = Community.objects.get(id = community_id)

    # get data on user
    person = Person.objects.get(user = request.user)
    _person = PersonSerializer(person)
    _person_ = _person.data
    # filter all posts belonging to community, If they're not a member, show only public posts
    try:
        _pc = PersonCommunity.objects.get(person = person, community = _community)
        context['isMod'] = _pc.isMod
        posts = Post.objects.filter(community = _community).order_by("-posted")
    except PersonCommunity.DoesNotExist:
        context['notMember'] = True
        posts = Post.objects.filter(community = _community, isPrivate = False).order_by("-posted")
    

    # loop through psot, serialize and append to post list
    post_list = []
    for post in posts:
        _allege, created = Allegiance.objects.get_or_create(post = post, user = request.user)
        _op = Person.objects.get(user = post.op)
        __op = PersonSerializer(_op)
        _op_ = __op.data
        _post = PostSerializer(post)
        _post_ = _post.data
        _post_['is_shared'] = _allege.shared
        # append profile picture if it exists. append none instead
        if _op.pfp:
            _post_['oppfp'] = add_base(request, _op_['pfp'])
        else:
            _post_['oppfp'] = "None"
        # add extra data about user    
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
    # construct context object
    context['post_list'] = post_list
    context['length'] = len(post_list)
    _com_dets = {}
    _com_dets['community_is_private'] = _community.is_private
    _com_dets['community_name'] = _community.name
    _com_dets['community_description'] = _community.description
    if _community.pfp:
        comm_pfp = add_base(request, '/media/' + str(_community.pfp))
    else:
        comm_pfp = None

    context['community_details'] = _com_dets
    context['community_details']['community_pfp'] = comm_pfp
    # append user pfp is they have one
    if _person_['pfp']:
        context['user_pfp'] = add_base(request, _person_['pfp'])
    else:
        context['user_pfp'] = 'None'
    
    # pass user id of current user
    context['user_id'] = request.user.id
    # check if user is mod of community
    # return community ID. USers on the front would need this to exit the community
    context['community_details']['community_id'] = community_id
    context['csrf'] = get_token(request)
    return Response(context, status=200)



# api to get all notifications
@api_view(['GET'])
def get_notifications(request):
    # confirming authentication
    if request.user.is_authenticated:
        # filter all notifications for user
        notifications = Notification.objects.filter(associated_user = request.user).order_by('-time')
        # list of notification objects
        notif_list = []
        # loop through query set
        for notif in notifications:
            # get person who triggered the notification action
            person = notif.person
            # serialize data
            _person = PersonSerializer(person)
            _person_ = _person.data
            # serialize notification object
            _notif = NotificationSerializer(notif)
            _notif_ = _notif.data
            # check if user has dp, if they do, append their dp
            if person.pfp:
                _notif_['oppfp'] = add_base(request, _person_['pfp'])
            # append extra data
            _notif_['user'] = _person_['display_name']
            _notif_['user_id'] = _person_['id']
            # append post id to notification
            if notif.type == "commented" or notif.type == "liked-post" or notif.type == "ghost-liked" or notif.type == "disliked-post" or notif.type == "shared":
                post = Post.objects.get(id = _notif_['id_item'])
                _notif_['post_id'] = post.id
                _notif_['post'] = post.post
            if notif.type == "liked-comment":
                _comment = Comment.objects.get(id = _notif_['id'])
                _notif_['post'] = _comment.comment
                _notif_['post_id'] = _comment.post.id
            # truncate notification text if one. Not all notification objects have messages appended to them. Use try and except block to prevent error
            try:            
                if len(_notif_['post']) > 150:
                    _notif_['post'] = _notif_['post'][:150] + "..."
            except:
                pass

            # append notification
            notif_list.append(_notif_)
        # construct dictionary to return
        context = {}
        context['notif'] = notif_list
        _person__ = PersonSerializer(Person.objects.get(user = request.user))
        person_data = _person__.data
        # get requesting user profile picture if they have one
        if person_data['pfp']:
            context['pfp'] = add_base(request, person_data['pfp'])
        else:
            context['pfp'] = 'None'
        # just before notifications are returned to user, mark them all as seen in database but not in context dictionary to be returned
        for _ in notifications:
            _.is_seen = True
            _.save()
        return Response(context, status=200)
    else:
        # redirect to login with error message for not authenticated users
        return Response({'err':'Sign in to view your notifications'},status=301)
@api_view(['GET'])
def join_community(request):
    # get community ID from request object and the matching community
    community_id = request.GET.get('communityId')
    community_obj = Community.objects.get(id = int(community_id))
    # get person requesting to join the community
    person = Person.objects.get(user = request.user)

    bans = Ban.objects.filter(user = person.user, community = community_obj)
    if bans:
        return Response({'err':f'You are banned from {community_obj.name}.'}, status=403)

    # if commuinty is pricate, make a reqyest and wait for mod to accept
    if community_obj.is_private == True:
        JoinRequest.objects.get_or_create(user = request.user, community = community_obj)
        return Response(status=202)
    # else join community
    else:
        PersonCommunity.objects.get_or_create(person = person, community = community_obj)
        return Response(status=200)

# accept request. Can only be done by mod
@api_view(['GET'])
def community_request(request):
    # get person approving request
    person = Person.objects.get(user = request.user)
    # get community request was sent to
    comm_id = request.GET.get('id')
    community_obj = Community.objects.get(id = comm_id )
    # get relationshop betwwen user signed in and community object. Check if user is a mod
    rel = PersonCommunity.objects.get(person = person, community = community_obj)
    # make sure only mods can access data
    if rel.isMod == False:
        return Response({'err':"you're not mod"}, status= 403)

    #accept or reject request
    item_id = int(request.GET.get('itemId'))
    action = int(request.GET.get('action'))


    try:
        # get join request
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
    

    # get remaining request and send to user
    _join_requests = JoinRequest.objects.filter(community = community_obj)
    _join_list = []
    for _ in _join_requests:
        __ = JoinRequestSerializer(_)
        ___ = __.data
        ___['username'] = User.objects.get(id = ___['user'] ).username
        _join_list.append(___)
    context = {}
    context['join_requests'] = _join_list
    # get all members
    __pc = PersonCommunity.objects.filter(community = community_obj)
    members = []
    mods = []
    for _ in __pc:
        
        _person = _.person
        _temp = PersonSerializer(_person)
        temp = _temp.data
        temp['isMod'] = _.isMod
        if _.isMod:
            mods.append(_person.id)
        if _person.pfp:
            temp['pfp'] = add_base(request, temp['pfp'])
        members.append(temp)
    # make a list of banned users
    banned = []
    bans = Ban.objects.filter(community = community_obj)
    for _ in bans:
        # get the person, serialize and append to the banned list
        _banned_person = Person.objects.get(user = _.user)
        banned_person_ = PersonSerializer(_banned_person)
        banned_person = banned_person_.data
        if _banned_person.pfp:
            banned_person['pfp'] = add_base(request, banned_person['pfp'])
        else:
            banned_person['pfp']= None
        banned.append(banned_person)
    # add all data to context
    context['members'] = members
    context['mods'] = mods
    context['banned'] = banned
    # return context
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


# create new community, accept post and get requests
@api_view(['GET', 'POST'])
def create_new_community(request):
    # check for authentication
    if not request.user.is_authenticated:
        return Response({'err': 'Sign in to continue'}, status=301)
    # check method of request
    if request.method == 'POST':
        # get data from server and remove whitespaces
        data = request.data
        name = str(data['name']).strip()
        description = str(data['description']).strip()
        is_private = str(data['isPrivate']).strip()

        # verify name validity
        if name == "":
            return Response({'err':'Name cannot be blank'}, status= 400)
        if len(name) > 50:
            return Response("Name cannot be longer than 50 characters", status=400) # validate name length
        
        """Create community"""
        # get person creating the community
        _person = Person.objects.get(user =  request.user)
        # create community
        new_community = Community.objects.create(creator = _person, name = name)
        if is_private == 'true':
            new_community.is_private = True
        if description != "":
            new_community.description = description
        new_community.save()
        PersonCommunity.objects.create(person = _person, community = new_community, isMod = True)

        return Response({'id': new_community.id}, status=200)
    # if get, return csrf token to send post request with
    else:
        csrf = get_token(request)
        return Response({'csrf':csrf}, status=200)

"""Get footer details"""
@api_view(['GET'])
def footer_details(request):
    if not request.user.is_authenticated:
        return Response({'err':'not signed in'}, status=403)
    has_new_message = ChatUser.objects.get(user = request.user).has_new_message
    notifications = Notification.objects.filter(associated_user = request.user, is_seen = False)
    for _ in notifications:
        print(_)

    context = {}
    context['notification_count'] = len(notifications)
    context['has_new_message'] = has_new_message 
    return Response(context, status=200)

# exit community view
@api_view(['GET'])
def exit_commuity(request):
    # get person, commuity ad use it to get the perosn community object. if succesful, delete.
    _ = int(request.GET.get('communityId'))
    comm = Community.objects.get(id = _)
    _person = Person.objects.get(user = request.user)
    try:
        if _person == comm.creator:
            return Response({'err':'You cannot exit your own community.'}, status=403)
        
        PersonCommunity.objects.get(person = _person, community = comm).delete()
    except Exception as e:
        Error.objects.create(error = e)
    return Response(status=200)


# edit community details
@api_view(['POST'])
def change_community_details(request):
    name = str(request.data.get('name')).strip()
    description = str(request.data.get('description')).strip()
    privacy = str(request.data.get('isPrivate')).strip()
    if privacy == 'false':
        privacy = False
    else:
        privacy = True
    id = int(request.data.get('communityId'))
    try:
        image = request.FILES.get('pfp')
    except Exception as e:
        print(e)
    """ validate the person editing this community is a mod"""
    # get person object for user
    _person = Person.objects.get(user = request.user)
    # get community object if it exists
    try:

        _community = Community.objects.get(id = id)
    except Community.DoesNotExist:
        return Response(status=403)
    # check user belongs to this community and is mod
    try:

        _pc = PersonCommunity.objects.get(person = _person, community = _community)
    except PersonCommunity.DoesNotExist:
        return Response({'err':"You're not a member of this community"}, status=403)
    # if user is a mod, make changes
    if _pc.isMod:
        _community.name = name
        _community.is_private = privacy
        _community.pfp = image
        _community.description = description
        _community.save()
        # alert front end of success
        return Response({'msg':f'{_community.name} has been updated succesfully.'}, status=200)
    else:
        return Response({'err':"You dont have permission to do this"}, status=403)

"""Add and remove mods"""
@api_view(['GET'])
def edit_mod(request):
    # get person and comunity to edit, check if person is mod of community
    person_id =int(request.GET.get('personId'))
    community_id = int(request.GET.get('communityId'))
    _person = Person.objects.get(id = person_id)
    _community = Community.objects.get(id = community_id)
    try:
        _pc = PersonCommunity.objects.get(person = _person, community = _community)
    except PersonCommunity.DoesNotExist:
        return Response({'err':'Not a member'}, status=403)
    # get all mods and acounts
    _mods = PersonCommunity.objects.filter(community = _community, isMod = True)
    mods = len(_mods)
    # person ovject of user
    _mod_person = Person.objects.get(user = request.user)
    # if they are mod and there's an extra mod to keep running community, revoke
    if _pc.isMod:
        if mods > 1:
            if _community.creator != _pc.person:
                _pc.isMod = False
                # notify user they are no longer mod
                new_notif = Notification.objects.create(type='not_mod', message = f'revoked your moderator status at {_community.name}.', person = _mod_person, associated_user = _person.user)
            else:
                return Response({'err':f'You cannot remove {str(_community.creator).upper()} from {_community.name} as they are it\'s founder.'}, status=403)
        else:
            return Response({'err':'You can\'t delete all mods. Communities need at least one active mod to run them.'}, status=403)
    else:
        if mods < 10:
            _pc.isMod = True
            new_notif = Notification.objects.create(type='is_mod', message = f'made you a moderator at {_community.name}.', person = _mod_person, associated_user = _person.user)
        else:
            return Response({'err':'Community cannnot have more than 10 mods,'}, status= 403)
        
    _pc.save()
    new_notif.save()
    return Response(status=200)

"""Ban user from community
Fucntion that takes in a user and community and bans the user from the community permanently.
It creates a Banned object in memory that stores community details and user details and deletes the personcommunity object
that links said user to community..
WHen user tries to rejoin, join function checks for ban objects. Since it exists, It rejects their join requests
"""
@api_view(['GET'])
def ban_from_community(request):
    print(request.GET)
    # get person id from request object
    _person_id = int(request.GET.get('userId'))
    _comm_id = int(request.GET.get('commId'))
    # confirm authentication
    if not request.user.is_authenticated:
        return Response({'err':'There\'s been an issue with your authentication. Log in again to reconfirm your identity.'}, status=403)
    # get user
    _person = Person.objects.get(id = _person_id)
    # get community
    _community = Community.objects.get(id = _comm_id)
    # make sure the user being banned is not community creator
    if _person == _community.creator:
        return Response({'err':f'{str(_person.display_name).upper()} cannot be banned from {_community.name} as they are the founder.'},status=403)

    """Remove and ban user"""
    # ban user
    ban_obj, created = Ban.objects.get_or_create(user = _person.user, community = _community)
    _pcs = PersonCommunity.objects.filter(person = _person, community = _community)
    for _ in _pcs:
        _.delete()
    ban_obj.save()
    # alert user of their ban
    Notification.objects.create(type='banned', message= f'You have been banned from {_community.name}', person = _person, associated_user = _person.user)
    return Response(status=200)

"""
Function to unban user
This function takes in a community id and user id
It first confirm authentication and permissions
If all is well, recreate the person to community object and delete their ban object
"""
@api_view(['GET'])
def lift_ban(request):
    # extract parameters
    comm_id = int(request.GET.get('communityId'))
    person_id = int(request.GET.get('userId'))

    # confirm authentication
    if not request.user.is_authenticated:
        return Response({'err':'Error, you need to log in'},status=403)
    
    # confirm user is a mod
    _requesting_person = Person.objects.get(user = request.user)
    _community = Community.objects.get(id = comm_id)
    print(_requesting_person, _community)

    _pc = PersonCommunity.objects.get(person = _requesting_person, community = _community )
    print(_pc, _pc.isMod)
    if not _pc.isMod:
        return Response({'err':'You\'re not a moderator'}, status=403)
    _person_to_unban = Person.objects.get(id = person_id)
    _new_pc, created = PersonCommunity.objects.get_or_create(person = _person_to_unban , community = _community)
    _ban_objs = Ban.objects.filter( user = _person_to_unban.user ,community = _community)
    new_notif = Notification.objects.create(type='unban', message=f'lifted your ban at "{_community.name}".', person = _requesting_person, associated_user = _person_to_unban.user)
    for _ in _ban_objs:
        _.delete()
    _new_pc.save()
    return Response(status=200)
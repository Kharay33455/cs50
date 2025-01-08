# Import django modules
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
#Store data about user. Data already included in USer model is excluded
class Person(models.Model):
    # user object to refer to user
    user = models.OneToOneField(User, on_delete=models.CASCADE) # get user model
    # data about user
    display_name = models.CharField(max_length=30) #dislay name, different from username
    pfp = models.ImageField(upload_to='pfp/', blank=True, null= True) # profile picture
    bio = models.CharField(max_length=200, blank=True, null=True) # bio of user
    # user last known location. Can be null. Needs to be provided to find communities near user
    long = models.FloatField( blank=True, null=True)
    lat = models.FloatField(max_length=10, blank=True, null=True)
    # track if users has seen their new notifications
    #return username to allow identification in admin panel and print statements
    def __str__(self):
        return self.user.username


# class to store community details
class Community(models.Model):
    creator = models.ForeignKey(Person, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    is_private = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    pfp = models.ImageField(upload_to='community_pfp/', blank= True, null= True)

    def __str__(self):
        return f'{self.name} by {self.creator}'



# Store info about a single post
class Post(models.Model):
    op = models.ForeignKey(User, on_delete=models.CASCADE) # The user who made the post
    post = models.TextField(blank=True, null=True) # The post text
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    #Post pictures/ videos. All optional
    media1 = models.FileField(blank=True, null=True, upload_to='medias/') 
    media2 = models.FileField(blank=True, null=True, upload_to='medias/') 
    media3 = models.FileField(blank=True, null=True, upload_to='medias/')
    media4 = models.FileField(blank=True, null=True, upload_to='medias/')
    # reaction count
    likes = models.BigIntegerField(default=0)
    frowns = models.BigIntegerField(default=0)
    ghost_likes = models.BigIntegerField(default=0)
    comments = models.BigIntegerField(default=0)
    shares = models.BigIntegerField(default=0)
    isPrivate = models.BooleanField(default=True) # who can see post? community members or anyone?
    # Total interactions of any kind
    interactions = models.BigIntegerField(default=0)
    # Date posted
    posted = models.DateTimeField(auto_now_add=True)
    # Last date edited
    updated = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.op.username}'s post"
    
# Allegiance of users to post. A user can only have one of three(like, frown or ghost)
class Allegiance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # user
    post = models.ForeignKey(Post, on_delete=models.CASCADE) # the post
    # like, comment, dislike, ghost
    allegiance = models.CharField(max_length = 10, default=None, blank=True, null=True) # user's allegiance
    shared = models.BooleanField(default=False) # check if user has shared this post

    def __str__(self):
        return f'{self.user.username} allegiance to {self.post}'

# Model single comment    
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Who made the comment
    post = models.ForeignKey(Post, on_delete = models.CASCADE) # What post was commented on
    comment = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}\'s comment on {self.post.op.username}\'s post.'

class PersonCommunity(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    isMod = models.BooleanField(default=False) # are they a mod?
    joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.person} to {self.community} object'
    
class Notification(models.Model):
    type = models.CharField(max_length=20)
    message = models.TextField()
    time = models.DateTimeField(auto_now_add=True)
    # person interracting with post
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    # owner of post
    associated_user = models.ForeignKey(User, on_delete=models.CASCADE)
    id_item = models.IntegerField(blank = True, null= True)
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.type} notification object for {self.person}'

# request objects to join new community
class JoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    time_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} request to join {self.community.name}'
    
# Model to save unexpected errors
class Error(models.Model):
    error = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.error} on {self.date}'

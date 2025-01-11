from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Person)
admin.site.register(Post)
admin.site.register(Community)
admin.site.register(PersonCommunity)
admin.site.register(Notification)
admin.site.register(JoinRequest)
admin.site.register(Error)
admin.site.register(Ban)
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat, name='chat'),
    path('show', views.show_chat, name='show'),
    path('send-message', views.send_message, name='send-message'),
    path('new-post', views.new_post, name='new-post'),
] 
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat, name='chat'),
    path('show/<slug:chat_id>', views.show_chat, name='show'),
    path('send-message', views.send_message, name='send-message'),
    path('new-post', views.new_post, name='new-post'),
    path('new-message', views.new_chat, name='new_message'),
    path('delete-chat', views.delete_chat, name='delete_chat'),
    path('community-chat', views.community_chats, name='comm-chats'),
    path('comm-messages', views.get_messages_for_community, name='chat-messages'),
] 
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
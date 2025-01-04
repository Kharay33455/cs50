from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('person', views.get_person, name='get_person'),
    path('', views.base, name='base'),
    path('test/', views.bases, name='bases'),
    path('login', views.login_request, name='login'),
    path('logout', views.logout_request, name='logout'),
    path('allegiance', views.allegiances, name='allegiance'),
    path('post_extension', views.extend_post, name='extend_post'),
    path('comment', views.add_comment, name='comment'),
    path('community', views.community, name='community'),
    path('get-community-posts', views.get_post_by_community, name='getcps'),
    path('get-notifs', views.get_notifications, name='getnotifs'),
    path('join-community', views.join_community, name='join-community'),
    path('community-req', views.community_request, name='community-req'),
    path('register', views.register_request, name='register'),
    path('update-person', views.update_person, name='update-person'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

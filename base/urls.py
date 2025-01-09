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
    path('join-community', views.join_community, name='join_community'),
    path('community-req', views.community_request, name='community_req'),
    path('register', views.register_request, name='register'),
    path('update-person', views.update_person, name='update_person'),
    path('new-community', views.create_new_community, name='new_community'),
    path('footer-details', views.footer_details, name="footer_dets"),
    path('exit-community', views.exit_commuity, name='exit_community'),
    path('change-community-details', views.change_community_details, name='change_comm_dets'),
    path('edit-mod', views.edit_mod, name='edit_mod'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

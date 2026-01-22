from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('create/', views.create_post, name='create_post'),
    path('post/<uuid:pk>/', views.post_detail, name='post_detail'),
    path('post/<uuid:pk>/like/', views.like_post, name='like_post'),
    path('post/<uuid:pk>/comment/', views.add_comment, name='add_comment'),

    # Static Pages
    path('about/', views.static_page, {'page_name': 'about'}, name='about'),
    path('mission/', views.static_page, {'page_name': 'mission'}, name='mission'),
    path('faq/', views.static_page, {'page_name': 'faq'}, name='faq'),
    path('legal/', views.static_page, {'page_name': 'legal'}, name='legal'),
    path('security/', views.static_page, {'page_name': 'security'}, name='security'),
    path('safety/', views.static_page, {'page_name': 'safety'}, name='safety'),
]

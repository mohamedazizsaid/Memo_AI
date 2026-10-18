from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_media, name='media-upload'),
    path('<uuid:pk>/delete/', views.delete_media, name='media-delete'),
    path('entry/<uuid:entry_id>/', views.entry_media, name='entry-media'),
    path('gallery/', views.user_gallery, name='user-gallery'),
]

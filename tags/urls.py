from django.urls import path
from . import views

urlpatterns = [
    path('', views.TagListCreateView.as_view(), name='tag-list-create'),
    path('<uuid:pk>/', views.TagDetailView.as_view(), name='tag-detail'),
    path('<uuid:pk>/memories/', views.tag_memories, name='tag-memories'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.PersonListView.as_view(), name='person-list'),
    path('<uuid:pk>/', views.PersonDetailView.as_view(), name='person-detail'),
    path('<uuid:pk>/memories/', views.person_memories, name='person-memories'),
    path('<uuid:pk>/merge/', views.merge_persons, name='person-merge'),
    path('faces/<uuid:detection_id>/assign/', views.assign_face, name='face-assign'),
]

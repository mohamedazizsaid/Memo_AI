from django.urls import path
from . import views

urlpatterns = [
    path('entries/<uuid:entry_id>/', views.ai_analysis_detail, name='ai-analysis-detail'),
    path('entries/<uuid:entry_id>/retrigger/', views.retrigger_ai, name='ai-retrigger'),
    path('entries/<uuid:entry_id>/generate-image/', views.generate_image_for_entry, name='ai-generate-image'),
]

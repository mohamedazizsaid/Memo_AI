from django.urls import path
from . import insight_views

urlpatterns = [
    path('sentiment/', insight_views.sentiment_timeline, name='insights-sentiment'),
    path('keywords/', insight_views.top_keywords, name='insights-keywords'),
    path('moods/', insight_views.mood_distribution, name='insights-moods'),
    path('locations/', insight_views.top_locations, name='insights-locations'),
    path('activity/', insight_views.writing_activity, name='insights-activity'),
    path('weekly-summary/', insight_views.weekly_summary_insight, name='insights-weekly'),
    path('people/', insight_views.top_people, name='insights-people'),
]

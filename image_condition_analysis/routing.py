from django.urls import path, re_path
from image_condition_analysis import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/analysis-progress/$",
        consumers.AnalysisProgressConsumer.as_asgi(),
    ),
]

from django.urls import include, path
from image_condition_analysis import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"image-condition-analyses", views.ImageConditionAnalysisViewSet)
router.register(r"overall-image-analyses", views.OverallImageAnalysisViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("update-prompt/", views.PromptUpdateView.as_view(), name="update-prompt"),
    path("get-prompt/", views.GetPromptView.as_view(), name="get-prompt"),
    path("analyze/", views.AnalysisView.as_view(), name="analyze"),
]

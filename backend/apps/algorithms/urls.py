from django.urls import path

from .views import AlgorithmOverviewView, CashChangeSuggestionView

app_name = "algorithms"

urlpatterns = [
    path("algorithms/overview/", AlgorithmOverviewView.as_view(), name="overview"),
    path("algorithms/change/", CashChangeSuggestionView.as_view(), name="change"),
]

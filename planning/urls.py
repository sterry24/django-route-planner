from django.urls import path

from . import views

app_name = 'planning'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('new/', views.ride_create, name='create'),
    path('<int:pk>/', views.ride_detail, name='detail'),
    path('<int:pk>/edit/', views.ride_edit, name='edit'),
    path('<int:pk>/delete/', views.ride_delete, name='delete'),
    path('<int:pk>/wind/', views.ride_wind, name='wind'),
]

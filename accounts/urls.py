from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
    path('signup/', views.signup_view, name='signup'),
    path('rwgps/connect/', views.rwgps_connect, name='rwgps_connect'),
    path('rwgps/callback/', views.rwgps_callback, name='rwgps_callback'),
    path('rwgps/disconnect/', views.rwgps_disconnect, name='rwgps_disconnect'),
]

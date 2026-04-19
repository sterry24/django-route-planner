from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
    path('signup/', views.signup_view, name='signup'),
]

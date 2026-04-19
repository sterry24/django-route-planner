from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='routes:list', permanent=False)),
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('routes/', include('routes.urls', namespace='routes')),
    path('planning/', include('planning.urls', namespace='planning')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
]

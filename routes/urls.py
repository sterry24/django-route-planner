from django.urls import path

from . import views

app_name = 'routes'

urlpatterns = [
    path('', views.route_list, name='list'),
    path('new/', views.route_create, name='create'),
    path('save/', views.route_save, name='save'),
    path('import/', views.route_import, name='import'),
    path('rwgps/import/', views.rwgps_import, name='rwgps_import'),
    path('osrm/', views.osrm_proxy, name='osrm'),
    path('<int:pk>/', views.route_detail, name='detail'),
    path('<int:pk>/edit/', views.route_edit, name='edit'),
    path('<int:pk>/delete/', views.route_delete, name='delete'),
    path('<int:pk>/geojson/', views.route_geojson, name='geojson'),
    path('<int:pk>/wind/', views.route_wind, name='wind'),
    path('<int:pk>/export/<str:fmt>/', views.route_export, name='export'),
]

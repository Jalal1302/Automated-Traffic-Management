from django.urls import path
from . import views 

urlpatterns = [
    path('', views.home, name='home'),
    path('addroads/', views.add_roads, name = 'addroads'),
    path('getroads/', views.get_roads, name = 'getroads'),
    path('register/', views.add_vehicle, name = 'register'),
    path('addjunction/', views.add_junction, name = 'addjunction'),
    path('getjunction/', views.get_junctions, name = 'getjunction'),
    path('logvehicle/', views.log_vehicle_at_junction, name = 'logvehicle'),
    path('trafficanalysis/', views.get_traffic_analysis, name = 'trafficanalysis'),
]
from django.urls import path
from . import views 

urlpatterns = [
    path('', views.home, name='home'),
    path('addvehicle/', views.add_vehicle, name='addvehicle'),
    path('addroads/', views.add_roads, name = 'addroads'),
    path('getroads/', views.get_roads, name = 'getroads'),
    path('addjunction/', views.add_junction, name = 'addjunction'),
    path('getjunctions/', views.get_junctions, name = 'getjunctions'),
    path('logvehicle/', views.log_vehicle_at_junction, name = 'logvehicle'),
    path('parkingfine/',views.parking_fine, name = 'parkingfine'),
    path('violatorlist/',views.vehicles_with_violations,name = 'violatorlist'),
    path('trafficanalysis/',views.get_traffic_analysis, name ='trafficanalysis'), 
    path('analyzecongestion/',views.analyze_congestion,name = 'analyzecongestion'),
    path('speedingviolation/', views.speeding_violation, name='speedingviolation'),
    path('getprediction/', views.predict_and_suggest_routes, name = 'getprediction'),
    
]
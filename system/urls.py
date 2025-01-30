from django.urls import path
from . import views 

urlpatterns = [
    path('home/', views.home, name='home'),
    path('registervehicle/', views.register_vehicle, name='registervehicle'),
    path('addroads/', views.add_roads, name = 'addroads'),
    path('getroads/', views.get_roads, name = 'getroads'),
    
    

]

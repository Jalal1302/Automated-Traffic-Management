from django.db import models

# Create your models here.

class Vehicle(models.Model):
    number_plate = models.CharField(max_length= 10)
    owner_name = models.CharField (max_length= 100)
    vehicle_type = models.CharField(max_length= 10)
    registration_date = models.DateTimeField(auto_now_add= True)
class Junction(models.Model):
    road = models.CharField(max_length= 20)
    logged_vehicles = models.CharField(max_length= 100)
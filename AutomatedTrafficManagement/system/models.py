from django.db import models

# Create your models here.

class Vehicle(models.Model):
    number_plate = models.CharField(max_length= 10)
    owner_name = models.CharField (max_length= 100)
    vehicle_type = models.CharField(max_length= 10)
    registration_date = models.DateTimeField(auto_now_add= True)

    def __str__(self):
        return self.name
    
    @classmethod
    def create(cls, number_plate, owner_name, vehicle_type, registration_date):
        vehicle = cls(number_plate=number_plate, owner_name=owner_name, vehicle_type=vehicle_type, registration_date=registration_date)
        vehicle.save
        return vehicle

class Road(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    @classmethod
    def create(cls, name):
        road = cls(name=name)
        road.save
        return road


class Junction(models.Model):
    road = models.ManyToManyField(Road)
    logged_vehicles = models.ManyToManyField(Vehicle)

    def __str__(self):
        return self.name
    
    def create(cls):
        junction = cls()
        junction.save
        return junction
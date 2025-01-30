from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class Vehicle(models.Model):
    number_plate = models.CharField(max_length=10, unique=True)
    owner_name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=10)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.number_plate} - {self.owner_name}"
    
    @classmethod
    def create(cls, number_plate, owner_name, vehicle_type):
        vehicle = cls(
            number_plate=number_plate,
            owner_name=owner_name,
            vehicle_type=vehicle_type
        )
        vehicle.save()
        return vehicle

class Road(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    @classmethod
    def create(cls, name):
        road = cls(name=name)
        road.save()
        return road

class Junction(models.Model):
    name = models.CharField(max_length=100)
    roads = models.ManyToManyField(Road)
    logged_vehicles = models.ManyToManyField(Vehicle, blank=True)

    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        if self.id:  
            if self.roads.count() < 2:
                raise ValidationError(_('A junction must connect at least 2 roads.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def create(cls, name, roads):
        if len(roads) < 2:
            raise ValidationError(_('A junction must be created with at least 2 roads.'))
        
        junction = cls(name=name)
        junction.save()
        junction.roads.set(roads)
        return junction
    
    def log_vehicle(self, vehicle):
        self.logged_vehicles.add(vehicle)
        

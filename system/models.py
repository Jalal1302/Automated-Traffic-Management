from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Sum, Q, Max
from django.db.models.functions import Cast
from django.db.models import FloatField
from django.http import JsonResponse
import json

class Vehicle(models.Model):
    number_plate = models.CharField(max_length=10, unique=True)
    owner_name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=10)
    registration_date = models.DateTimeField(auto_now_add=True)
    owner_email = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.number_plate} - {self.owner_name}"
    
    @classmethod
    def create(cls, number_plate, owner_name, vehicle_type,owner_email):
        vehicle = cls(
            number_plate=number_plate,
            owner_name=owner_name,
            vehicle_type=vehicle_type,
            owner_email=owner_email
        )
        vehicle.save()
        return vehicle

class Road(models.Model):
    LIGHT_STATUS = [
        ('RED', 'Red Light'),
        ('GREEN', 'Green Light')
    ]
    
    name = models.CharField(max_length=100, unique=True)
    light_status = models.CharField(max_length=5, choices=LIGHT_STATUS, default='RED')
    last_status_change = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name
    
    @property
    def current_light_status(self):

        time_elapsed = timezone.now() - self.last_status_change
        seconds_elapsed = time_elapsed.total_seconds()
        
        cycles = int(seconds_elapsed // 30)
        if cycles > 0:

            self.last_status_change = self.last_status_change + timedelta(seconds=(cycles * 30))
            
            if cycles % 2 == 1:  
                self.light_status = 'GREEN' if self.light_status == 'RED' else 'RED'
            self.save()
            
        return self.light_status
    
    @classmethod
    def create(cls, name):
        road = cls(name=name)
        road.save()
        return road


class Junction(models.Model):
    name = models.CharField(max_length=100)
    roads = models.ManyToManyField(Road)
    logged_vehicles = models.ManyToManyField(Vehicle, through='JunctionVehicleLog', blank=True)
    last_status_change = models.DateTimeField(default=timezone.now)
    
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
    
    def update_light_statuses(self):

        time_elapsed = timezone.now() - self.last_status_change
        seconds_elapsed = time_elapsed.total_seconds()
        
        # Check if 30 seconds have passed
        cycles = int(seconds_elapsed // 30)
        if cycles > 0:
            roads = list(self.roads.all())
            current_time = timezone.now()
            
            # For 2 roads
            if len(roads) == 2:
                # If odd number of cycles, swap the statuses
                if cycles % 2 == 1:
                    roads[0].light_status = 'GREEN' if roads[0].light_status == 'RED' else 'RED'
                    roads[1].light_status = 'RED' if roads[1].light_status == 'GREEN' else 'GREEN'
                    roads[0].last_status_change = current_time
                    roads[1].last_status_change = current_time
                    roads[0].save()
                    roads[1].save()
            
            self.last_status_change = current_time
            self.save()
    
    def get_roads_status(self):

        self.update_light_statuses()
        return {
            road.name: road.light_status 
            for road in self.roads.all()
        }
    
    @classmethod
    def create(cls, name, roads):
        if len(roads) < 2:
            raise ValidationError(_('A junction must be created with at least 2 roads.'))
        
        junction = cls(name=name)
        junction.save()
        
        # Set initial light statuses for the roads
        for i, road in enumerate(roads):
            road.light_status = 'GREEN' if i == 0 else 'RED'
            road.last_status_change = timezone.now()
            road.save()
        
        junction.roads.set(roads)
        return junction
    
    def log_vehicle(self, vehicle, entry_road):
        log = JunctionVehicleLog.objects.create(
            junction = self,
            vehicle = vehicle,
            entry_road = entry_road,
        )

        TrafficAnalytics.record_traffic(self, log.timestamp)
        return log
        
class Violation(models.Model):
    VIOLATION_TYPES = [
        ('RED_LIGHT', 'Running Red Light'),
        ('SPEEDING', 'Speeding'),
        ('PARKING', 'Parking Violation')
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High')
    ]
    
    BASE_FINES = {
        'RED_LIGHT': 300,
        'SPEEDING': 250,
        'PARKING': 100
    }
    
    SEVERITY_MULTIPLIERS = {
        'LOW': 1.0,
        'MEDIUM': 1.5,
        'HIGH': 2.0
    }
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='violations')
    violation_type = models.CharField(max_length=20, choices=VIOLATION_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    timestamp = models.DateTimeField(auto_now_add=True)
    junction = models.ForeignKey(Junction, on_delete=models.CASCADE, related_name='violations', null=True, blank=True)
    description = models.TextField(blank=True)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def calculate_fine(self):
        base_fine = self.BASE_FINES[self.violation_type]
        multiplier = self.SEVERITY_MULTIPLIERS[self.severity]
        return base_fine * multiplier
    
    def save(self, *args, **kwargs):
        if not self.fine_amount:
            self.fine_amount = self.calculate_fine()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.vehicle.number_plate} - {self.get_violation_type_display()} ({self.get_severity_display()})"
    
    @classmethod
    def create(cls, vehicle, violation_type, severity, junction=None, description=''):
        violation = cls(
            vehicle=vehicle,
            violation_type=violation_type,
            severity=severity,
            junction=junction,
            description=description
        )

        violation.save()
        return violation

class JunctionVehicleLog(models.Model):
    junction = models.ForeignKey('Junction', on_delete=models.CASCADE)
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE)
    entry_road = models.ForeignKey('Road', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class TrafficAnalytics(models.Model):
    junction = models.ForeignKey('Junction', on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    hour = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])
    vehicle_count = models.IntegerField(default=0)
    peak_status = models.BooleanField(default=False)  # Flag for peak hours
    
    class Meta:
        unique_together = ['junction', 'date', 'hour']
        
    @classmethod
    def record_traffic(cls, junction, timestamp):
        """Record traffic count for a specific hour"""
        date = timestamp.date()
        hour = timestamp.hour
        
        analytics, created = cls.objects.get_or_create(
            junction=junction,
            date=date,
            hour=hour,
            defaults={'vehicle_count': 0}
        )
        
        # Increment vehicle count
        analytics.vehicle_count += 1
        
        
        analytics.peak_status = analytics.vehicle_count > 4
        analytics.save()
        
        return analytics

    @classmethod
    def get_daily_summary(cls, junction, date):
        """Get traffic summary for a specific day"""
        return cls.objects.filter(
            junction=junction,
            date=date
        ).aggregate(
            total_vehicles=Sum('vehicle_count'),
            avg_vehicles_per_hour=Avg('vehicle_count'),
            peak_hours_count=Count('id', filter=Q(peak_status=True))
        )
    
    @classmethod
    def identify_congestion_prone_areas(cls, threshold_vehicles=5, days_to_analyze=1):

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_to_analyze)
        
        # Get all junctions with their traffic data
        congestion_data = cls.objects.filter(
            date__range=[start_date, end_date]
        ).values(
            'junction__name'
        ).annotate(
            total_peak_hours=Count('id', filter=Q(vehicle_count__gt=threshold_vehicles)),
            avg_daily_vehicles=Avg('vehicle_count'),
            max_hourly_vehicles=Max('vehicle_count'),
            congestion_frequency=Count('id', filter=Q(vehicle_count__gt=threshold_vehicles)) / Cast(days_to_analyze, FloatField()) * 100
        ).order_by('-congestion_frequency')
        
        congestion_prone_areas = []
        for data in congestion_data:
            risk_level = 'LOW'
            if data['congestion_frequency'] > 75:
                risk_level = 'SEVERE'
            elif data['congestion_frequency'] > 50:
                risk_level = 'HIGH'
            elif data['congestion_frequency'] > 25:
                risk_level = 'MODERATE'
            
            congestion_prone_areas.append({
                'junction_name': data['junction__name'],
                'risk_level': risk_level,
                'stats': {
                    'total_peak_hours': data['total_peak_hours'],
                    'avg_daily_vehicles': round(data['avg_daily_vehicles'], 2),
                    'max_hourly_vehicles': data['max_hourly_vehicles'],
                    'congestion_frequency': round(data['congestion_frequency'], 2)
                }
            })
        
        return congestion_prone_areas



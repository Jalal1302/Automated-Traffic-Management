from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction
import requests
# Create your views here.


def add_roads(request):
    name = request.GET.get('name', '')
    if not name:
        return JsonResponse({"error": "Road name is required."}, status=400)
    
    try:
        road, created = Road.objects.get_or_create(name=name)
        return JsonResponse({
            "message": "Road created successfully!" if created else "Road already exists.",
            "road": {
                "name": road.name,
            }
        }, status=201 if created else 200)
    
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status = 500)
    
def get_roads(request):
    roads = Road.objects.all()
    data = [
        {
            "name": road.name,
        }
        for road in roads
    ]
    return JsonResponse(data, safe=False)

def add_junction(request):
    name = request.GET.get('name', '')
    road_names = request.GET.getlist('roads', [])  # Gets multiple road names from query params
    
    if not name:
        return JsonResponse({"error": "Junction name is required."}, status=400)
    
    if len(road_names) < 2:
        return JsonResponse({"error": "At least 2 roads are required for a junction."}, status=400)
    
    try:
        # First, get all the road objects
        roads = [Road.objects.get(name=road_name) for road_name in road_names]
        
        # Create the junction
        junction = Junction.create(name=name, roads=roads)
        
        return JsonResponse({
            "message": "Junction created successfully!",
            "junction": {
                "name": junction.name,
                "roads": [road.name for road in junction.roads.all()]
            }
        }, status=201)
    
    except Road.DoesNotExist:
        return JsonResponse({"error": "One or more roads do not exist."}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

def get_junctions(request):
    junctions = Junction.objects.all()
    data = [
        {
            "name": junction.name,
            "roads": [road.name for road in junction.roads.all()],
            "logged_vehicles": [vehicle.number_plate for vehicle in junction.logged_vehicles.all()]
        }
        for junction in junctions
    ]
    return JsonResponse(data, safe=False)

def log_vehicle_at_junction(request):
    junction_name = request.GET.get('junction', '')
    vehicle_plate = request.GET.get('vehicle', '')
    
    if not junction_name:
        return JsonResponse({"error": "Junction name is required."}, status=400)
    
    if not vehicle_plate:
        return JsonResponse({"error": "Vehicle number plate is required."}, status=400)
    
    try:
        # Get the junction and vehicle objects
        junction = Junction.objects.get(name=junction_name)
        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
        
        # Log the vehicle at the junction
        junction.log_vehicle(vehicle)
        
        return JsonResponse({
            "message": "Vehicle logged successfully!",
            "junction": {
                "name": junction.name,
                "vehicle": vehicle.number_plate
            }
        }, status=200)
    
    except Junction.DoesNotExist:
        return JsonResponse({"error": "Junction does not exist."}, status=404)
    except Vehicle.DoesNotExist:
        return JsonResponse({"error": "Vehicle does not exist."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

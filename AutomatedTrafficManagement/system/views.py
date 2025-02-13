from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction, JunctionVehicleLog, Violation
import requests

# Create your views here.



def home(request):
    return render (request, 'home.html')


def add_vehicle(request):
    number_plate = request.GET.get('plate', '')
    owner_name = request.GET.get('owner', '')
    vehicle_type = request.GET.get('type', '')
    owner_email = request.GET.get('email', '')
    if not number_plate:
        return JsonResponse({"error": "Vehicle plate number is required."}, status=400)
    if not owner_name:
        return JsonResponse({"error": "Owner name is required."}, status=400)
    if not vehicle_type:
        return JsonResponse({"error": "Vehicle type is required."}, status=400)
    if not owner_email:
        return JsonResponse({"error": "Owner Email is requried."}, status=400)

    try:
        vehicle, created = Vehicle.objects.get_or_create(number_plate=number_plate, owner_name=owner_name, vehicle_type=vehicle_type,owner_email=owner_email)
        return JsonResponse({
            "message": "Vehicle registered successfully!" if created else "Vehicle already registered.",
            "Vechicle": {
                "Plate": vehicle.number_plate,
                "Owner": vehicle.owner_name,
                "Type": vehicle.vehicle_type,
                "Email": vehicle.owner_email
            }
        }, status=201 if created else 200)
    
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status = 500)
    

def add_roads(request):
    name = request.GET.get('name', '')
    if not name:
        return JsonResponse({"error": "Road name is required."}, status=400)
    
    try:
        road, created = Road.objects.get_or_create(name=name)
        return render(request,"addroads.html",{
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
            "logged_vehicles": [
                {
                    "plate": log.vehicle.number_plate,
                    "entry_road": log.entry_road.name,
                    "timestamp": log.timestamp
                }
                for log in JunctionVehicleLog.objects.filter(junction=junction)
            ]
        }
        for junction in junctions
    ]
    return JsonResponse(data, safe=False)



def log_vehicle_at_junction(request):
    junction_name = request.GET.get('junction', '')
    vehicle_plate = request.GET.get('vehicle', '')
    entry_road_name = request.GET.get('entry_road', '')
    
    if not junction_name:
        return JsonResponse({"error": "Junction name is required."}, status=400)
    
    if not vehicle_plate:
        return JsonResponse({"error": "Vehicle number plate is required."}, status=400)
    
    if not entry_road_name:
        return JsonResponse({"error": "Entry road name is required."}, status=400)
    
    try:
        # Get the junction and vehicle objects
        junction = Junction.objects.get(name=junction_name)
        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
        entry_road = Road.objects.get(name=entry_road_name)

        if not junction.roads.filter(id=entry_road.id).exists():
            return JsonResponse({
                "error": f"Road '{entry_road_name}' is not connected to junction '{junction_name}'."
            }, status=400)
        

        if entry_road.current_light_status == 'RED':
            violation = Violation.create(
                vehicle=vehicle,
                violation_type='RED_LIGHT',
                severity='HIGH',
                junction=junction,
                description=f"Vehicle ran red light at {entry_road.name} entering {junction.name} junction"
            )

        
        # Log the vehicle at the junction
        junction.log_vehicle(vehicle, entry_road)
        
        response_data = {
            "message": "Vehicle logged successfully!",
            "junction": {
                "name": junction.name,
                "vehicle": vehicle.number_plate,
                "entry_road": entry_road.name,
                "light_status": entry_road.current_light_status
            }
        }
        
        # Add violation information if a red light was run
        if entry_road.current_light_status == 'RED':
            response_data["violation"] = {
                "type": "RED_LIGHT",
                "severity": "HIGH",
                "fine_amount": float(violation.fine_amount),
                "description": violation.description
            }
            response_data["message"] = "Vehicle logged successfully, but violation recorded for running red light!"
            
        return JsonResponse(response_data, status=200)


    
    except Junction.DoesNotExist:
        return JsonResponse({"error": "Junction does not exist."}, status=404)
    except Vehicle.DoesNotExist:
        return JsonResponse({"error": "Vehicle does not exist."}, status=404)
    except Road.DoesNotExist:
        return JsonResponse({"error": "Entry road does not exist."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

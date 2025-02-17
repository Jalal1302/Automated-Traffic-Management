from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction, JunctionVehicleLog, Violation, TrafficAnalytics, TrafficPrediction
import requests
from datetime import datetime
from django.utils import timezone

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


def get_traffic_analysis(request):
    
    junction_name = request.GET.get('junction', '')
    date_str = request.GET.get('date', '')
    
    # Check if junction name was provided
    if not junction_name:
        return JsonResponse({
            "error": "Junction name is required.",
            "details": "Please provide a junction name in the query parameters."
        }, status=400)
    
    # Check if date was provided
    if not date_str:
        return JsonResponse({
            "error": "Date is required.",
            "details": "Please provide a date in YYYY-MM-DD format."
        }, status=400)
    
    try:
        # Try to get the junction
        try:
            junction = Junction.objects.get(name=junction_name)
        except Junction.DoesNotExist:
            return JsonResponse({
                "error": "Junction not found.",
                "details": f"No junction exists with the name '{junction_name}'. Please check the junction name and try again."
            }, status=404)
        
        # Try to parse the date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                "error": "Invalid date format.",
                "details": "Date must be in YYYY-MM-DD format. For example: 2025-02-13"
            }, status=400)
        
        # Get hourly counts
        hourly_data = TrafficAnalytics.objects.filter(
            junction=junction,
            date=date
        ).values('hour', 'vehicle_count')
        
        # Check if any data exists for this date
        if not hourly_data.exists():
            return JsonResponse({
                "error": "No data available.",
                "details": f"No traffic data found for junction '{junction_name}' on {date_str}"
            }, status=404)
        
        # Get daily summary
        summary = TrafficAnalytics.get_daily_summary(junction, date)
        
        return JsonResponse({
            'junction': junction_name,
            'date': date_str,
            'hourly_data': list(hourly_data),
            'daily_summary': summary
        })
        
    except Exception as e:
        return JsonResponse({
            "error": "An unexpected error occurred.",
            "details": str(e)
        }, status=500)


def analyze_congestion(request):

    try:
        days = int(request.GET.get('days', 1))
        threshold = int(request.GET.get('threshold', 5))
        
        if days <= 0:
            return JsonResponse({
                "error": "Invalid days parameter",
                "details": "Days must be a positive number"
            }, status=400)
            
        if threshold <= 0:
            return JsonResponse({
                "error": "Invalid threshold parameter",
                "details": "Threshold must be a positive number"
            }, status=400)
        
        congestion_analysis = TrafficAnalytics.identify_congestion_prone_areas(
            threshold_vehicles=threshold,
            days_to_analyze=days
        )
        
        if not congestion_analysis:
            return JsonResponse({
                "message": "No congestion data available for the specified period",
                "data": []
            })
        
        return JsonResponse({
            "message": "Congestion analysis completed successfully",
            "analysis_period": f"Last {days} days",
            "congestion_threshold": f"{threshold} vehicles per hour",
            "data": congestion_analysis
        })
        
    except ValueError as e:
        return JsonResponse({
            "error": "Invalid parameter",
            "details": str(e)
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            "error": "An unexpected error occurred",
            "details": str(e)
        }, status=500)

def predict_and_suggest_routes(request):
    """
    API endpoint to get congestion predictions and alternate routes.
    """
    start_junction_name = request.GET.get('start_junction')
    end_junction_name = request.GET.get('end_junction')
    
    if not start_junction_name or not end_junction_name:
        return JsonResponse({
            "error": "Both start and end junction names are required."
        }, status=400)
    
    try:
        start_junction = Junction.objects.get(name=start_junction_name)
        end_junction = Junction.objects.get(name=end_junction_name)
        current_time = timezone.now()
        
        # Get congestion prediction for start junction
        congestion_prediction = TrafficPrediction.predict_congestion(
            start_junction,
            current_time
        )
        
        # Get alternate routes
        alternate_routes = TrafficPrediction.get_alternate_routes(
            start_junction,
            end_junction,
            current_time
        )
        
        return JsonResponse({
            "start_junction": start_junction_name,
            "end_junction": end_junction_name,
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "congestion_prediction": congestion_prediction,
            "alternate_routes": alternate_routes
        })
        
    except Junction.DoesNotExist:
        return JsonResponse({
            "error": "One or both junctions not found."
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "error": f"An unexpected error occurred: {str(e)}"
        }, status=500)


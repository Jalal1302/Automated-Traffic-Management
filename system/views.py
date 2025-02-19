from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction, JunctionVehicleLog, Violation, TrafficAnalytics
import requests
from datetime import datetime
from django.utils import timezone
from django.core.mail import send_mail
# Create your views here.


def send_test_email():
    send_mail(
        'Test Subject',  # Subject
        'This is a test email.',  # Message body
        'jaka.mamedov@gmail.com',  # From email
        ['calalm2002@gmail.com'],  # To email list
        fail_silently=False,
    )
def home(request):
    return render (request, 'home.html')


def add_vehicle(request):
    number_plate = request.GET.get('plate', '')
    owner_name = request.GET.get('owner', '')
    vehicle_type = request.GET.get('type', '')
    owner_email = request.GET.get('email', '')
    if not number_plate:
        return render(request,"addvehicle.html",{"error": "Vehicle plate number is required."}, status=400)
    if not owner_name:
        return render(request,"addvehicle.html",{"error": "Owner name is required."}, status=400)
    if not vehicle_type:
        return render(request,"addvehicle.html",{"error": "Vehicle type is required."}, status=400)
    if not owner_email:
        return render(request,"addvehicle.html",{"error": "Owner Email is requried."}, status=400)

    try:
        vehicle, created = Vehicle.objects.get_or_create(number_plate=number_plate, owner_name=owner_name, vehicle_type=vehicle_type,owner_email=owner_email)
        return render(request, "addvehicle.html",{
            "message": "Vehicle registered successfully!" if created else "Vehicle already registered.",
            "Vechicle": {
                "Plate": vehicle.number_plate,
                "Owner": vehicle.owner_name,
                "Type": vehicle.vehicle_type,
                "Email": vehicle.owner_email
            }
        })
    
    except Exception as e:
        return render(request,"addvehicle.html",{"error": f"An error occurred: {str(e)}"}, status = 500)
    

def add_roads(request):
    name = request.GET.get('name', '')
    if not name:
        return render(request,"addroads.html",{"error": "Road name is required."}, status=400)
    
    try:
        road, created = Road.objects.get_or_create(name=name)
        return render(request,"addroads.html",{
            "message": "Road created successfully!" if created else "Road already exists.",
            "road": {
                "name": road.name,
            }
        })
    
    except Exception as e:
        return render(request,"addroads.html",{"error": f"An error occurred: {str(e)}"}, status = 500)
    
def get_roads(request):
    roads = Road.objects.all()
    return render(request, "getroads.html", {
        "data": {
            "roads": roads
        }
    })

def add_junction(request):
    name = request.GET.get('name', '')
    road_names = request.GET.getlist('roads', [])
    
    context = {}
    
    if not name:
        context["error"] = "Junction name is required."
        return render(request, "addjunctions.html", context)

    if not road_names:
        context["error"] = "At least one road is required."
        return render(request, "addjunctions.html", context)

    try:
        if Junction.objects.filter(name=name).exists():
            context["error"] = "Junction with this name already exists."
            return render(request, "addjunctions.html", context)

        roads = [Road.objects.get(name=road_name) for road_name in road_names]
        junction = Junction.create(name=name, roads=roads)

        context["message"] = "Junction created successfully!"
        context["junction"] = {
            "name": junction.name,
            "roads": [road.name for road in junction.roads.all()]
        }

    except Road.DoesNotExist:
        context["error"] = "One or more roads do not exist."
    except Exception as e:
        context["error"] = f"An error occurred: {str(e)}"

    return render(request, "addjunctions.html", context)


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
    return render(request, 'getjunctions.html', {'data': data})


def log_vehicle_at_junction(request):
    vehicles = Vehicle.objects.all()  # Query all vehicles
    message = None
    error = None
    violation_info = None

    if request.method == "POST":
        junction_name = request.POST.get('junction', '').strip()
        vehicle_plate = request.POST.get('vehicle', '').strip()
        entry_road_name = request.POST.get('entry_road', '').strip()

        if not junction_name:
            return render(request, "logvehicle.html", {"error": "Junction name is required.", "vehicles": vehicles}, status=400)
        
        if not vehicle_plate:
            return render(request, "logvehicle.html", {"error": "Vehicle number plate is required.", "vehicles": vehicles}, status=400)
        
        if not entry_road_name:
            return render(request, "logvehicle.html", {"error": "Entry road name is required.", "vehicles": vehicles}, status=400)
        
        try:
            # Get the junction, vehicle, and entry road from the database
            junction = Junction.objects.get(name=junction_name)
            vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
            entry_road = Road.objects.get(name=entry_road_name)

            # Check if the entry road is connected to the junction
            if not junction.roads.filter(id=entry_road.id).exists():
                return render(request, "logvehicle.html", {
                    "error": f"Road '{entry_road_name}' is not connected to junction '{junction_name}'.",
                    "vehicles": vehicles
                }, status=400)

            # Check for violations (e.g., red light violation)
            if entry_road.current_light_status == 'RED':
                violation = Violation.create(
                    vehicle=vehicle,
                    violation_type='RED_LIGHT',
                    severity='HIGH',
                    junction=junction,
                    description=f"Vehicle ran red light at {entry_road.name} entering {junction.name} junction"
                )
                violation_info = {
                    "type": "RED_LIGHT",
                    "severity": "HIGH",
                    "fine_amount": float(violation.fine_amount),
                    "description": violation.description
                }

            # Log the vehicle at the junction
            junction.log_vehicle(vehicle, entry_road)

            # Success message
            message = "Vehicle logged successfully!"

            # Add violation details if applicable
            if entry_road.current_light_status == 'RED':
                message = "Vehicle logged successfully, but violation recorded for running red light!"

            # Prepare the response data
            response_data = {
                "message": message,
                "junction": {
                    "name": junction.name,
                    "vehicle": vehicle.number_plate,
                    "entry_road": entry_road.name,
                    "light_status": entry_road.current_light_status
                }
            }

            if violation_info:
                response_data["violation"] = violation_info
                response_data["message"] = "Vehicle logged successfully, but violation recorded for running red light!"

            return render(request, "logvehicle.html", response_data, status=200)

        except Junction.DoesNotExist:
            error = "Junction does not exist."
        except Vehicle.DoesNotExist:
            error = "Vehicle does not exist."
        except Road.DoesNotExist:
            error = "Entry road does not exist."
        except Exception as e:
            error = f"An error occurred: {str(e)}"
        
        return render(request, "logvehicle.html", {"error": error, "vehicles": vehicles}, status=400)

    # If the method is not POST, render the template with the vehicle list
    return render(request, "logvehicle.html", {"vehicles": vehicles})

def parking_fine(request):
    vehicle_plate = request.GET.get('vehicle_plate', '')
    junction_name = request.GET.get('junction_name', '')
    description = request.GET.get('description', '')

    context = {}

    context["vehicle_plates"] = Vehicle.objects.all()

    if not vehicle_plate:
        context["error"] = "Vehicle number plate is required."
        return render(request, "parkingfine.html", context)

    try:
        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
    except Vehicle.DoesNotExist:
        context["error"] = "Vehicle not found."
        return render(request, "parkingfine.html", context)

    try:
        violation = Violation.create(
            vehicle=vehicle,
            violation_type='PARKING',
            severity='LOW',
            junction=None if not junction_name else Junction.objects.get(name=junction_name),
            description=description
        )

        fine_amount = violation.fine_amount
        violation_timestamp = violation.timestamp

        context["message"] = "Parking violation registered successfully."
        context["fine_amount"] = fine_amount
        context["timestamp"] = violation_timestamp

    except Junction.DoesNotExist:
        context["error"] = "Junction does not exist."
    except Exception as e:
        context["error"] = f"An error occurred: {str(e)}"

    return render(request, "parkingfine.html", context)

def speeding_violation(request):
    vehicle_plate = request.GET.get('vehicle_plate', '')
    road_name = request.GET.get('road_name', '')
    speed = request.GET.get('speed', '')
    speed_limit = request.GET.get('speed_limit', '')
    
    context = {}
    context["vehicle_plates"] = Vehicle.objects.all()
    context["roads"] = Road.objects.all()

    if not vehicle_plate:
        context["error"] = "Vehicle number plate is required."
        return render(request, "speedingviolation.html", context)

    if not road_name:
        context["error"] = "Road name is required."
        return render(request, "speedingviolation.html", context)

    if not speed or not speed_limit:
        context["error"] = "Both speed and speed limit are required."
        return render(request, "speedingviolation.html", context)

    try:
        speed = float(speed)
        speed_limit = float(speed_limit)
    except ValueError:
        context["error"] = "Speed and speed limit must be numbers."
        return render(request, "speedingviolation.html", context)

    try:
        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
        road = Road.objects.get(name=road_name)

        # Calculate severity based on how much the speed limit was exceeded
        if speed > speed_limit:
            speed_difference = speed - speed_limit
            if speed_difference > 30:
                severity = 'HIGH'
            elif speed_difference > 15:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'

            description = f"Vehicle was recorded at {speed} km/h in a {speed_limit} km/h zone on {road.name}"
            
            violation = Violation.create(
                vehicle=vehicle,
                violation_type='SPEEDING',
                severity=severity,
                junction=None,
                description=description
            )

            context["message"] = "Speeding violation registered successfully."
            context["violation"] = {
                "speed": speed,
                "speed_limit": speed_limit,
                "difference": speed_difference,
                "severity": severity,
                "fine_amount": violation.fine_amount,
                "timestamp": violation.timestamp
            }
        else:
            context["message"] = "No violation: Vehicle was within speed limit."
            context["speed_info"] = {
                "recorded_speed": speed,
                "speed_limit": speed_limit
            }

    except Vehicle.DoesNotExist:
        context["error"] = "Vehicle not found."
    except Road.DoesNotExist:
        context["error"] = "Road not found."
    except Exception as e:
        context["error"] = f"An error occurred: {str(e)}"

    return render(request, "speedingviolation.html", context)

def vehicles_with_violations(request):

    vehicles = Vehicle.objects.filter(violation__isnull=False).distinct()

    return render(request, "violatorslist.html", {"vehicles": vehicles})


def get_traffic_analysis(request):
    junction_name = request.GET.get('junction', '')
    date_str = request.GET.get('date', '')


    if not junction_name:
        return render(request, "trafficanalysis.html", {
            "error": "Junction name is required.",
            "details": "Please provide a junction name in the query parameters."
        })


    if not date_str:
        return render(request, "trafficanalysis.html", {
            "error": "Date is required.",
            "details": "Please provide a date in YYYY-MM-DD format."
        })

    try:
        try:
            junction = Junction.objects.get(name=junction_name)
        except Junction.DoesNotExist:
            return render(request, "trafficanalysis.html", {
                "error": "Junction not found.",
                "details": f"No junction exists with the name '{junction_name}'. Please check the junction name and try again."
            })

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return render(request, "trafficanalysis.html", {
                "error": "Invalid date format.",
                "details": "Date must be in YYYY-MM-DD format. For example: 2025-02-13"
            })

        hourly_data = TrafficAnalytics.objects.filter(
            junction=junction,
            date=date
        ).values('hour', 'vehicle_count')

        if not hourly_data.exists():
            return render(request, "trafficanalysis.html", {
                "error": "No data available.",
                "details": f"No traffic data found for junction '{junction_name}' on {date_str}"
            })

        summary = TrafficAnalytics.get_daily_summary(junction, date)

        return render(request, "trafficanalysis.html", {
            "junction": junction_name,
            "date": date_str,
            "hourly_data": list (hourly_data),
            "daily_summary": summary
        })

    except Exception as e:
        return render(request, "trafficanalysis.html", {
            "error": "An unexpected error occurred.",
            "details": str(e)
        })
    

def analyze_congestion(request):
    try:
        days = int(request.GET.get('days', 1))
        threshold = int(request.GET.get('threshold', 5))

        if days <= 0:
            return render(request, "analyzecongestion.html", {
                "error": "Invalid days parameter",
                "details": "Days must be a positive number"
            })
            
        if threshold <= 0:
            return render(request, "analyzecongestion.html", {
                "error": "Invalid threshold parameter",
                "details": "Threshold must be a positive number"
            })
        
        congestion_analysis = TrafficAnalytics.identify_congestion_prone_areas(
            threshold_vehicles=threshold,
            days_to_analyze=days
        )

        if not congestion_analysis:
            
            return render(request, "analyzecongestion.html", {
                "message": "No congestion data available for the specified period",
                "data": [],
            })
        if congestion_analysis:
            return render(request, "analyzecongestion.html", {
            "message": "Congestion analysis completed successfully",
            "analysis_period": f"Last {days} days",
            "congestion_threshold": f"{threshold} vehicles per hour",
            "congestion_analysis": congestion_analysis
            })
            

        
    except ValueError as e:
        return render(request, "analyzecongestion.html", {
            "error": "Invalid parameter",
            "details": str(e)
        })
        
    except Exception as e:
        return render(request, "analyzecongestion.html", {
            "error": "An unexpected error occurred",
            "details": str(e)
        })

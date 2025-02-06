from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction, Violation
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
        }, status=201 if created else 200)
    
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
    road_names = request.GET.getlist('roads', [])  # Gets multiple road names from query params
    
    if not name:
        return render(request,"addjunctions.html",{"error": "Junction name is required."}, status=400)
    
    if len(road_names) < 2:
        return render(request,"addjunctions.html",{"error": "At least 2 roads are required for a junction."}, status=400)
    
    try:
        # First, get all the road objects
        roads = [Road.objects.get(name=road_name) for road_name in road_names]
        
        # Create the junction
        junction = Junction.create(name=name, roads=roads)
        
        return render(request,"addjunctions.html",{
            "message": "Junction created successfully!",
            "junction": {
                "name": junction.name,
                "roads": [road.name for road in junction.roads.all()]
            }
        }, status=201)
    
    except Road.DoesNotExist:
        return render(request,"addjunctions.html",{"error": "One or more roads do not exist."}, status=400)
    except ValidationError as e:
        return render(request,"addjunctions.html",{"error": str(e)}, status=400)
    except Exception as e:
        return render(request,"addjunctions.html",{"error": f"An error occurred: {str(e)}"}, status=500)

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
    junction_name = request.GET.get('junction', '')
    vehicle_plate = request.GET.get('vehicle', '')
    
    if not junction_name:
        return render(request,"logvehicle.html",{"error": "Junction name is required."}, status=400)
    
    if not vehicle_plate:
        return render(request,"logvehicle.html",{"error": "Vehicle number plate is required."}, status=400)
    
    try:
        # Get the junction and vehicle objects
        junction = Junction.objects.get(name=junction_name)
        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
        
        # Log the vehicle at the junction
        junction.log_vehicle(vehicle)
        
        return render(request,"logvehicle.html",{
            "message": "Vehicle logged successfully!",
            "junction": {
                "name": junction.name,
                "vehicle": vehicle.number_plate
            }
        }, status=200)
    
    except Junction.DoesNotExist:
        return render(request,"logvehicle.html",{"error": "Junction does not exist."}, status=404)
    except Vehicle.DoesNotExist:
        return render(request,"logvehicle.html",{"error": "Vehicle does not exist."}, status=404)
    except Exception as e:
        return render(request,"logvehicle.html",{"error": f"An error occurred: {str(e)}"}, status=500)


def parking_fine(request):
    vehicle_plate = request.GET.get('vehicle_plate', '')
    junction_name = request.GET.get('junction_name', '')
    description = request.GET.get('description', '')
    severity = request.GET.get('severity', '')
    if not vehicle_plate:
        return JsonResponse({"error": "Vehicle number plate is required."}, status=400)

    try:

        vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
    except Vehicle.DoesNotExist:
        return JsonResponse({"error": "Vehicle not found."}, status=404)


    try:

        violation = Violation.create(
            vehicle=vehicle,
            violation_type='PARKING', 
            severity=severity,
            junction=None if not junction_name else Junction.objects.get(name=junction_name),
            description=description
        )

        fine_amount = violation.fine_amount
        violation_timestamp = violation.timestamp

        # send_violation_email(vehicle.owner_email, violation_timestamp, fine_amount, violation.violation_type, junction_name)

        return JsonResponse({
            "message": "Parking violation registered successfully.",
            "fine_amount": fine_amount,
        }, status=201)

    except Junction.DoesNotExist:
        return JsonResponse({"error": "Junction does not exist."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

# def send_violation_email(owner_email, violation_time, fine_amount, violation_type, junction_name):
#     """Function to send the email to the vehicle owner with violation details."""
#     subject = f"Parking Violation - Fine Notification"

#     violation_time_str = violation_time.strftime("%Y-%m-%d %H:%M:%S")
    
#     message = f"""
#     Dear Vehicle Owner,

#     You have been issued a parking violation on {violation_time_str}. 

#     Violation Type: {violation_type}
#     Fine Amount: {fine_amount} USD
#     Date and Time: {violation_time_str}
    
#     Crime Location: {junction_name if junction_name else 'Location not specified'}

#     Please ensure the payment is made within the prescribed time.

#     Thank you for your cooperation.
#     """
    
#     send_mail(
#         subject,
#         message,
#         'traffic@management.com',
#         [owner_email], 
#         fail_silently=False,
#     )

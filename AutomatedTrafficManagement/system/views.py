from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.exceptions import ValidationError
import json
from .models import Vehicle, Road, Junction, JunctionVehicleLog, Violation, TrafficAnalytics, TrafficPrediction
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
# Create your views here.



def home(request):
    return render (request, 'home.html')


def add_vehicle(request):
    vehicle_types = Vehicle.VEHICLE_TYPES
    
    if request.method == 'GET' and any(param in request.GET for param in ['plate', 'owner', 'type', 'email']):
        number_plate = request.GET.get('plate', '')
        owner_name = request.GET.get('owner', '')
        vehicle_type = request.GET.get('type', '')
        owner_email = request.GET.get('email', '')
        
        if not number_plate:
            return render(request, "addvehicle.html", {
                "error": "Vehicle plate number is required.",
                "vehicle_types": vehicle_types
            }, status=400)
        if not owner_name:
            return render(request, "addvehicle.html", {
                "error": "Owner name is required.",
                "vehicle_types": vehicle_types
            }, status=400)
        if not vehicle_type:
            return render(request, "addvehicle.html", {
                "error": "Vehicle type is required.",
                "vehicle_types": vehicle_types
            }, status=400)
        if not owner_email:
            return render(request, "addvehicle.html", {
                "error": "Owner Email is required.",
                "vehicle_types": vehicle_types
            }, status=400)

        valid_types = [type_code for type_code, _ in vehicle_types]
        if vehicle_type not in valid_types:
            return render(request, "addvehicle.html", {
                "error": "Invalid vehicle type selected.",
                "vehicle_types": vehicle_types
            }, status=400)

        try:
            vehicle, created = Vehicle.objects.get_or_create(
                number_plate=number_plate,
                defaults={
                    'owner_name': owner_name,
                    'vehicle_type': vehicle_type,
                    'owner_email': owner_email
                }
            )
            
            if not created:
                vehicle.owner_name = owner_name
                vehicle.vehicle_type = vehicle_type
                vehicle.owner_email = owner_email
                vehicle.save()
                
            return render(request, "addvehicle.html", {
                "message": "Vehicle registered successfully!" if created else "Vehicle updated successfully.",
                "vehicle": {
                    "Plate": vehicle.number_plate,
                    "Owner": vehicle.owner_name,
                    "Type": vehicle.get_vehicle_type_display(),  
                    "Email": vehicle.owner_email
                },
                "vehicle_types": vehicle_types
            })
        
        except Exception as e:
            return render(request, "addvehicle.html", {
                "error": f"An error occurred: {str(e)}",
                "vehicle_types": vehicle_types
            }, status=500)
    
    
    return render(request, "addvehicle.html", {"vehicle_types": vehicle_types})


    

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
            junction = Junction.objects.get(name=junction_name)
            vehicle = Vehicle.objects.get(number_plate=vehicle_plate)
            entry_road = Road.objects.get(name=entry_road_name)

            if not junction.roads.filter(id=entry_road.id).exists():
                return render(request, "logvehicle.html", {
                    "error": f"Road '{entry_road_name}' is not connected to junction '{junction_name}'.",
                    "vehicles": vehicles
                }, status=400)

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

            junction.log_vehicle(vehicle, entry_road)

            request.session["message"] = "Vehicle logged successfully!"
            if violation_info:
                request.session["violation"] = violation_info
                request.session["message"] = "Vehicle logged successfully, but violation recorded for running red light!"

            return redirect("logvehicle")  # Prevents duplicate form submissions

        except Junction.DoesNotExist:
            error = "Junction does not exist."
        except Vehicle.DoesNotExist:
            error = "Vehicle does not exist."
        except Road.DoesNotExist:
            error = "Entry road does not exist."
        except Exception as e:
            error = f"An error occurred: {str(e)}"

        return render(request, "logvehicle.html", {"error": error, "vehicles": vehicles}, status=400)

    # Retrieve session-stored messages after redirect and clear them
    message = request.session.pop("message", None)
    violation_info = request.session.pop("violation", None)

    return render(request, "logvehicle.html", {
        "vehicles": vehicles,
        "message": message,
        "violation": violation_info
    })





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

        if congestion_analysis:
            # Send email notifications for congested junctions
            for area in congestion_analysis:
                if area['risk_level'] in ['MODERATE', 'HIGH', 'SEVERE']:
                    # Get affected vehicles
                    junction = Junction.objects.get(name=area['junction_name'])
                    affected_vehicles = Vehicle.objects.filter(
                        junctionvehiclelog__junction=junction,
                        junctionvehiclelog__timestamp__gte=timezone.now() - timedelta(days=days)
                    ).distinct()
                    
                    # Find alternative routes
                    alternative_routes = _find_alternative_routes(junction)
                    
                    # Send notification to each vehicle owner
                    for vehicle in affected_vehicles:
                        send_congestion_email(
                            vehicle.owner_email,
                            vehicle.owner_name,
                            area,
                            junction.name,
                            alternative_routes
                        )
            
            return render(request, "analyzecongestion.html", {
                "message": "Congestion analysis completed successfully. Email notifications sent.",
                "analysis_period": f"Last {days} days",
                "congestion_threshold": f"{threshold} vehicles per hour",
                "congestion_analysis": congestion_analysis
            })
        else:
            return render(request, "analyzecongestion.html", {
                "message": "No congestion data available for the specified period",
                "data": [],
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


def send_congestion_email(email, owner_name, congestion_data, junction_name, alternative_routes):
    """Send email notification about congestion with alternative routes"""
    try:
        subject = f"Traffic Alert: Congestion at {junction_name}"
        
        message = f"""
Dear {owner_name},

We've detected significant congestion at {junction_name}.

Congestion Details:
- Risk Level: {congestion_data['risk_level']}
- Average Daily Vehicles: {congestion_data['stats']['avg_daily_vehicles']}
- Congestion Frequency: {congestion_data['stats']['congestion_frequency']}%

Suggested Alternative Routes:
"""

        for route in alternative_routes:
            message += f"- {route['route']} via {route['via']}\n"
            
        message += """
Please plan your journey accordingly.

Regards,
Traffic Management System
"""

        send_mail(
            subject,
            message,
            'laubia20@gmail.com',  # From email (use your system email)
            [email],  # To email
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
        return False


def _find_alternative_routes(congested_junction):
    """Find alternative routes to avoid congested junction"""
    # Get all roads connected to the congested junction
    congested_roads = set(congested_junction.roads.all())
    
    # Find other junctions that aren't congested
    alternative_routes = []
    
    # Get other junctions
    other_junctions = Junction.objects.exclude(id=congested_junction.id)
    
    for junction in other_junctions:
        # Simple alternative route suggestion
        alternative_routes.append({
            'route': f"Use {junction.name} junction instead",
            'via': ", ".join([road.name for road in junction.roads.all()[:2]])
        })
        
        # Limit to 3 alternative routes
        if len(alternative_routes) >= 3:
            break
            
    # If no alternatives found, suggest a generic detour
    if not alternative_routes:
        alternative_routes.append({
            'route': "Consider delaying your journey or using main highways",
            'via': "Main city bypass"
        })
        
    return alternative_routes


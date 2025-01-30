from django.shortcuts import render, redirect
from .models import Vehicle, Junction , Road
from django.http import JsonResponse
import json
import requests




def home(request):
    return render(request, 'system/home.html')
def register_vehicle(request):
    # if request.method == 'POST':
    #     number_plate = request.POST['number_plate']
    #     owner = request.POST['owner']
    #     make_model = request.POST['make_model']
    #     Vehicle.objects.create(number_plate=number_plate, owner=owner, make_model=make_model)
    #     return redirect('home')
    # return render(request, 'system/register_vehicle.html')
    name = request.GET.get('name', '')
    if not name:
        number_plate = request.GET.get('number_plate')
        owner = request.GET.get('owner')
        model = request.GET.get ('model')
        Vehicle.objects.create(number_plate = number_plate,owner = owner, model = model)
        return JsonResponse({"car was added successfuly"})
    
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
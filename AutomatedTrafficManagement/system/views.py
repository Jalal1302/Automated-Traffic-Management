from django.shortcuts import render
from django.http import JsonResponse
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
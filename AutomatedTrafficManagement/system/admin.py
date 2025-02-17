from django.contrib import admin
from .models import Vehicle, Road, Junction, Violation, JunctionVehicleLog, TrafficAnalytics
# Register your models here.

admin.site.register(Vehicle)
admin.site.register(Road)
admin.site.register(Junction)
admin.site.register(Violation)
admin.site.register(JunctionVehicleLog)
admin.site.register(TrafficAnalytics)

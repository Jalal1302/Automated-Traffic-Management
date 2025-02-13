from django.contrib import admin
from .models import Vehicle, Road, Junction, Violation
# Register your models here.

admin.site.register(Vehicle)
admin.site.register(Road)
admin.site.register(Junction)
admin.site.register(Violation)
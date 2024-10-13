# urls.py
from django.urls import path
from .views import GetData

urlpatterns = [
    path('getdata/', GetData, name='GetData'),
    # otras rutas...
]
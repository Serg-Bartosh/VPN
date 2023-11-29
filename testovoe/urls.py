from django.contrib import admin
from vpn.views import main
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', main, name='main'),
    path('account/', include('vpn.urls')),
]

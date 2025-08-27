from django.urls import path
from django.http import HttpResponse
from . import views

def hcdb_home(request):
    return HttpResponse("""
        <h1>Hominin_Characters Database</h1>
        <p><a href="/hcdb/character/">View Character</a></p>
        <p><a href="/admin/">Admin Panel</a></p>
    """)

app_name = 'hcdb'
urlpatterns = [
    path('', hcdb_home, name='home'),  # Add this line
    path('character/', views.CharacterListView.as_view(), name='character_list_view'),
    path('character/<int:pk>/', views.CharacterDetailView.as_view(), name='character_detail_view'),
]
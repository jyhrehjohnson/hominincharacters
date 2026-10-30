from django.urls import path
from . import views

app_name = 'hcdb'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Character URLs
    path('characters/', views.CharacterListView.as_view(), name='character_list'),
    path('characters/<int:pk>/', views.CharacterDetailView.as_view(), name='character_detail'),
    
    # Fossil URLs
    path('fossils/', views.FossilListView.as_view(), name='fossil_list'),
    path('fossils/<int:pk>/', views.FossilDetailView.as_view(), name='fossil_detail'),

    # Skeletal element URLs
    path('elements/', views.SkeletalElementListView.as_view(), name='element_list'),
    path('elements/<int:pk>/', views.SkeletalElementDetailView.as_view(), name='element_detail'),

    # Publication URLs
    path('publications/', views.PublicationListView.as_view(), name='publication_list'),
    path('publications/<int:pk>/', views.PublicationDetailView.as_view(), name='publication_detail'),
    
    # Browse and search
    path('browse-by-taxon/', views.browse_by_taxon, name='browse_by_taxon'),
    path('search/', views.search, name='search'),

    path('skeleton/', views.skeleton_view, name='skeleton_explorer'),
    path('api/bone/<str:uberon_id>/', views.bone_data, name='bone_data'),
]

from django.shortcuts import render
from django.http import JsonResponse
from django.views import generic
from django.db.models import Q
from .models import Character, CharacterState, Fossil, FossilCharacterState


# Home page view
def home(request):
    """Public home page with overview statistics"""
    context = {
        'total_characters': Character.objects.count(),
        'total_fossils': Fossil.objects.count(),
        'total_states': CharacterState.objects.count(),
        'taxa_list': Fossil.objects.values_list('taxon', flat=True).distinct().exclude(taxon=''),
    }
    return render(request, 'hcdb/home.html', context)


# Character views
class CharacterListView(generic.ListView):
    """List all characters with filtering options"""
    model = Character
    template_name = 'hcdb/character_list.html'
    context_object_name = 'characters'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Character.objects.all().prefetch_related('states')
        
        # Filter by anatomical region
        region = self.request.GET.get('region')
        if region:
            queryset = queryset.filter(anatomical_region=region)
        
        # Filter by character type
        char_type = self.request.GET.get('type')
        if char_type:
            queryset = queryset.filter(character_type=char_type)
        
        # Search by character name or description
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(character__icontains=search) | 
                Q(description__icontains=search) |
                Q(skeletal_element__icontains=search)
            )
        
        return queryset.order_by('character')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['regions'] = dict(Character._meta.get_field('anatomical_region').choices)
        context['char_types'] = dict(Character._meta.get_field('character_type').choices)
        context['current_region'] = self.request.GET.get('region', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class CharacterDetailView(generic.DetailView):
    """Detailed view of a single character"""
    model = Character
    template_name = 'hcdb/character_detail.html'
    context_object_name = 'character'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character = self.get_object()
        
        # Get all states for this character
        context['states'] = character.states.all().order_by('state_order', 'state_code')
        
        # Get fossils that have any of these states
        context['fossils'] = Fossil.objects.filter(
            character_states__character=character
        ).distinct().select_related().prefetch_related('character_states')
        
        return context


# Fossil views
class FossilListView(generic.ListView):
    """List all fossils with filtering options"""
    model = Fossil
    template_name = 'hcdb/fossil_list.html'
    context_object_name = 'fossils'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Fossil.objects.all().prefetch_related('character_states')
        
        # Filter by taxon
        taxon = self.request.GET.get('taxon')
        if taxon:
            queryset = queryset.filter(taxon=taxon)
        
        # Filter by anatomical region
        region = self.request.GET.get('region')
        if region:
            queryset = queryset.filter(anatomical_region=region)
        
        # Filter by element type
        element = self.request.GET.get('element')
        if element:
            queryset = queryset.filter(element_type__icontains=element)
        
        # Search by fossil ID or description
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(fossil_id__icontains=search) | 
                Q(short_description__icontains=search) |
                Q(element_type__icontains=search)
            )
        
        return queryset.order_by('fossil_id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['taxa'] = dict(Fossil._meta.get_field('taxon').choices)
        context['regions'] = dict(Fossil._meta.get_field('anatomical_region').choices)
        context['current_taxon'] = self.request.GET.get('taxon', '')
        context['current_region'] = self.request.GET.get('region', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class FossilDetailView(generic.DetailView):
    """Detailed view of a single fossil"""
    model = Fossil
    template_name = 'hcdb/fossil_detail.html'
    context_object_name = 'fossil'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fossil = self.get_object()
        
        # Get character state assignments with related data
        context['character_state_assignments'] = fossil.fossil_character_states.select_related(
            'character_state__character'
        ).order_by('character_state__character__character')
        
        return context


# Browse by taxon
def browse_by_taxon(request):
    """View to browse characters organized by taxon"""
    taxa_data = []
    
    # Get all taxa choices
    taxa_choices = dict(Fossil._meta.get_field('taxon').choices)
    
    for taxon_code, taxon_name in taxa_choices.items():
        fossils = Fossil.objects.filter(taxon=taxon_code).prefetch_related('character_states')
        if fossils.exists():
            taxa_data.append({
                'code': taxon_code,
                'name': taxon_name,
                'fossil_count': fossils.count(),
                'fossils': fossils[:5]  # Show first 5
            })
    
    context = {
        'taxa_data': taxa_data
    }
    return render(request, 'hcdb/browse_by_taxon.html', context)


# Search view
def search(request):
    """Universal search across characters and fossils"""
    query = request.GET.get('q', '')
    
    context = {
        'query': query,
        'characters': [],
        'fossils': [],
    }
    
    if query:
        # Search characters
        context['characters'] = Character.objects.filter(
            Q(character__icontains=query) |
            Q(description__icontains=query) |
            Q(skeletal_element__icontains=query)
        )[:10]
        
        # Search fossils
        context['fossils'] = Fossil.objects.filter(
            Q(fossil_id__icontains=query) |
            Q(short_description__icontains=query) |
            Q(element_type__icontains=query)
        )[:10]
    
    return render(request, 'hcdb/search.html', context)


def skeleton_view(request):
    """Render the interactive skeleton template"""
    return render(request, 'hcdb/skeleton_explorer.html')  # Note: hcdb/ prefix

def bone_data(request, uberon_id):
    """API endpoint to get bone data by Uberon ID"""
    # Get fossils with this Uberon ID
    fossils = Fossil.objects.filter(uberon_ID=uberon_id).values(
        'fossil_id', 'taxon', 'element_type', 'anatomical_region', 
        'short_description', 'age'
    )
    
    # Get characters with this Uberon ID
    characters = Character.objects.filter(uberon_ID=uberon_id).values(
        'character', 'skeletal_element', 'anatomical_region', 
        'character_type', 'description'
    )
    
    data = {
        'uberon_id': uberon_id,
        'fossils': list(fossils),
        'characters': list(characters),
        'fossil_count': len(fossils),
        'character_count': len(characters)
    }
    
    return JsonResponse(data)




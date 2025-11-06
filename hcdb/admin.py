from django.contrib import admin
from .models import Character, CharacterState, Fossil, FossilCharacterState
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields, widgets
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.views import generic
from django.db.models import Q


#  set the header of the admin page
admin.site.site_header = "Known Hominin Characters Database"

# Define custom resources for better import/export control
class CharacterResource(resources.ModelResource):
    class Meta:
        model = Character
        import_id_fields = ['id']  # or ['character_code'] if you want to match on that
        fields = ('id', 'character', 'skeletal_element',
                  'anatomical_region', 'character_type', 'multistate_type',
                  'character_designation', 'character_significance', 'uberon_ID',
                  'state_code', 'number_of_states', 'taxa_found', 'description', 'notes')
        skip_unchanged = False
        report_skipped = False

class CharacterStateResource(resources.ModelResource):
    class Meta:
        model = CharacterState
        import_id_fields = ['id']  # Use ID to match existing records
        fields = ('id', 'character', 'state_code', 'state_name', 
                  'state_description', 'state_order', 'is_derived', 'notes')
        skip_unchanged = False
        report_skipped = False

class FossilResource(resources.ModelResource):
    # Explicitly define the anatomical_region field
    anatomical_region = fields.Field(
        column_name='anatomical_region',
        attribute='anatomical_region',
        widget=widgets.CharWidget()
    )
    
    # Explicitly define taxon field to handle choices
    taxon = fields.Field(
        column_name='taxon',
        attribute='taxon',
        widget=widgets.CharWidget()
    )
    
    # Explicitly define uberon_ID field
    uberon_ID = fields.Field(
        column_name='uberon_ID',
        attribute='uberon_ID',
        widget=widgets.CharWidget()
    )
    
    class Meta:
        model = Fossil
        import_id_fields = ['fossil_id']
        fields = ('id', 'fossil_id', 'age', 'taxon', 'element_type', 'anatomical_region', 'uberon_ID',
                  'short_description','long_description','notes')
        skip_unchanged = False  # Make sure this is False
        report_skipped = False
        
    def before_import_row(self, row, **kwargs):
        """Debug and validate before import"""
        fossil_id = row.get('fossil_id', '')
        anatomical_region = row.get('anatomical_region', '')
        taxon = row.get('taxon', '')
        uberon_id = row.get('uberon_ID', '')
        
        print(f"Importing {fossil_id}:")
        print(f"  - anatomical_region = '{anatomical_region}'")
        print(f"  - taxon = '{taxon}'")
        print(f"  - uberon_ID = '{uberon_id}'")
        
        # Validate anatomical_region
        valid_region_codes = ['CR', 'DEN', 'CF', 'PC']
        if anatomical_region and anatomical_region not in valid_region_codes:
            raise ValueError(f"Invalid anatomical_region '{anatomical_region}' for {fossil_id}. Must be one of: {valid_region_codes}")
        
        # Validate taxon
        valid_taxa_codes = ['AA', 'ANA', 'PA', 'PB', 'A', 'H', 'HH', 'HE', 'HO', 'HER', 'KP']
        if taxon and taxon not in valid_taxa_codes:
            raise ValueError(f"Invalid taxon code '{taxon}' for {fossil_id}. Must be one of: {valid_taxa_codes}")

class FossilCharacterStateResource(resources.ModelResource):
    class Meta:
        model = FossilCharacterState
        import_id_fields = ['id']  # or ['fossil', 'character_state'] for the unique_together
        fields = ('id', 'fossil', 'character_state', 'confidence', 'assigned_by',
                  'assigned_date', 'notes')
        skip_unchanged = False
        report_skipped = False

class CharacterStateInline(admin.TabularInline):
    model = CharacterState
    extra = 1
    fields = ['state_code', 'state_name', 'state_description', 'state_order', 'is_derived', 'notes']
    ordering = ['state_order', 'state_code']

class CharacterAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CharacterResource
    fieldsets = [  # create the field sets for user input
        ('Character Information',
         {'fields': ['character', 'skeletal_element', 'anatomical_region', 'character_type', 'multistate_type',
                     'character_designation','character_significance', 'uberon_ID', 'description', 'number_of_states',
                     'state_code', 'taxa_found', 'notes' ]}
         ),
    ]

    #readonly_fields = ('default_image',)
    list_display = [  # create the list display
        'character', 'skeletal_element', 'display_anatomical_region', 'display_character_type', 'display_multistate_type', 'display_character_designation',
        'display_character_significance', 'uberon_ID', 'state_code']
    list_filter = ['anatomical_region','character_type', 'character_designation', 'character_significance']  # set what can be filtered
    search_fields = ['character', 'anatomical_region', 'character_type','character_designation']  # set what can be searched

    inlines = [CharacterStateInline]
    
    def display_anatomical_region(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_anatomical_region_display() if obj.anatomical_region else '-'
    display_anatomical_region.short_description = 'Anatomical Region'
    display_anatomical_region.admin_order_field = 'anatomical_region'  # Allows column sorting

    def display_character_type(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_character_type_display() if obj.character_type else '-'
    display_character_type.short_description = 'Character Type'
    display_character_type.admin_order_field = 'character_type'  # Allows column sorting

    def display_multistate_type(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_multistate_type_display() if obj.multistate_type else '-'
    display_multistate_type.short_description = 'Multistate Type'
    display_multistate_type.admin_order_field = 'multistate_type'  # Allows column sorting

    def display_character_designation(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_character_designation_display() if obj.character_designation else '-'
    display_character_designation.short_description = 'Character Designation'
    display_character_designation.admin_order_field = 'character_designation'  # Allows column sorting

    def display_character_significance(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_character_significance_display() if obj.character_significance else '-'
    display_character_significance.short_description = 'character_significance'
    display_character_significance.admin_order_field = 'character_significance'  # Allows column sorting


admin.site.register(Character, CharacterAdmin)  # register the classes to the admin site

class CharacterStateAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CharacterStateResource
    #list_select_related = ('character',) # optimizes query by joining character table in queries. may need to test performance
    fieldsets = [
        ('State Information',
         {'fields': ['character', 'state_code', 'state_name', 'state_description']}
         ),
        ('Additional Properties',
         {'fields': ['state_order', 'is_derived', 'notes'],
          'classes': ['collapse']}
         ),
    ]

    readonly_fields = ('created_at', 'updated_at')

    list_display = [
        'character',
        'state_code',
        'state_name',
        'state_order',
        'is_derived',
        'created_at'
    ]

    list_filter = [
        'is_derived',
        'created_at'
    ]

    search_fields = [
        'state_code',
        'state_name',
        'state_description',
        'character__character'
    ]

    autocomplete_fields = ['character']
    list_per_page = 50
    ordering = ['character', 'state_order', 'state_code']

admin.site.register(CharacterState, CharacterStateAdmin)


class FossilCharacterStateInline(admin.TabularInline):
    model = FossilCharacterState
    extra = 1
    fields = ['character_state', 'confidence', 'assigned_by', 'assigned_date', 'notes']
    autocomplete_fields = ['character_state']
    verbose_name = 'Character State'
    verbose_name_plural = 'Character States'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Optionally filter character states based on fossil's anatomical region"""
        if db_field.name == "character_state":
            # You can add filtering logic here if needed
            pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class FossilAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = FossilResource
    fieldsets = [
        ('Fossil Identification',
         {'fields': ['fossil_id', 'age', 'taxon', 'element_type', 'anatomical_region', 'uberon_ID', 'short_description',
                     'long_description']}
         ),
        ('Additional Information',
         {'fields': ['discovery_date', 'location', 'notes'],
          'classes': ['collapse']}  # This makes the section collapsible
         ),
    ]

    readonly_fields = ('created_at', 'updated_at')

    list_display = [
        'fossil_id',
        'age',
        'taxon',
        'element_type',
        'uberon_ID',
        'display_anatomical_region',  # Changed this line
        'get_character_count',
    ]

    list_filter = [
        'taxon',
        'anatomical_region',
        'element_type',
        'discovery_date',
        'created_at'
    ]

    search_fields = [
        'taxon',
        'fossil_id',
        'element_type',
        'location',
        'notes'
    ]

    inlines = [FossilCharacterStateInline]
    
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    def get_character_count(self, obj):
        """Display the number of character states assigned to this fossil"""
        return obj.character_states.count()
    get_character_count.short_description = 'Character States'
    
    def display_anatomical_region(self, obj):
        """Display the human-readable anatomical region"""
        return obj.get_anatomical_region_display() if obj.anatomical_region else '-'
    display_anatomical_region.short_description = 'Anatomical Region'
    display_anatomical_region.admin_order_field = 'anatomical_region'  # Allows column sorting

    def display_age(self, obj):
        """Display the human-readable age"""
        return obj.get_age_display() if obj.age else '-'
    display_age.short_description = 'Age'
    display_age.admin_order_field = 'age'  # Allows column sorting

    def display_taxon(self, obj):
        """Display the human-readable taxon"""
        return obj.get_taxon_display() if obj.age else '-'
    display_taxon.short_description = 'Taxon'
    display_taxon.admin_order_field = 'taxon'  # Allows column sorting


admin.site.register(Fossil, FossilAdmin)


class FossilCharacterStateAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = FossilCharacterStateResource
    fieldsets = [
        ('Assignment Information',
         {'fields': ['fossil', 'character_state', 'confidence']}
         ),
        ('Details',
         {'fields': ['assigned_by', 'assigned_date', 'notes'],
          'classes': ['collapse']}
         ),
    ]

    readonly_fields = ('created_at', 'updated_at')

    list_display = [
        'fossil',
        'get_character',
        'character_state',
        'confidence',
        'assigned_by',
        'assigned_date',
        'created_at'
    ]

    list_filter = [
        'confidence',
        'character_state__character',
        'assigned_date',
        'created_at'
    ]

    search_fields = [
        'fossil__fossil_id',
        'character_state__state_name',
        'character_state__character__character',
        'assigned_by',
        'notes'
    ]

    autocomplete_fields = ['fossil', 'character_state']
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['fossil', 'character_state__character', 'character_state__state_order']

    def get_character(self, obj):
        """Display the character name"""
        return obj.character_state.character.character
    get_character.short_description = 'Character'
    get_character.admin_order_field = 'character_state__character__character'


admin.site.register(FossilCharacterState, FossilCharacterStateAdmin)


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


# Legacy view for items (keep if needed)
def public_page(request):
    items = Item.objects.all().order_by('-created_at')
    return render(request, 'public_page.html', {'items': items})

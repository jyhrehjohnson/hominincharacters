from django.contrib import admin
#from import_export.admin import ImportExportModelAdmin
from .models import Character


class CharacterAdmin(admin.ModelAdmin):
    fieldsets = [  # create the field sets for user input
        ('Character Information',
         {'fields': ['name', 'skeletal_element', 'element', 'type', 'designation', 'state_code', 'states_types', 'description' ]}
         ),
    ]

    #readonly_fields = ('default_image',)
    list_display = [  # create the list display
        'name', 'skeletal_element', 'element', 'type', 'designation', 'state_code', 'states_types', 'description' ]
    list_filter = ['type', 'element','designation']  # set what can be filtered
    search_fields = ['type', 'element','designation']  # set what can be searched
    inlines = [
        # ReferenceInline, # the number of references significantly slows page loads
       # PhotosInline,
    ]

admin.site.register(Character, CharacterAdmin)  # register the classes to the admin site

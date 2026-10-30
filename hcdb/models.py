from django.db import models
import os

CHARTYPE_CHOICES = (('C', 'Continuous'), ('D', 'Discrete'))
ORDER_CHOICES = (('UM', 'Unordered Multistate'), ('OM', 'Ordered Multistate'))
REGIONAL_CHOICES = (('CR', 'Cranial'), ('DEN', 'Dental'), ('CF', 'Craniofacial'),('POST', 'Postcranial'))
CHARDESIGNATION_CHOICES = (('TAX', 'Taxonomic'), ('PHY', 'Phylogenetic'), ('BOTH', 'Both'))
CHARSIGNIFICANCE_CHOICES = (('D', 'Diagnostic'), ('ND', 'Non-diagnostic'))
#STATETYPE_CHOICES = (('A', 'Absent'), ('P', 'Present'), ('SM', 'Small'), ('I', 'Intermediate'), ('M', 'Medium'),
                    # ('L', 'Large'), ('VL', 'Very Large'))
TAXA_CHOICES = (('AA', 'Australopithecus afarensis'), ('ANA', 'Australopithecus anamensis'),
                ('PA', 'Paranthropus aethiopicus'),('PB', 'Paranthropus boisei'), ('A', 'Australopithecus'),
                ('H', 'Hominini'), ('HH', 'Homo habils'), ('HE', 'Homo erectus'), ('HO', 'Homo'),
                ('HER', 'Homo ergaster'), ('KP', 'Kenyanthropus platyops'))

class Character(models.Model):
    #character_code = models.IntegerField(default=0, null=True, blank=True)
    character = models.CharField(max_length=100, null=False)
    skeletal_element = models.CharField(max_length=20, null=True, blank=True)
    anatomical_region = models.CharField(max_length=100, null=True, blank=True, choices=REGIONAL_CHOICES)
    character_type = models.CharField(max_length=100, null=False, blank=True, choices=CHARTYPE_CHOICES)
    multistate_type = models.CharField(max_length=100, null=False, blank=True, choices=ORDER_CHOICES)
    character_designation = models.CharField(max_length=50, null=True, blank=True, choices=CHARDESIGNATION_CHOICES)
    character_significance = models.CharField(max_length=50, null=True, blank=True, choices=CHARSIGNIFICANCE_CHOICES)
    #discrete_state_type = models.CharField(max_length=100, null=True, choices=STATETYPE_CHOICES)
    #continuous_state_type = models.CharField(max_length=5, null=True, blank=True)
    uberon_ID = models.CharField(max_length=100, null=True, blank=True)
    state_code = models.TextField(null=True, blank=True)
    number_of_states = models.IntegerField(default=2, null=True, blank=True)
    taxa_found = models.CharField(max_length=200, null=True, blank=True, choices=TAXA_CHOICES)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    #origins = models.BooleanField(default=False) #this allows for checkbox
    skeletal_elements = models.ManyToManyField('SkeletalElement', related_name='characters', blank=True,
                                               help_text="Skeletal element(s) this character is scored on")
    publications = models.ManyToManyField('Publication', through='CharacterPublication',
                                          related_name='characters', blank=True,
                                          help_text="Publications that define, describe or use this character")

    def __str__(self):
        return self.character

class CharacterState(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE,
                                  related_name='states',
                                  help_text="The character this state belongs to")
    state_code = models.CharField(max_length=10, null=False, blank=False,
                                  help_text="Code for this state (e.g., 0, 1, 2, A, B)")
    state_name = models.CharField(max_length=100, null=False, blank=False,
                                  help_text="Name/label of the state")
    state_description = models.TextField(null=True, blank=True,
                                        help_text="Detailed description of this state")
    state_order = models.IntegerField(default=0, null=True, blank=True,
                                     help_text="Order of this state (for ordered multistate characters)")
    is_derived = models.BooleanField(default=False, null=True, blank=True,
                                    help_text="Whether this is a derived state")
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['character', 'state_order', 'state_code']
        verbose_name = 'Character State'
        verbose_name_plural = 'Character States'
        unique_together = ['character', 'state_code']

    def __str__(self):
        return f"{self.character.character} - State {self.state_code}: {self.state_name}"


class Fossil(models.Model):
    fossil_id = models.CharField(max_length=50, unique=True, null=False, blank=True,
                                 help_text="Catalog Number for the fossil specimen")
    age = models.CharField(max_length=5,null=True, blank=True)
    taxon = models.CharField(max_length=100, null=False, blank=True, choices=TAXA_CHOICES,
                             help_text="Taxonomic name of the fossil")
    element_type = models.CharField(max_length=100, null=False, blank=True,
                                    help_text="Type of skeletal element (e.g., femur, cranium, mandible)")
    anatomical_region = models.CharField(max_length=100, null=False, blank=False,
                                         choices=REGIONAL_CHOICES,
                                         help_text="Anatomical region of the fossil")
    uberon_ID = models.CharField(max_length=100, null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    long_description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Many-to-many relationship with CharacterState
    character_states = models.ManyToManyField(CharacterState, 
                                              through='FossilCharacterState',
                                              related_name='fossils',
                                              blank=True,
                                              help_text="Character states associated with this fossil")

    # Optional additional fields that might be useful
    discovery_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fossil_id']
        verbose_name = 'Fossil'
        verbose_name_plural = 'Fossils'

    def __str__(self):
        return f"{self.fossil_id} - {self.element_type}"
    
    def get_characters(self):
        """Returns all unique characters associated with this fossil"""
        return Character.objects.filter(states__fossils=self).distinct()
    
    def get_character_state_pairs(self):
        """Returns a list of (character, state) tuples for this fossil"""
        return [(fcs.character_state.character, fcs.character_state) 
                for fcs in self.fossil_character_states.select_related('character_state__character')]


class FossilCharacterState(models.Model):
    """Intermediary model linking fossils to their character states"""
    fossil = models.ForeignKey(Fossil, on_delete=models.CASCADE,
                               related_name='fossil_character_states',
                               help_text="The fossil specimen")
    character_state = models.ForeignKey(CharacterState, on_delete=models.CASCADE,
                                        related_name='fossil_character_states',
                                        help_text="The character state observed in this fossil")
    confidence = models.CharField(max_length=20, null=True, blank=True,
                                  choices=(
                                      ('HIGH', 'High Confidence'),
                                      ('MEDIUM', 'Medium Confidence'),
                                      ('LOW', 'Low Confidence'),
                                      ('UNCERTAIN', 'Uncertain')
                                  ),
                                  help_text="Confidence level of this character state assignment")
    notes = models.TextField(null=True, blank=True,
                            help_text="Notes about this specific character state observation")
    assigned_by = models.CharField(max_length=100, null=True, blank=True,
                                   help_text="Person who assigned this state")
    assigned_date = models.DateField(null=True, blank=True,
                                     help_text="Date when this state was assigned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['fossil', 'character_state']
        ordering = ['fossil', 'character_state__character', 'character_state__state_order']
        verbose_name = 'Fossil Character State'
        verbose_name_plural = 'Fossil Character States'

    def __str__(self):
        return f"{self.fossil.fossil_id} - {self.character_state}"
    
    @property
    def character(self):
        """Quick access to the character"""
        return self.character_state.character


SOURCE_ROLE_CHOICES = (
    ('CHAR', 'Character definition'),   # character taken from this source's character list / matrix
    ('DESC', 'Character description'),  # wording of the description taken from this source
    ('STATE', 'State definitions'),     # states / state coding taken from this source
    ('USE', 'Used or cited'),           # character used, scored or discussed in this source
)


class SkeletalElement(models.Model):
    """A skeletal element (bone, tooth class, or composite structure) that characters are scored on."""
    name = models.CharField(max_length=100, unique=True,
                            help_text="Element name (e.g., Temporal, Mandible, Femur)")
    anatomical_region = models.CharField(max_length=100, null=True, blank=True, choices=REGIONAL_CHOICES,
                                         help_text="Default region; leave blank if characters on this element span regions")
    uberon_ID = models.CharField(max_length=100, null=True, blank=True,
                                 help_text="UBERON ID for the element itself, not the character-level structure")
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Skeletal Element'
        verbose_name_plural = 'Skeletal Elements'

    def __str__(self):
        return self.name


class Publication(models.Model):
    """A publication or other source (e.g., ASUDAS) that defines, describes or uses characters."""
    citation_key = models.CharField(max_length=50, unique=True,
                                    help_text="Short unique key, e.g. Strait1997, Dembo2015")
    authors = models.CharField(max_length=500, help_text="Author list, e.g. 'Strait, D.S., Grine, F.E., Moniz, M.A.'")
    year = models.IntegerField(null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    journal = models.CharField(max_length=200, null=True, blank=True, help_text="Journal or book/volume title")
    volume = models.CharField(max_length=20, null=True, blank=True)
    issue = models.CharField(max_length=20, null=True, blank=True)
    pages = models.CharField(max_length=30, null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True, verbose_name='DOI')
    url = models.URLField(null=True, blank=True, verbose_name='URL')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['authors', 'year']
        verbose_name = 'Publication'
        verbose_name_plural = 'Publications'

    def __str__(self):
        return f"{self.authors} ({self.year})" if self.year else self.authors


class CharacterPublication(models.Model):
    """How a given publication uses a given character -- the 'uses' record."""
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='character_publications')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='character_publications')
    role = models.CharField(max_length=10, choices=SOURCE_ROLE_CHOICES, default='USE',
                            help_text="What this publication contributes for this character")
    character_number = models.CharField(max_length=20, null=True, blank=True,
                                        help_text="Character number in the source's list or matrix")
    original_wording = models.TextField(null=True, blank=True,
                                        help_text="Character definition as worded in the source")
    original_states = models.TextField(null=True, blank=True,
                                       help_text="States/coding as given in the source, if they differ")
    page = models.CharField(max_length=30, null=True, blank=True, help_text="Page, table or figure in the source")
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['character', 'publication', 'role']
        ordering = ['character', 'publication__year']
        verbose_name = 'Character Publication'
        verbose_name_plural = 'Character Publications'

    def __str__(self):
        return f"{self.character} - {self.publication} ({self.get_role_display()})"


class Item(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

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
        
        # Validate taxon - updated to include KP
        valid_taxa_codes = ['AA', 'ANA', 'PA', 'PB', 'A', 'H', 'HH', 'HE', 'HO', 'HER', 'KP']
        if taxon and taxon not in valid_taxa_codes:
            raise ValueError(f"Invalid taxon code '{taxon}' for {fossil_id}. Must be one of: {valid_taxa_codes}")
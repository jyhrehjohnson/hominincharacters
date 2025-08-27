from django.db import models
import os

CHARTYPE_CHOICES = (('C', 'Continuous'), ('D', 'Discrete'))
ELEMENT_CHOICES = (('CR', 'Cranial'), ('CD', 'Craniodental'), ('CF', 'Craniofacial'), ('PC', 'Postcranial'))
CHARDESIGNATION_CHOICES = (('TAX', 'Taxonomic'), ('PHL', 'Phylogenetic'), ('BOTH', 'Both'))
STATETYPE_CHOICES = (('A', 'Absent'), ('P', 'Present'), ('SM', 'Small'), ('I', 'Intermediate'), ('M', 'Medium'),
                     ('L', 'Large'), ('VL', 'Very Large'), ('LATFLARE', 'Lateral flare wth posterior protrusion'))

class Character(models.Model):
    character_code = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=50, null=False)
    skeletal_element = models.CharField(max_length=5, null=True, blank=True)
    element = models.CharField(max_length=50, null=True, blank=True, choices=ELEMENT_CHOICES)
    type = models.CharField(max_length=50, null=False, choices=CHARTYPE_CHOICES)
    designation = models.CharField(max_length=50, null=False, choices=CHARDESIGNATION_CHOICES)
    state_code = models.CharField(max_length=20, default='', null=False)
    states_types = models.CharField(max_length=50, null=False, choices=STATETYPE_CHOICES)
    description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name


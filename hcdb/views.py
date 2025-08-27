from django.views import generic
from .models import Character


class CharacterListView(generic.ListView):
    #  model = Character
    context_object_name = 'character'

    def get_queryset(self):
        """Return a list of Character """
        character = Character.objects.filter(classification_status='accepted')
        return character

class CharacterDetailView(generic.DetailView):
    model = Character




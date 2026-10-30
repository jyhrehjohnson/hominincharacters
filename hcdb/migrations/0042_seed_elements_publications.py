"""
Seed SkeletalElement and Publication from data already in Character.

- One SkeletalElement per distinct (cleaned) Character.skeletal_element value; each character
  is linked to its element. Whitespace is trimmed and the plural 'Metatarsals' is merged into
  'Metatarsal'. An element's anatomical_region is filled only when every character on it shares
  one region; otherwise it is left blank for review.
- Publications are created from the citations written in Character.notes and linked through
  CharacterPublication with a role:
      "Traits from ..."        -> CHAR  (character definition)
      "Descriptions from ..."  -> DESC  (description wording)
      any other citation       -> USE   (used / cited)
  Only author + year are filled; title, journal, DOI etc. are left for you to complete.

The original skeletal_element and notes fields are NOT modified, so this is fully reversible.
"""
import re
from django.db import migrations

ELEMENT_ALIASES = {'Metatarsals': 'Metatarsal'}

# citation_key: (authors, year, regex that detects it in notes)
PUBLICATIONS = {
    'Strait1997':  ('Strait et al.', 1997, r'Strait,?\s*1997'),
    'Strait2004':  ('Strait & Grine', 2004, r'Strait,?\s*1997\s*;\s*2004|Strait,?\s*2004'),
    'Dembo2015':   ('Dembo et al.', 2015, r'Dembo,?\s*2015'),
    'Asfaw1999':   ('Asfaw et al.', 1999, r'Asfaw et al\.?\s*1999'),
    'Berger2010':  ('Berger et al.', 2010, r'Berger( et al\.?)?\s*2010'),
    'White1994':   ('White et al.', 1994, r'White et al\.?\s*1994'),
    'Dart1925':    ('Dart', 1925, r'Dart\s*1925'),
    'ASUDAS':      ('Arizona State University Dental Anthropology System (ASUDAS)', None, r'ASUDAS'),
}


def roles_for(notes):
    """Return a set of (citation_key, role) pairs found in a notes string."""
    found = set()
    if not notes:
        return found
    # split into the "Traits from" part, the "Descriptions from" part, and everything else
    traits = re.search(r'Traits from(.*?)(?:\.|$)', notes)
    descs = re.search(r'Descriptions from\s*(Dembo,?\s*2015)', notes)
    rest = notes
    if traits:
        rest = rest.replace(traits.group(0), ' ')
    if descs:
        rest = rest.replace(descs.group(0), ' ')
    for key, (_, _, pat) in PUBLICATIONS.items():
        if traits and re.search(pat, traits.group(1)):
            found.add((key, 'CHAR'))
        if descs and re.search(pat, descs.group(1)):
            found.add((key, 'DESC'))
        if re.search(pat, rest):
            found.add((key, 'USE'))
    return found


def seed(apps, schema_editor):
    Character = apps.get_model('hcdb', 'Character')
    SkeletalElement = apps.get_model('hcdb', 'SkeletalElement')
    Publication = apps.get_model('hcdb', 'Publication')
    CharacterPublication = apps.get_model('hcdb', 'CharacterPublication')

    # --- skeletal elements ---
    regions = {}
    for ch in Character.objects.all():
        name = (ch.skeletal_element or '').strip()
        if not name:
            continue
        name = ELEMENT_ALIASES.get(name, name)
        el, _ = SkeletalElement.objects.get_or_create(name=name)
        ch.skeletal_elements.add(el)
        if ch.anatomical_region:
            regions.setdefault(el.pk, set()).add(ch.anatomical_region)
    for pk, regs in regions.items():
        if len(regs) == 1:
            SkeletalElement.objects.filter(pk=pk).update(anatomical_region=regs.pop())

    # --- publications ---
    pubs = {}
    for key, (authors, year, _) in PUBLICATIONS.items():
        pubs[key], _ = Publication.objects.get_or_create(
            citation_key=key, defaults={'authors': authors, 'year': year,
                                        'notes': 'Auto-created from Character.notes; complete full citation.'})
    links = []
    for ch in Character.objects.exclude(notes__isnull=True).exclude(notes=''):
        for key, role in roles_for(ch.notes):
            links.append(CharacterPublication(character=ch, publication=pubs[key], role=role))
    CharacterPublication.objects.bulk_create(links, ignore_conflicts=True)
    # drop any publication that ended up with no characters
    for p in pubs.values():
        if not CharacterPublication.objects.filter(publication=p).exists():
            p.delete()


def unseed(apps, schema_editor):
    apps.get_model('hcdb', 'CharacterPublication').objects.all().delete()
    apps.get_model('hcdb', 'Publication').objects.all().delete()
    apps.get_model('hcdb', 'Character').skeletal_elements.through.objects.all().delete()
    apps.get_model('hcdb', 'SkeletalElement').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('hcdb', '0041_skeletalelement_publication'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]

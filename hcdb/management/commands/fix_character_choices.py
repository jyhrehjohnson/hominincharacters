from django.core.management.base import BaseCommand
from hcdb.models import Character


class Command(BaseCommand):
    help = 'Fix character choice field values to match expected codes'

    def handle(self, *args, **options):
        # Mapping of possible imported values to correct codes
        region_map = {
            'Cranial': 'CR', 'cranial': 'CR', 'CR': 'CR',
            'Dental': 'DEN', 'dental': 'DEN', 'DEN': 'DEN',
            'Craniofacial': 'CF', 'craniofacial': 'CF', 'CF': 'CF',
            'Postcranial': 'PC', 'postcranial': 'PC', 'PC': 'PC'
        }

        type_map = {
            'Continuous': 'C', 'continuous': 'C', 'C': 'C',
            'Discrete': 'D', 'discrete': 'D', 'D': 'D'
        }

        multistate_map = {
            'Unordered Multistate': 'UM', 'unordered multistate': 'UM', 'UM': 'UM',
            'Ordered Multistate': 'OM', 'ordered multistate': 'OM', 'OM': 'OM'
        }

        designation_map = {
            'Taxonomic': 'TAX', 'taxonomic': 'TAX', 'TAX': 'TAX',
            'Phylogenetic': 'PHY', 'phylogenetic': 'PHY', 'PHY': 'PHY',
            'Both': 'BOTH', 'both': 'BOTH', 'BOTH': 'BOTH'
        }

        significance_map = {
            'Diagnostic': 'D', 'diagnostic': 'D', 'D': 'D',
            'Non-diagnostic': 'ND', 'non-diagnostic': 'ND', 'ND': 'ND'
        }

        updated_count = 0

        for char in Character.objects.all():
            updated = False

            # Fix anatomical_region
            if char.anatomical_region:
                clean_region = char.anatomical_region.strip()
                if clean_region in region_map:
                    new_val = region_map[clean_region]
                    if char.anatomical_region != new_val:
                        self.stdout.write(f"Fixing {char.character}: region '{char.anatomical_region}' -> '{new_val}'")
                        char.anatomical_region = new_val
                        updated = True
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Unknown region value: '{clean_region}' for {char.character}"))

            # Fix character_type
            if char.character_type:
                clean_type = char.character_type.strip()
                if clean_type in type_map:
                    new_val = type_map[clean_type]
                    if char.character_type != new_val:
                        self.stdout.write(f"Fixing {char.character}: type '{char.character_type}' -> '{new_val}'")
                        char.character_type = new_val
                        updated = True
                else:
                    self.stdout.write(self.style.WARNING(f"Unknown type value: '{clean_type}' for {char.character}"))

            # Fix multistate_type
            if char.multistate_type:
                clean_multi = char.multistate_type.strip()
                if clean_multi in multistate_map:
                    new_val = multistate_map[clean_multi]
                    if char.multistate_type != new_val:
                        self.stdout.write(
                            f"Fixing {char.character}: multistate '{char.multistate_type}' -> '{new_val}'")
                        char.multistate_type = new_val
                        updated = True
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Unknown multistate value: '{clean_multi}' for {char.character}"))

            # Fix character_designation
            if char.character_designation:
                clean_desig = char.character_designation.strip()
                if clean_desig in designation_map:
                    new_val = designation_map[clean_desig]
                    if char.character_designation != new_val:
                        self.stdout.write(
                            f"Fixing {char.character}: designation '{char.character_designation}' -> '{new_val}'")
                        char.character_designation = new_val
                        updated = True
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Unknown designation value: '{clean_desig}' for {char.character}"))

            # Fix character_significance
            if char.character_significance:
                clean_sig = char.character_significance.strip()
                if clean_sig in significance_map:
                    new_val = significance_map[clean_sig]
                    if char.character_significance != new_val:
                        self.stdout.write(
                            f"Fixing {char.character}: significance '{char.character_significance}' -> '{new_val}'")
                        char.character_significance = new_val
                        updated = True
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Unknown significance value: '{clean_sig}' for {char.character}"))

            if updated:
                char.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated_count} characters'))
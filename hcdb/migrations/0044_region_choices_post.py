# Brings the migrations in line with REGIONAL_CHOICES in models.py (commit "Change PC to POST in
# Regional_Choices") and converts fossils still stored with the old code 'PC' to 'POST'.

from django.db import migrations, models


def pc_to_post(apps, schema_editor):
    for model in ('Fossil', 'Character'):
        apps.get_model('hcdb', model).objects.filter(anatomical_region='PC').update(anatomical_region='POST')


class Migration(migrations.Migration):

    dependencies = [
        ("hcdb", "0043_fossil_score_source_taxoncharacterstate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="character",
            name="anatomical_region",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CR", "Cranial"),
                    ("DEN", "Dental"),
                    ("CF", "Craniofacial"),
                    ("POST", "Postcranial"),
                ],
                max_length=100,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="fossil",
            name="anatomical_region",
            field=models.CharField(
                choices=[
                    ("CR", "Cranial"),
                    ("DEN", "Dental"),
                    ("CF", "Craniofacial"),
                    ("POST", "Postcranial"),
                ],
                help_text="Anatomical region of the fossil",
                max_length=100,
            ),
        ),
        # Reverse is a no-op: the old 'PC' rows can't be told apart from real 'POST' rows afterwards.
        migrations.RunPython(pc_to_post, migrations.RunPython.noop),
    ]

# Adds SkeletalElement, Publication and CharacterPublication, and links them to Character.

from django.db import migrations, models
import django.db.models.deletion

REGIONAL_CHOICES = [('CR', 'Cranial'), ('DEN', 'Dental'), ('CF', 'Craniofacial'), ('POST', 'Postcranial')]
ROLE_CHOICES = [('CHAR', 'Character definition'), ('DESC', 'Character description'),
                ('STATE', 'State definitions'), ('USE', 'Used or cited')]


def _id():
    return models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')


class Migration(migrations.Migration):

    dependencies = [
        ('hcdb', '0040_alter_character_taxa_found_alter_fossil_taxon'),
    ]

    operations = [
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', _id()),
                ('citation_key', models.CharField(help_text='Short unique key, e.g. Strait1997, Dembo2015', max_length=50, unique=True)),
                ('authors', models.CharField(help_text="Author list, e.g. 'Strait, D.S., Grine, F.E., Moniz, M.A.'", max_length=500)),
                ('year', models.IntegerField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('journal', models.CharField(blank=True, help_text='Journal or book/volume title', max_length=200, null=True)),
                ('volume', models.CharField(blank=True, max_length=20, null=True)),
                ('issue', models.CharField(blank=True, max_length=20, null=True)),
                ('pages', models.CharField(blank=True, max_length=30, null=True)),
                ('doi', models.CharField(blank=True, max_length=100, null=True, verbose_name='DOI')),
                ('url', models.URLField(blank=True, null=True, verbose_name='URL')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Publication', 'verbose_name_plural': 'Publications', 'ordering': ['authors', 'year']},
        ),
        migrations.CreateModel(
            name='SkeletalElement',
            fields=[
                ('id', _id()),
                ('name', models.CharField(help_text='Element name (e.g., Temporal, Mandible, Femur)', max_length=100, unique=True)),
                ('anatomical_region', models.CharField(blank=True, choices=REGIONAL_CHOICES, help_text='Default region; leave blank if characters on this element span regions', max_length=100, null=True)),
                ('uberon_ID', models.CharField(blank=True, help_text='UBERON ID for the element itself, not the character-level structure', max_length=100, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Skeletal Element', 'verbose_name_plural': 'Skeletal Elements', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='CharacterPublication',
            fields=[
                ('id', _id()),
                ('role', models.CharField(choices=ROLE_CHOICES, default='USE', help_text='What this publication contributes for this character', max_length=10)),
                ('character_number', models.CharField(blank=True, help_text="Character number in the source's list or matrix", max_length=20, null=True)),
                ('original_wording', models.TextField(blank=True, help_text='Character definition as worded in the source', null=True)),
                ('original_states', models.TextField(blank=True, help_text='States/coding as given in the source, if they differ', null=True)),
                ('page', models.CharField(blank=True, help_text='Page, table or figure in the source', max_length=30, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='character_publications', to='hcdb.character')),
                ('publication', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='character_publications', to='hcdb.publication')),
            ],
            options={
                'verbose_name': 'Character Publication',
                'verbose_name_plural': 'Character Publications',
                'ordering': ['character', 'publication__year'],
                'unique_together': {('character', 'publication', 'role')},
            },
        ),
        migrations.AddField(
            model_name='character',
            name='publications',
            field=models.ManyToManyField(blank=True, help_text='Publications that define, describe or use this character', related_name='characters', through='hcdb.CharacterPublication', to='hcdb.publication'),
        ),
        migrations.AddField(
            model_name='character',
            name='skeletal_elements',
            field=models.ManyToManyField(blank=True, help_text='Skeletal element(s) this character is scored on', related_name='characters', to='hcdb.skeletalelement'),
        ),
    ]

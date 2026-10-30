"""Import specimen-level character scores (fossil -> character state) from a CSV file.

CSV columns (header row required, extra columns are ignored):
  fossil_id      catalog number exactly as in the database, e.g. KNM-ER 3954
  character_id   database id of the character (shown in the admin and on the public site)
  character      character name; only used when character_id is blank (case-insensitive exact match)
  state_code     the state code as defined in THIS database (0, 1, 2...). Use 0/1 when the source
                 could not decide between states. Blank or ? means not scorable: the row is skipped.
  source         citation_key of the publication (e.g. Strait1997). Blank = your own observation.
  page           optional: page, table or figure in the source
  confidence     optional: HIGH, MEDIUM, LOW or UNCERTAIN (0/1-type scores are always UNCERTAIN)
  assigned_by    optional: who scored it
  assigned_date  optional: YYYY-MM-DD
  notes          optional

Usage (from the project folder):
  python manage.py import_fossil_scores --template fossil_scores_template.csv
  python manage.py import_fossil_scores scores.csv            # dry run: checks every row, writes nothing
  python manage.py import_fossil_scores scores.csv --commit   # writes, but only if no row has an error
  python manage.py import_fossil_scores scores.csv --commit --replace
        # --replace: a fossil/character/source that already has a different state is overwritten
"""
import csv
import re
from collections import defaultdict
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hcdb.models import Character, CharacterState, Fossil, FossilCharacterState, Publication

COLUMNS = ['fossil_id', 'character_id', 'character', 'state_code', 'source', 'page',
           'confidence', 'assigned_by', 'assigned_date', 'notes']
CONFIDENCE = {'HIGH', 'MEDIUM', 'LOW', 'UNCERTAIN'}
SPLIT = re.compile(r'\s*[/&,]\s*')


class Command(BaseCommand):
    help = "Import fossil (specimen-level) character scores from a CSV. Dry run unless --commit."

    def add_arguments(self, parser):
        parser.add_argument('csv_path', nargs='?')
        parser.add_argument('--commit', action='store_true', help='Write to the database (default: dry run)')
        parser.add_argument('--replace', action='store_true',
                            help='Overwrite an existing different state from the same source')
        parser.add_argument('--template', metavar='PATH', help='Write an empty template CSV and stop')

    def handle(self, *args, **opts):
        if opts['template']:
            with open(opts['template'], 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(COLUMNS)
                w.writerow(['KNM-ER 3954', '', 'Mandibular cross-sectional area at M1', '1', 'Strait1997',
                            'Table 2', 'HIGH', '', '', 'example row - delete'])
            self.stdout.write(f"Template written to {opts['template']}")
            return
        if not opts['csv_path']:
            raise CommandError('Give a CSV file, or --template PATH')

        with open(opts['csv_path'], newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            header = [h.strip() for h in (reader.fieldnames or [])]
            missing = {'fossil_id', 'state_code'} - set(header)
            if missing or not ({'character_id', 'character'} & set(header)):
                raise CommandError(f"CSV needs columns fossil_id, state_code and character_id or character. "
                                   f"Found: {header}")
            rows = [{(k or '').strip(): (v or '').strip() for k, v in r.items()} for r in reader]

        fossils = {f.fossil_id.strip().lower(): f for f in Fossil.objects.all()}
        chars_by_id = {c.pk: c for c in Character.objects.all()}
        chars_by_name = defaultdict(list)
        for c in chars_by_id.values():
            chars_by_name[c.character.strip().lower()].append(c)
        states = {(s.character_id, s.state_code.strip()): s for s in CharacterState.objects.all()}
        pubs = {p.citation_key.lower(): p for p in Publication.objects.all()}

        errors, skipped, planned = [], 0, []
        seen = {}  # (fossil, character, source) -> set of state ids from this file
        for n, r in enumerate(rows, start=2):  # row 1 is the header
            if not any(r.values()):
                continue
            where = f"row {n}"
            fossil = fossils.get(r.get('fossil_id', '').lower())
            if fossil is None:
                errors.append(f"{where}: fossil '{r.get('fossil_id', '')}' not found")
                continue
            char = None
            cid = r.get('character_id', '')
            if cid:
                if not cid.isdigit() or int(cid) not in chars_by_id:
                    errors.append(f"{where}: character_id '{cid}' not found")
                    continue
                char = chars_by_id[int(cid)]
            else:
                hits = chars_by_name.get(r.get('character', '').lower(), [])
                if len(hits) != 1:
                    errors.append(f"{where}: character '{r.get('character', '')}' "
                                  f"{'not found' if not hits else 'matches several characters; use character_id'}")
                    continue
                char = hits[0]
            code = r.get('state_code', '')
            if code in ('', '?'):
                skipped += 1
                continue
            codes = [c for c in SPLIT.split(code) if c]
            st = [states.get((char.pk, c)) for c in codes]
            if any(s is None for s in st):
                known = sorted(k[1] for k in states if k[0] == char.pk)
                errors.append(f"{where}: state '{code}' not defined for character {char.pk} "
                              f"'{char.character}' (defined: {', '.join(known) or 'none'})")
                continue
            src = r.get('source', '')
            pub = None
            if src:
                pub = pubs.get(src.lower())
                if pub is None:
                    errors.append(f"{where}: source '{src}' is not a publication citation_key")
                    continue
            conf = r.get('confidence', '').upper()
            if len(st) > 1:
                conf = 'UNCERTAIN'
            if conf and conf not in CONFIDENCE:
                errors.append(f"{where}: confidence '{r.get('confidence')}' must be one of {sorted(CONFIDENCE)}")
                continue
            adate = None
            if r.get('assigned_date'):
                try:
                    adate = date.fromisoformat(r['assigned_date'])
                except ValueError:
                    errors.append(f"{where}: assigned_date '{r['assigned_date']}' is not YYYY-MM-DD")
                    continue
            key = (fossil.pk, char.pk, pub.pk if pub else None)
            ids = {s.pk for s in st}
            if key in seen and seen[key] != ids:
                errors.append(f"{where}: {fossil.fossil_id} / character {char.pk} / source "
                              f"{src or '(own)'} appears earlier in the file with a different state")
                continue
            seen[key] = ids
            note = r.get('notes', '')
            if len(st) > 1:
                note = (f"Uncertain between states {code}. " + note).strip()
            planned.append(dict(fossil=fossil, char=char, states=st, pub=pub, page=r.get('page') or None,
                                confidence=conf or None, assigned_by=r.get('assigned_by') or None,
                                assigned_date=adate, notes=note or None, where=where))

        # conflicts with scores already in the database
        conflicts = []
        for p in planned:
            existing = FossilCharacterState.objects.filter(
                fossil=p['fossil'], character_state__character=p['char'], publication=p['pub'])
            other = existing.exclude(character_state__in=p['states'])
            if other.exists():
                p['replace'] = list(other)
                if not opts['replace']:
                    conflicts.append(f"{p['where']}: {p['fossil'].fossil_id} already has state "
                                     f"{', '.join(o.character_state.state_code for o in other)} for character "
                                     f"{p['char'].pk} from this source (use --replace to overwrite)")
        errors += conflicts

        n_scores = sum(len(p['states']) for p in planned)
        self.stdout.write(f"{len(rows)} rows read: {len(planned)} valid ({n_scores} scores), "
                          f"{skipped} skipped as not scorable, {len(errors)} with errors.")
        for e in errors[:200]:
            self.stdout.write(self.style.ERROR('  ' + e))
        if len(errors) > 200:
            self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 200} more"))
        if errors:
            raise CommandError('Nothing was written. Fix the rows above and run again.')
        if not opts['commit']:
            self.stdout.write(self.style.WARNING('Dry run: nothing written. Add --commit to import.'))
            return

        created = updated = replaced = 0
        with transaction.atomic():
            for p in planned:
                for old in p.get('replace', []):
                    old.delete()
                    replaced += 1
                for s in p['states']:
                    obj, made = FossilCharacterState.objects.update_or_create(
                        fossil=p['fossil'], character_state=s, publication=p['pub'],
                        defaults=dict(page=p['page'], confidence=p['confidence'], assigned_by=p['assigned_by'],
                                      assigned_date=p['assigned_date'], notes=p['notes']))
                    created += made
                    updated += not made
        self.stdout.write(self.style.SUCCESS(
            f"Imported: {created} new scores, {updated} updated, {replaced} replaced."))

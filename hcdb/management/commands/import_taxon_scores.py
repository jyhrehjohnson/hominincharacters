"""Import species-level codings from a published character matrix (CSV).

Expected layout (one row per character, one column per taxon), e.g. Strait & Grine 2004 Table 3:

    Label, Character,                          Gorilla, Pan, P_boisei, ...
    SG1,   Projection of nasal bones above...,  0,      0,   1,  ...

Use --transpose if the matrix has one row per taxon and one column per character instead.

Two steps:

1. Match the matrix rows to characters in the database and write the matching for you to check:
     python manage.py import_taxon_scores sources/strait2004.csv --source Strait2004 \\
         --name-column Character --number-column Label --write-mapping sources/strait2004_mapping.csv
   Open the mapping file. Only rows with a character_id are imported:
     exact       the names match; character_id is filled in
     check       near-identical spelling (e.g. Antero-medial / Anteromedial); filled in, but confirm it
     suggestion  a similar name that may be a different character (e.g. Premolar vs. Molar crown area);
                 NOT filled in - copy suggested_id into character_id only if it is the same character
     none        no similar name in the database; fill in character_id yourself or leave blank to skip
   Then:

2. Import using the checked mapping (dry run first, then --commit):
     python manage.py import_taxon_scores sources/strait2004.csv --source Strait2004 \\
         --name-column Character --number-column Label --mapping sources/strait2004_mapping.csv
     ... add --commit to write.

Codes are always stored exactly as written (raw_code). Add --map-states ONLY if the source numbers its
states the same way this database does; then each code is also linked to the matching CharacterState.

Every matched character is also linked to the source as a Character definition (with its number in the
source). --prune-pooled-links additionally removes this source's Character-definition links for characters
that are NOT in the matrix (e.g. links created from a pooled "Traits from Strait, 1997;2004 & Dembo, 2015"
note), so the source is linked to exactly the characters in its matrix.
"""
import csv
import difflib
import re
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hcdb.models import Character, CharacterPublication, CharacterState, Publication, TaxonCharacterState

MISSING = {'', '?'}
INAPPLICABLE = {'-', '–', 'n/a', 'na'}
VARIABLE_WORDS = {'variable', 'polymorphic'}
SPLIT = re.compile(r'\s*(?:/|&|,|\+|\bor\b)\s*')


def norm(name):
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', name.lower()).split())


def parse_code(raw):
    """Return (status, list of code tokens, note)."""
    code = raw.strip()
    low = code.lower()
    if low in MISSING:
        return 'MISSING', [], ''
    if low in INAPPLICABLE:
        return 'NA', [], ''
    if ':' in code:  # e.g. "Colobus:2 Papio:0" for a composite outgroup
        return 'UNMAPPED', [], 'Composite coding for more than one taxon'
    if low in VARIABLE_WORDS:
        return 'POLY', [], 'Coded as variable in the source'
    tokens = [t for t in SPLIT.split(code) if t]
    # a state code is a number (0, 1, 12) or a single letter (A, B); anything else is a word
    if not tokens or not all(re.fullmatch(r'\d+|[A-Za-z]', t) for t in tokens):
        # words rather than codes, e.g. Strait 1997's "Projected, expanded" or "Small or absent"
        return 'UNMAPPED', [], 'Descriptive coding in the source (not a state code)'
    if len(tokens) > 1:
        return 'POLY', tokens, ''
    return 'SCORED', tokens, ''


class Command(BaseCommand):
    help = "Import species-level character codings from a matrix CSV (two steps: --write-mapping, then --mapping)."

    def add_arguments(self, parser):
        parser.add_argument('csv_path')
        parser.add_argument('--source', required=True, help='citation_key of the publication, e.g. Strait2004')
        parser.add_argument('--name-column', default='Character', help='Column with character names')
        parser.add_argument('--number-column', default=None, help="Column with the source's character numbers")
        parser.add_argument('--transpose', action='store_true',
                            help='Matrix has one row per taxon (first column = taxon) and one column per character')
        parser.add_argument('--skip-columns', default='',
                            help='Comma-separated columns that are not taxa (e.g. "No.,Anatomical Region")')
        parser.add_argument('--write-mapping', metavar='PATH', help='Step 1: write the character matching and stop')
        parser.add_argument('--mapping', metavar='PATH', help='Step 2: use this checked matching')
        parser.add_argument('--threshold', type=float, default=0.85, help='Name similarity for a suggested match')
        parser.add_argument('--map-states', action='store_true',
                            help="Link codes to this database's states (only if the source uses the same numbering)")
        parser.add_argument('--prune-pooled-links', action='store_true',
                            help="Remove this source's Character-definition links to characters not in the matrix")
        parser.add_argument('--commit', action='store_true', help='Write to the database (default: dry run)')

    # ---- reading ---------------------------------------------------------------
    def read_matrix(self, opts):
        with open(opts['csv_path'], newline='', encoding='utf-8-sig') as f:
            rows = [[c.strip() for c in r] for r in csv.reader(f)]
        rows = [r for r in rows if any(r)]
        if not rows:
            raise CommandError('The CSV is empty')
        if opts['transpose']:
            width = max(len(r) for r in rows)
            rows = [r + [''] * (width - len(r)) for r in rows]
            rows = [list(col) for col in zip(*rows)]
            rows[0][0] = opts['name_column']
        header = rows[0]
        if opts['name_column'] not in header:
            raise CommandError(f"Column '{opts['name_column']}' not found. Columns: {header}")
        name_i = header.index(opts['name_column'])
        num_i = header.index(opts['number_column']) if opts['number_column'] in header else None
        if opts['number_column'] and num_i is None:
            raise CommandError(f"Column '{opts['number_column']}' not found. Columns: {header}")
        skip = {s.strip() for s in opts['skip_columns'].split(',') if s.strip()}
        taxa = [(i, h) for i, h in enumerate(header)
                if i not in (name_i, num_i) and h and h not in skip]
        if not taxa:
            raise CommandError('No taxon columns found')
        chars = []
        for r in rows[1:]:
            r = r + [''] * (len(header) - len(r))
            if not r[name_i]:
                continue
            chars.append({'name': r[name_i], 'number': r[num_i] if num_i is not None else '',
                          'codes': {h: r[i] for i, h in taxa}})
        return chars, [h for _, h in taxa]

    # ---- step 1 ----------------------------------------------------------------
    def write_mapping(self, chars, path, threshold):
        db = list(Character.objects.all())
        by_norm = {}
        for c in db:
            by_norm.setdefault(norm(c.character), []).append(c)
        names = list(by_norm)
        counts = Counter()
        digits = lambda s: re.findall(r'\d+', s)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['row', 'source_number', 'source_name', 'character_id', 'suggested_id',
                        'database_name', 'similarity', 'match'])
            for i, ch in enumerate(chars, start=1):
                n = norm(ch['name'])
                if n in by_norm and len(by_norm[n]) == 1:
                    c = by_norm[n][0]
                    w.writerow([i, ch['number'], ch['name'], c.pk, '', c.character, '1.00', 'exact'])
                    counts['exact'] += 1
                    continue
                best = difflib.get_close_matches(n, names, n=1, cutoff=threshold)
                if best:
                    c = by_norm[best[0]][0]
                    sim = difflib.SequenceMatcher(None, n, best[0]).ratio()
                    if sim >= 0.95 and digits(n) == digits(best[0]) and len(by_norm[best[0]]) == 1:
                        # near-identical spelling (e.g. Antero-medial / Anteromedial): filled in, but check it
                        w.writerow([i, ch['number'], ch['name'], c.pk, '', c.character, f'{sim:.2f}', 'check'])
                        counts['check'] += 1
                    else:
                        # only a suggestion: copy suggested_id into character_id if it is the same character
                        w.writerow([i, ch['number'], ch['name'], '', c.pk, c.character, f'{sim:.2f}', 'suggestion'])
                        counts['suggestion'] += 1
                else:
                    w.writerow([i, ch['number'], ch['name'], '', '', '', '', 'none'])
                    counts['none'] += 1
        self.stdout.write(f"{len(chars)} characters in the matrix: {counts['exact']} exact matches, "
                          f"{counts['check']} near-exact (filled in, please check), "
                          f"{counts['suggestion']} suggestions (NOT filled in), {counts['none']} with no match.")
        self.stdout.write(f"Mapping written to {path}. Review it - only rows with a character_id are imported - "
                          f"then run again with --mapping {path}")

    # ---- step 2 ----------------------------------------------------------------
    def handle(self, *args, **opts):
        pub = Publication.objects.filter(citation_key__iexact=opts['source']).first()
        if pub is None:
            raise CommandError(f"No publication with citation_key '{opts['source']}'. Add it in the admin first.")
        chars, taxa = self.read_matrix(opts)
        if opts['write_mapping']:
            self.write_mapping(chars, opts['write_mapping'], opts['threshold'])
            return
        if not opts['mapping']:
            raise CommandError('Run step 1 with --write-mapping first, check the file, then pass it with --mapping')

        db_chars = {c.pk: c for c in Character.objects.all()}
        errors, mapping = [], {}
        with open(opts['mapping'], newline='', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                row, cid = (r.get('row') or '').strip(), (r.get('character_id') or '').strip()
                if not row.isdigit():
                    continue
                if not cid:
                    continue  # deliberately skipped
                if not cid.isdigit() or int(cid) not in db_chars:
                    errors.append(f"mapping row {row}: character_id '{cid}' not found")
                    continue
                mapping[int(row)] = db_chars[int(cid)]
        used = Counter(c.pk for c in mapping.values())
        for pk, k in used.items():
            if k > 1:
                errors.append(f"character_id {pk} is mapped from {k} matrix rows; each character may appear once")
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR('  ' + e))
            raise CommandError('Nothing was written. Fix the mapping file and run again.')

        states = {}
        if opts['map_states']:
            for s in CharacterState.objects.filter(character__in=mapping.values()):
                states.setdefault(s.character_id, {})[s.state_code.strip().lower()] = s

        planned, status_counts, unmatched_codes = [], Counter(), []
        for i, ch in enumerate(chars, start=1):
            char = mapping.get(i)
            if char is None:
                continue
            for taxon in taxa:
                raw = ch['codes'].get(taxon, '')
                status, tokens, note = parse_code(raw)
                linked = []
                if opts['map_states'] and tokens:
                    found = [states.get(char.pk, {}).get(t.lower()) for t in tokens]
                    if all(found):
                        linked = found
                    else:
                        status = 'UNMAPPED'
                        missing = [t for t, s in zip(tokens, found) if s is None]
                        note = (note + f" Code(s) {', '.join(missing)} not defined for this character.").strip()
                        unmatched_codes.append(f"{taxon} / {char.character}: {raw}")
                status_counts[status] += 1
                planned.append(dict(char=char, taxon=taxon, raw=raw, status=status, states=linked,
                                    number=ch['number'] or None, note=note or None))

        n_skipped = len(chars) - len(mapping)
        self.stdout.write(f"{len(mapping)} characters x {len(taxa)} taxa = {len(planned)} codings "
                          f"({n_skipped} matrix rows skipped, no character_id).")
        self.stdout.write('  ' + ', '.join(f"{k}: {v}" for k, v in sorted(status_counts.items())))
        if not opts['map_states']:
            self.stdout.write("  Codes stored as written; not linked to database states (no --map-states).")
        elif unmatched_codes:
            self.stdout.write(self.style.WARNING(f"  {len(unmatched_codes)} codes have no matching state "
                                                 f"(stored as UNMAPPED), e.g. {unmatched_codes[:3]}"))

        existing_links = CharacterPublication.objects.filter(publication=pub, role='CHAR')
        to_prune = existing_links.exclude(character__in=mapping.values())
        if opts['prune_pooled_links']:
            self.stdout.write(f"  Will remove {to_prune.count()} Character-definition links from {pub.citation_key} "
                              f"to characters not in this matrix.")
        else:
            self.stdout.write(f"  {to_prune.count()} existing Character-definition links from {pub.citation_key} "
                              f"point to characters not in this matrix (kept; --prune-pooled-links removes them).")

        if not opts['commit']:
            self.stdout.write(self.style.WARNING('Dry run: nothing written. Add --commit to import.'))
            return

        with transaction.atomic():
            created = updated = 0
            for p in planned:
                obj, made = TaxonCharacterState.objects.update_or_create(
                    character=p['char'], publication=pub, taxon=p['taxon'],
                    defaults=dict(raw_code=p['raw'], status=p['status'],
                                  character_number=p['number'], notes=p['note']))
                obj.states.set(p['states'])
                created += made
                updated += not made
            linked = 0
            for i, char in mapping.items():
                number = chars[i - 1]['number'] or None
                link, made = CharacterPublication.objects.get_or_create(
                    character=char, publication=pub, role='CHAR', defaults={'character_number': number})
                if not made and number and link.character_number != number:
                    link.character_number = number
                    link.save(update_fields=['character_number', 'updated_at'])
                linked += made
            pruned = 0
            if opts['prune_pooled_links']:
                pruned = to_prune.count()
                to_prune.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Imported: {created} new codings, {updated} updated; {linked} new character links"
            f"{f', {pruned} pooled links removed' if opts['prune_pooled_links'] else ''}."))

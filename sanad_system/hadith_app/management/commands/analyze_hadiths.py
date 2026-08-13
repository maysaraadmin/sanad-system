from django.core.management.base import BaseCommand
from hadith_app.models import Hadith, Sanad, SanadNarrator
from hadith_app.utils.sanad_utils import (
    detect_shadh,
    detect_mutawatir,
    validate_chronological_overlap,
    detect_tadlis
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze hadiths for shadh, mutawatir, and other hadith science metadata'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hadith-id',
            type=int,
            help='Analyze a specific hadith ID'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of hadiths to analyze'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update hadith metadata in database'
        )

    def handle(self, *args, **options):
        hadith_id = options.get('hadith_id')
        limit = options.get('limit')
        update = options.get('update', False)
        
        if hadith_id:
            hadiths = Hadith.objects.filter(id=hadith_id)
            if not hadiths.exists():
                self.stdout.write(self.style.ERROR(f'Hadith {hadith_id} not found'))
                return
        else:
            hadiths = Hadith.objects.all()
            if limit:
                hadiths = hadiths[:limit]
        
        total = hadiths.count()
        self.stdout.write(f'Analyzing {total} hadiths...')
        
        shadh_count = 0
        mutawatir_count = 0
        updated_count = 0
        
        for hadith in hadiths:
            try:
                shadh_analysis = detect_shadh(hadith)
                mutawatir_analysis = detect_mutawatir(hadith)
                
                if shadh_analysis['is_shadh']:
                    shadh_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Hadith #{hadith.system_hadith_number} (ID:{hadith.id}) is SHADH: "
                            f"score={shadh_analysis['score']:.2f}, reasons={shadh_analysis['reasons'][:2]}"
                        )
                    )
                
                if mutawatir_analysis['is_mutawatir']:
                    mutawatir_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Hadith #{hadith.system_hadith_number} (ID:{hadith.id}) is MUTAWATIR: "
                            f"chains={mutawatir_analysis['total_chains']}, narrators={mutawatir_analysis['unique_narrators']}"
                        )
                    )
                
                if update:
                    update_fields = []
                    if hadith.anomaly_score != shadh_analysis['score']:
                        hadith.anomaly_score = shadh_analysis['score']
                        update_fields.append('anomaly_score')
                    if hadith.is_shadh != shadh_analysis['is_shadh']:
                        hadith.is_shadh = shadh_analysis['is_shadh']
                        update_fields.append('is_shadh')
                    if not hadith.is_mutawatir and mutawatir_analysis['is_mutawatir']:
                        hadith.is_mutawatir = True
                        update_fields.append('is_mutawatir')
                    
                    if update_fields:
                        hadith.save(update_fields=update_fields)
                        updated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error analyzing hadith {hadith.id}: {e}")
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nAnalysis complete!\n'
                f'Total analyzed: {total}\n'
                f'Shadh hadiths: {shadh_count}\n'
                f'Mutawatir hadiths: {mutawatir_count}\n'
                f'Updated in DB: {updated_count}'
            )
        )

from django.core.management.base import BaseCommand
from library_app.models import DocumentType

class Command(BaseCommand):
    help = 'Adds initial document types to the database'
    
    def handle(self, *args, **options):
        document_types = [
            ('كتاب', 'كتب علمية وبحثية'),
            ('مقال', 'مقالات علمية وبحثية'),
            ('بحث', 'أبحاث ودراسات'),
            ('مذكرة', 'مذكرات دراسية'),
            ('ملاحظات', 'ملاحظات وملخصات'),
            ('وثيقة', 'وثائق ومستندات رسمية'),
            ('صوت', 'ملفات صوتية'),
            ('فيديو', 'ملفات فيديو'),
        ]
        
        for name, description in document_types:
            DocumentType.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully added initial document types'))

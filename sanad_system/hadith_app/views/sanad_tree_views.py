from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from ..models import Hadith, Sanad, SanadNarrator, Narrator
import json

class SanadTreeView(DetailView):
    """View for displaying hadith sanad as an interactive tree"""
    model = Hadith
    template_name = 'hadith_app/sanad_tree.html'
    context_object_name = 'hadith'
    pk_url_kwarg = 'hadith_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hadith = self.get_object()
        
        # Get all sanads for this hadith
        sanads = hadith.asanid.all().prefetch_related('sanadnarrator_set__narrator')
        
        # Build tree data for each sanad
        sanad_trees = []
        for sanad in sanads:
            tree_data = self.build_sanad_tree(sanad)
            sanad_trees.append({
                'sanad': sanad,
                'tree_data': tree_data,
                'tree_json': json.dumps(tree_data, ensure_ascii=False)
            })
        
        context.update({
            'sanad_trees': sanad_trees,
            'total_sanads': sanads.count(),
        })
        
        return context
    
    def build_sanad_tree(self, sanad):
        """Build hierarchical tree structure for a sanad"""
        # Get narrators in order (from Prophet to final narrator)
        from hadith_app.models import SanadNarrator
        sanad_narrators = SanadNarrator.objects.filter(sanad=sanad).select_related('narrator').order_by('order')
        
        nodes = []
        edges = []
        previous_id = None
        
        for i, sanad_narrator in enumerate(sanad_narrators):
            narrator = sanad_narrator.narrator
            
            # Create node for this narrator
            node_id = f"narrator_{narrator.id}_{i}"
            node_data = {
                'id': node_id,
                'name': narrator.name,
                'title': narrator.name,
                'death_year': narrator.death_year,
                'birth_year': narrator.birth_year,
                'reliability': narrator.get_reliability_display() if narrator.reliability else 'غير محدد',
                'biography': narrator.biography[:200] + '...' if narrator.biography and len(narrator.biography) > 200 else narrator.biography,
                'position': i,
                'level': i,  # Each level represents a generation
                'type': 'narrator'
            }
            
            # Add special markers for important positions
            if i == 0:
                node_data['type'] = 'prophet_companion'
                node_data['special'] = 'صحابي'
            elif i == len(sanad_narrators) - 1:
                node_data['type'] = 'final_narrator'
                node_data['special'] = 'راوي الحديث'
            
            nodes.append(node_data)
            
            # Create edge from previous narrator
            if previous_id:
                edges.append({
                    'from': previous_id,
                    'to': node_id,
                    'type': 'narration_chain'
                })
            
            previous_id = node_id
        
        # Add the hadith as final node
        hadith_node = {
            'id': f'hadith_{sanad.hadith.id}',
            'name': 'الحديث',
            'title': sanad.hadith.text[:100] + '...' if len(sanad.hadith.text) > 100 else sanad.hadith.text,
            'type': 'hadith',
            'level': len(sanad_narrators),
            'grade': sanad.hadith.get_grade_display(),
            'source': sanad.hadith.source
        }
        nodes.append(hadith_node)
        
        # Connect last narrator to hadith
        if previous_id:
            edges.append({
                'from': previous_id,
                'to': hadith_node['id'],
                'type': 'hadith_connection'
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'sanad_id': sanad.id,
                'total_narrators': len(sanad_narrators),
                'hadith_grade': sanad.hadith.get_grade_display(),
                'source': sanad.hadith.source
            }
        }

@require_GET
def sanad_comparison_view(request, hadith_id):
    """Compare multiple sanads for a hadith"""
    hadith = get_object_or_404(Hadith, id=hadith_id)
    sanads = hadith.asanid.all().prefetch_related('sanadnarrator_set__narrator')
    
    # Find common narrators and differences
    all_narrators = set()
    sanad_narrator_sets = []
    
    for sanad in sanads:
        narrator_set = set(sn.narrator.id for sn in sanad.sanadnarrator_set.all())
        sanad_narrator_sets.append(narrator_set)
        all_narrators.update(narrator_set)
    
    # Find narrators that appear in multiple sanads
    common_narrators = set()
    if len(sanad_narrator_sets) > 1:
        common_narrators = sanad_narrator_sets[0]
        for narrator_set in sanad_narrator_sets[1:]:
            common_narrators = common_narrators.intersection(narrator_set)
    
    # Find unique narrators for each sanad
    unique_narrators = {}
    for i, narrator_set in enumerate(sanad_narrator_sets):
        unique_narrators[i] = narrator_set - common_narrators
    
    # Prepare sanad data for JavaScript
    sanad_data = []
    common_narrator_ids = common_narrators
    
    for i, sanad in enumerate(sanads):
        narrators_data = []
        sanad_narrators = sanad.sanadnarrator_set.all().order_by('order')
        
        for sn in sanad_narrators:
            narrators_data.append({
                'name': sn.narrator.name,
                'deathYear': sn.narrator.death_year,
                'isCommon': sn.narrator.id in common_narrator_ids
            })
        
        sanad_data.append({
            'path': i + 1,
            'narrators': narrators_data
        })
    
    import json
    context = {
        'hadith': hadith,
        'sanads': sanads,
        'common_narrators': Narrator.objects.filter(id__in=common_narrators),
        'unique_narrators': {
            i: Narrator.objects.filter(id__in=narrator_ids) 
            for i, narrator_ids in unique_narrators.items()
        },
        'total_paths': sanads.count(),
        'total_common': len(common_narrators),
        'sanad_data_json': json.dumps(sanad_data, ensure_ascii=False),
    }
    
    return render(request, 'hadith_app/sanad_comparison.html', context)

@require_GET
def narrator_paths_api(request, narrator_id):
    """API to get all hadiths that include a specific narrator"""
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Find all sanads where this narrator appears
    sanad_narrators = SanadNarrator.objects.filter(narrator=narrator).select_related('sanad__hadith')
    
    paths = []
    for sn in sanad_narrators:
        sanad = sn.sanad
        hadith = sanad.hadith
        
        # Get full chain for this path
        chain = []
        sanad_narrators_in_chain = sanad.sanadnarrator_set.all().order_by('order')
        
        for chain_sn in sanad_narrators_in_chain:
            chain.append({
                'narrator': chain_sn.narrator.name,
                'position': chain_sn.order,
                'is_target': chain_sn.narrator.id == narrator.id
            })
        
        paths.append({
            'hadith_id': hadith.id,
            'hadith_text': hadith.text[:150] + '...' if len(hadith.text) > 150 else hadith.text,
            'hadith_grade': hadith.get_grade_display(),
            'source': hadith.source,
            'position_in_chain': sn.order,
            'total_narrators': sanad_narrators_in_chain.count(),
            'chain': chain
        })
    
    return JsonResponse({
        'narrator': {
            'id': narrator.id,
            'name': narrator.name,
            'death_year': narrator.death_year,
            'reliability': narrator.get_reliability_display() if narrator.reliability else None
        },
        'total_paths': len(paths),
        'paths': paths
    })

"""
Narrator Analysis Views

This module provides comprehensive analysis tools for hadith narrators,
including relationship networks, timelines, geographical maps, and comparisons.
"""
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext as _
import json
from hadith_app.models import Narrator, Hadith, SanadNarrator, Sanad
import json
from collections import defaultdict
from datetime import datetime


@require_http_methods(["GET"])
def hadith_comparison_api(request, hadith_ids):
    """
    API endpoint for comparing multiple hadith narrations.
    Returns detailed information about each hadith for side-by-side comparison.
    """
    try:
        # Convert comma-separated string of IDs to a list of integers
        hadith_id_list = [int(id) for id in hadith_ids.split(',')]
        
        # Get all hadiths with their related data
        hadiths = Hadith.objects.filter(id__in=hadith_id_list).select_related(
            'book', 'sanad'
        ).prefetch_related(
            'narrators', 'asanid__narrators'
        )
        
        # Prepare the response data
        comparison_data = []
        for hadith in hadiths:
            # Get all narrators in the chain
            narrators = []
            for sanad in hadith.asanid.all():
                for narrator in sanad.narrators.all():
                    narrators.append({
                        'id': narrator.id,
                        'name': narrator.name,
                        'reliability': narrator.get_reliability_display(),
                        'madhhab': narrator.get_madhhab_display() if narrator.madhhab else None,
                        'birth_year': narrator.birth_year,
                        'death_year': narrator.death_year,
                        'age': narrator.get_age()
                    })
            
            # Get hadith details
            hadith_data = {
                'id': hadith.id,
                'text': hadith.text,
                'book': hadith.book.title if hadith.book else None,
                'source': hadith.source,
                'grade': hadith.grade,
                'narrators': narrators,
                'sanad': hadith.sanad.text if hadith.sanad else None,
                'created_at': hadith.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': hadith.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hadith.updated_at else None
            }
            comparison_data.append(hadith_data)
        
        return JsonResponse({
            'status': 'success',
            'count': len(comparison_data),
            'results': comparison_data
        }, encoder=DjangoJSONEncoder)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@require_GET
def narrator_analysis_view(request, narrator_id):
    """
    Comprehensive narrator analysis view with relationship network,
    timeline, geographical map, and comparison tools.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Get all hadiths where this narrator appears
    hadiths = Hadith.objects.filter(asanid__narrators=narrator).distinct()
    
    # Get teacher-student relationships
    teachers = narrator.teachers.all()
    students = narrator.students.all()
    
    # Get contemporaries
    contemporaries = narrator.get_contemporaries()
    
    # Get narration locations
    locations = narrator.get_narration_locations()
    
    # Get hadith statistics by source
    source_stats = hadiths.values('source').annotate(count=Count('id')).order_by('-count')
    
    # Get reliability distribution of narrators in hadiths with this narrator
    reliability_stats = {}
    for hadith in hadiths:
        for sanad in hadith.asanid.all():
            for sn in sanad.sanadnarrator_set.all():
                rel = sn.narrator.get_reliability_display()
                reliability_stats[rel] = reliability_stats.get(rel, 0) + 1
    
    context = {
        'narrator': narrator,
        'hadiths': hadiths[:10],  # Limit to 10 for display
        'total_hadiths': hadiths.count(),
        'teachers': teachers,
        'students': students,
        'contemporaries': contemporaries[:10],
        'locations': locations,
        'source_stats': source_stats[:5],
        'reliability_stats': reliability_stats,
        'age': narrator.get_age(),
        'madhhab': narrator.get_madhhab_display(),
    }
    
    return render(request, 'hadith_app/narrator_analysis.html', context)


@require_GET
def narrator_relationship_network_api(request, narrator_id):
    """
    API endpoint for narrator relationship network visualization.
    Returns data in format suitable for network graph visualization.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Build network data
    nodes = []
    edges = []
    node_ids = set()
    
    # Add the main narrator
    nodes.append({
        'id': narrator.id,
        'name': narrator.name,
        'type': 'target',
        'reliability': narrator.get_reliability_display(),
        'birth_year': narrator.birth_year,
        'death_year': narrator.death_year,
        'madhhab': narrator.get_madhhab_display()
    })
    node_ids.add(narrator.id)
    
    # Add teachers
    for teacher in narrator.teachers.all():
        if teacher.id not in node_ids:
            nodes.append({
                'id': teacher.id,
                'name': teacher.name,
                'type': 'teacher',
                'reliability': teacher.get_reliability_display(),
                'birth_year': teacher.birth_year,
                'death_year': teacher.death_year,
                'madhhab': teacher.get_madhhab_display()
            })
            node_ids.add(teacher.id)
        
        edges.append({
            'from': teacher.id,
            'to': narrator.id,
            'type': 'teacher_student'
        })
    
    # Add students
    for student in narrator.students.all():
        if student.id not in node_ids:
            nodes.append({
                'id': student.id,
                'name': student.name,
                'type': 'student',
                'reliability': student.get_reliability_display(),
                'birth_year': student.birth_year,
                'death_year': student.death_year,
                'madhhab': student.get_madhhab_display()
            })
            node_ids.add(student.id)
        
        edges.append({
            'from': narrator.id,
            'to': student.id,
            'type': 'teacher_student'
        })
    
    # Add contemporaries with connections
    for contemporary in narrator.get_contemporaries()[:20]:
        if contemporary.id not in node_ids:
            nodes.append({
                'id': contemporary.id,
                'name': contemporary.name,
                'type': 'contemporary',
                'reliability': contemporary.get_reliability_display(),
                'birth_year': contemporary.birth_year,
                'death_year': contemporary.death_year,
                'madhhab': contemporary.get_madhhab_display()
            })
            node_ids.add(contemporary.id)
        
        # Add weak connection to contemporaries
        edges.append({
            'from': narrator.id,
            'to': contemporary.id,
            'type': 'contemporary'
        })
    
    return JsonResponse({
        'nodes': nodes,
        'edges': edges
    })


@require_GET
def narrator_timeline_api(request, narrator_id):
    """
    API endpoint for narrator timeline visualization.
    Returns timeline data including life events and hadith narrations.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    events = []
    
    # Birth event
    if narrator.birth_year:
        events.append({
            'year': narrator.birth_year,
            'type': 'birth',
            'title': 'الولادة',
            'description': f'ولادة {narrator.name} في {narrator.birth_place or "مكان غير محدد"}',
            'importance': 10
        })
    
    # Death event
    if narrator.death_year:
        events.append({
            'year': narrator.death_year,
            'type': 'death',
            'title': 'الوفاة',
            'description': f'وفاة {narrator.name} في {narrator.death_place or "مكان غير محدد"}',
            'importance': 10
        })
    
    # Teacher-student relationships (estimated years)
    for teacher in narrator.teachers.all():
        if teacher.death_year and narrator.birth_year:
            # Estimate when narration might have occurred
            narration_year = max(narrator.birth_year + 15, teacher.death_year - 20)
            if narration_year <= teacher.death_year and narration_year >= narrator.birth_year + 10:
                events.append({
                    'year': narration_year,
                    'type': 'narration',
                    'title': 'رواية عن شيخ',
                    'description': f'رواية {narrator.name} عن {teacher.name}',
                    'importance': 5
                })
    
    # Student narrations
    for student in narrator.students.all():
        if narrator.death_year and student.birth_year:
            narration_year = min(narrator.death_year - 5, student.birth_year + 30)
            if narration_year >= narrator.birth_year + 20 and narration_year <= narrator.death_year:
                events.append({
                    'year': narration_year,
                    'type': 'teaching',
                    'title': 'تلميذ يروي عنه',
                    'description': f'رواية {student.name} عن {narrator.name}',
                    'importance': 5
                })
    
    # Sort events by year
    events.sort(key=lambda x: x['year'])
    
    # Add contemporaries' timelines for context
    contemporaries_timeline = []
    for contemporary in narrator.get_contemporaries()[:10]:
        if contemporary.birth_year:
            contemporaries_timeline.append({
                'name': contemporary.name,
                'birth_year': contemporary.birth_year,
                'death_year': contemporary.death_year,
                'reliability': contemporary.get_reliability_display()
            })
    
    return JsonResponse({
        'events': events,
        'contemporaries': contemporaries_timeline,
        'narrator_info': {
            'name': narrator.name,
            'birth_year': narrator.birth_year,
            'death_year': narrator.death_year,
            'age': narrator.get_age()
        }
    })


@require_GET
def narrator_geographical_api(request, narrator_id):
    """
    API endpoint for narrator geographical distribution.
    Returns location data for narrations and relationships.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    locations = []
    
    # Birth place
    if narrator.birth_place:
        locations.append({
            'name': narrator.birth_place,
            'type': 'birth',
            'year': narrator.birth_year,
            'description': f'مولد {narrator.name}',
            'importance': 10
        })
    
    # Death place
    if narrator.death_place and narrator.death_place != narrator.birth_place:
        locations.append({
            'name': narrator.death_place,
            'type': 'death',
            'year': narrator.death_year,
            'description': f'وفاة {narrator.name}',
            'importance': 10
        })
    
    # Teachers' locations
    for teacher in narrator.teachers.all():
        if teacher.birth_place:
            locations.append({
                'name': teacher.birth_place,
                'type': 'teacher_location',
                'year': teacher.birth_year,
                'description': f'شيخه {teacher.name}',
                'importance': 5
            })
    
    # Students' locations
    for student in narrator.students.all():
        if student.birth_place:
            locations.append({
                'name': student.birth_place,
                'type': 'student_location',
                'year': student.birth_year,
                'description': f'تلميذه {student.name}',
                'importance': 5
            })
    
    # Remove duplicates and sort by importance
    unique_locations = {}
    for loc in locations:
        key = loc['name']
        if key not in unique_locations or loc['importance'] > unique_locations[key]['importance']:
            unique_locations[key] = loc
    
    return JsonResponse({
        'locations': list(unique_locations.values()),
        'narrator_info': {
            'name': narrator.name,
            'birth_place': narrator.birth_place,
            'death_place': narrator.death_place
        }
    })


@require_GET
def narrator_comparison_api(request, narrator_id):
    """
    API endpoint for comparing narrator with teachers and students.
    Returns comparative analysis data.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Get statistics for teachers
    teachers_stats = []
    for teacher in narrator.teachers.all():
        teacher_hadiths = Hadith.objects.filter(asanid__narrators=teacher).distinct()
        teachers_stats.append({
            'id': teacher.id,
            'name': teacher.name,
            'reliability': teacher.get_reliability_display(),
            'madhhab': teacher.get_madhhab_display(),
            'hadith_count': teacher_hadiths.count(),
            'birth_year': teacher.birth_year,
            'death_year': teacher.death_year,
            'age': teacher.get_age()
        })
    
    # Get statistics for students
    students_stats = []
    for student in narrator.students.all():
        student_hadiths = Hadith.objects.filter(asanid__narrators=student).distinct()
        students_stats.append({
            'id': student.id,
            'name': student.name,
            'reliability': student.get_reliability_display(),
            'madhhab': student.get_madhhab_display(),
            'hadith_count': student_hadiths.count(),
            'birth_year': student.birth_year,
            'death_year': student.death_year,
            'age': student.get_age()
        })
    
    # Calculate averages for comparison
    all_hadiths = Hadith.objects.filter(asanid__narrators=narrator).distinct()
    narrator_stats = {
        'id': narrator.id,
        'name': narrator.name,
        'reliability': narrator.get_reliability_display(),
        'madhhab': narrator.get_madhhab_display(),
        'hadith_count': all_hadiths.count(),
        'birth_year': narrator.birth_year,
        'death_year': narrator.death_year,
        'age': narrator.get_age()
    }
    
    # Calculate teacher averages
    if teachers_stats:
        avg_teacher_age = sum(t['age'] or 0 for t in teachers_stats) / len([t for t in teachers_stats if t['age']])
        avg_teacher_hadiths = sum(t['hadith_count'] for t in teachers_stats) / len(teachers_stats)
    else:
        avg_teacher_age = 0
        avg_teacher_hadiths = 0
    
    # Calculate student averages
    if students_stats:
        avg_student_age = sum(s['age'] or 0 for s in students_stats) / len([s for s in students_stats if s['age']])
        avg_student_hadiths = sum(s['hadith_count'] for s in students_stats) / len(students_stats)
    else:
        avg_student_age = 0
        avg_student_hadiths = 0
    
    return JsonResponse({
        'narrator': narrator_stats,
        'teachers': teachers_stats,
        'students': students_stats,
        'averages': {
            'teachers': {
                'age': avg_teacher_age,
                'hadith_count': avg_teacher_hadiths
            },
            'students': {
                'age': avg_student_age,
                'hadith_count': avg_student_hadiths
            }
        }
    })


@require_GET
def narrator_hadith_paths_api(request, narrator_id):
    """
    API endpoint to get all hadith paths where this narrator appears.
    Returns chain information for each hadith.
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Get all sanad narrators where this narrator appears
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
                'is_target': chain_sn.narrator.id == narrator.id,
                'reliability': chain_sn.narrator.get_reliability_display(),
                'narration_method': chain_sn.narration_method
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
            'reliability': narrator.get_reliability_display()
        },
        'total_paths': len(paths),
        'paths': paths[:50]  # Limit to 50 paths for performance
    })

"""
Student Management Views

This module provides views for managing students of narrators,
similar to the teacher management system.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _
from hadith_app.models import Narrator, TeacherStudentRelationship


@require_GET
def add_student_view(request, narrator_id):
    """
    Display form to add a student to a narrator
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    
    # Get all narrators who are not already students of this narrator
    existing_student_ids = narrator.student_relationships.values_list('student_id', flat=True)
    available_students = Narrator.objects.exclude(
        id__in=list(existing_student_ids) + [narrator.id]
    ).order_by('name')
    
    # Get current students for display
    current_students = Narrator.objects.filter(
        teacher_relationships__teacher=narrator
    ).order_by('name')
    
    context = {
        'narrator': narrator,
        'available_students': available_students,
        'current_students': current_students
    }
    
    return render(request, 'hadith_app/add_student.html', context)


@login_required
@require_POST
def add_student_submit(request, narrator_id):
    """
    Process the form to add a student to a narrator
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    student_id = request.POST.get('student_id')
    notes = request.POST.get('notes', '')
    
    if not student_id:
        messages.error(request, _('يرجى اختيار طالب'))
        return redirect('hadith_app:add_student', narrator_id=narrator_id)
    
    try:
        student = Narrator.objects.get(id=student_id)
        
        # Check if relationship already exists
        if TeacherStudentRelationship.objects.filter(
            teacher=narrator, 
            student=student
        ).exists():
            messages.warning(request, _('هذا الطالب موجود بالفعل'))
        else:
            # Create the relationship
            TeacherStudentRelationship.objects.create(
                teacher=narrator,
                student=student,
                notes=notes
            )
            messages.success(request, _('تم إضافة الطالب بنجاح'))
            
    except Narrator.DoesNotExist:
        messages.error(request, _('الطالب المحدد غير موجود'))
    
    return redirect('hadith_app:narrator_analysis', narrator_id=narrator_id)


@login_required
@require_POST
def remove_student(request, narrator_id, student_id):
    """
    Remove a student from a narrator
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    student = get_object_or_404(Narrator, id=student_id)
    
    try:
        relationship = TeacherStudentRelationship.objects.get(
            teacher=narrator,
            student=student
        )
        relationship.delete()
        messages.success(request, _('تم إزالة الطالب بنجاح'))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('تم إزالة الطالب بنجاح')
            })
            
    except TeacherStudentRelationship.DoesNotExist:
        messages.error(request, _('علاقة التلمذة غير موجودة'))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('علاقة التلمذة غير موجودة')
            })
    
    return redirect('hadith_app:narrator_analysis', narrator_id=narrator_id)


@require_GET
def student_list_view(request, narrator_id):
    """
    Display list of all students for a narrator
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    students = Narrator.objects.filter(
        teacher_relationships__teacher=narrator
    ).order_by('name')
    
    # Get relationship details
    student_relationships = TeacherStudentRelationship.objects.filter(
        teacher=narrator
    ).select_related('student')
    
    context = {
        'narrator': narrator,
        'students': students,
        'student_relationships': student_relationships
    }
    
    return render(request, 'hadith_app/student_list.html', context)


@login_required
@require_POST
def update_student_notes(request, narrator_id, student_id):
    """
    Update notes for a teacher-student relationship
    """
    narrator = get_object_or_404(Narrator, id=narrator_id)
    student = get_object_or_404(Narrator, id=student_id)
    notes = request.POST.get('notes', '')
    
    try:
        relationship = TeacherStudentRelationship.objects.get(
            teacher=narrator,
            student=student
        )
        relationship.notes = notes
        relationship.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('تم تحديث الملاحظات بنجاح'),
                'notes': notes
            })
        
        messages.success(request, _('تم تحديث الملاحظات بنجاح'))
        
    except TeacherStudentRelationship.DoesNotExist:
        messages.error(request, _('علاقة التلمذة غير موجودة'))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('علاقة التلمذة غير موجودة')
            })
    
    return redirect('hadith_app:student_list', narrator_id=narrator_id)

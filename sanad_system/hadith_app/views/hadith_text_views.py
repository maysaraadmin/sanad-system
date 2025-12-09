"""
Hadith Text Views

This module provides views for managing multiple text versions of hadiths,
including adding, editing, and managing different narrations.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _
from hadith_app.models import Hadith, HadithText
from hadith_app.forms import AddHadithTextForm, HadithTextForm


@require_GET
def hadith_texts_view(request, hadith_id):
    """
    Display all text versions of a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    texts = hadith.get_all_texts()
    
    context = {
        'hadith': hadith,
        'texts': texts,
        'text_count': hadith.get_text_count(),
        'primary_text': hadith.get_primary_text()
    }
    
    return render(request, 'hadith_app/hadith_texts.html', context)


@require_GET
def add_hadith_text_view(request, hadith_id):
    """
    Display form to add a new text version to a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    form = AddHadithTextForm()
    
    context = {
        'hadith': hadith,
        'form': form,
        'current_texts': hadith.get_all_texts().order_by('-is_primary', 'created_at')
    }
    
    return render(request, 'hadith_app/add_hadith_text.html', context)


@require_POST
def add_hadith_text_submit(request, hadith_id):
    """
    Process form submission to add a new text version to a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    form = AddHadithTextForm(request.POST)
    
    if form.is_valid():
        # If making this text primary, first unset current primary
        if form.cleaned_data.get('make_primary', False):
            HadithText.objects.filter(hadith=hadith, is_primary=True).update(is_primary=False)
        
        # Create the new text
        new_text = HadithText.objects.create(
            hadith=hadith,
            text=form.cleaned_data['text'],
            source_reference=form.cleaned_data.get('source_reference', ''),
            narrator_chain=form.cleaned_data.get('narrator_chain', ''),
            variation_notes=form.cleaned_data.get('variation_notes', ''),
            is_primary=form.cleaned_data.get('make_primary', False)
        )
        
        # If this is the first text, make it primary
        if hadith.get_text_count() == 1:
            new_text.is_primary = True
            new_text.save()
        
        # Update the main hadith text if this is primary
        if new_text.is_primary:
            hadith.text = new_text.text
            hadith.save()
        
        messages.success(request, f'تم إضافة نص جديد للحديث بنجاح')
        return redirect('hadith_app:hadith_texts', hadith_id=hadith.id)
    else:
        context = {
            'hadith': hadith,
            'form': form,
            'current_texts': hadith.get_all_texts().order_by('-is_primary', 'created_at')
        }
        return render(request, 'hadith_app/add_hadith_text.html', context)


@require_POST
def set_primary_text(request, hadith_id, text_id):
    """
    Set a specific text as the primary text for a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    new_primary = get_object_or_404(HadithText, id=text_id, hadith=hadith)
    
    # Unset current primary
    HadithText.objects.filter(hadith=hadith, is_primary=True).update(is_primary=False)
    
    # Set new primary
    new_primary.is_primary = True
    new_primary.save()
    
    # Update main hadith text
    hadith.text = new_primary.text
    hadith.save()
    
    messages.success(request, f'تم تعيين النص المحدد كنص أساسي للحديث')
    return redirect('hadith_app:hadith_texts', hadith_id=hadith.id)


@require_POST
def delete_hadith_text(request, hadith_id, text_id):
    """
    Delete a text version from a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    text_to_delete = get_object_or_404(HadithText, id=text_id, hadith=hadith)
    
    # Don't allow deletion of primary text if it's the only text
    if hadith.get_text_count() == 1:
        messages.error(request, 'لا يمكن حذف النص الوحيد للحديث')
        return redirect('hadith_app:hadith_texts', hadith_id=hadith.id)
    
    # If deleting primary text, set another text as primary
    if text_to_delete.is_primary:
        remaining_texts = HadithText.objects.filter(hadith=hadith).exclude(id=text_id)
        if remaining_texts.exists():
            new_primary = remaining_texts.first()
            new_primary.is_primary = True
            new_primary.save()
            hadith.text = new_primary.text
            hadith.save()
    
    text_to_delete.delete()
    messages.success(request, f'تم حذف نص الحديث بنجاح')
    return redirect('hadith_app:hadith_texts', hadith_id=hadith.id)


@require_GET
def hadith_text_comparison_view(request, hadith_id):
    """
    Display comparison view for all text versions of a hadith
    """
    hadith = get_object_or_404(Hadith, id=hadith_id)
    texts = hadith.get_all_texts()
    
    context = {
        'hadith': hadith,
        'texts': texts,
        'primary_text': hadith.get_primary_text()
    }
    
    return render(request, 'hadith_app/hadith_text_comparison.html', context)

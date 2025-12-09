"""
Sanad Narrator Views

This module provides views for managing narrators within a specific sanad,
including adding, removing, and reordering narrators in the chain.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.db import models
from hadith_app.models import Hadith, Sanad, SanadNarrator, Narrator
from hadith_app.forms import SanadNarratorForm


@require_GET
def sanad_narrators_view(request, sanad_id):
    """
    Display all narrators in a sanad with management options
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    narrators = sanad.sanadnarrator_set.all().order_by('order')
    
    context = {
        'sanad': sanad,
        'hadith': sanad.hadith,
        'narrators': narrators,
        'available_narrators': Narrator.objects.exclude(id__in=sanad.narrators.all()).order_by('name')
    }
    
    return render(request, 'hadith_app/sanad_narrators.html', context)


@require_GET
def add_sanad_narrator_view(request, sanad_id):
    """
    Display form to add a narrator to a sanad
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    form = SanadNarratorForm()
    
    # Exclude narrators already in this sanad
    form.fields['narrator'].queryset = Narrator.objects.exclude(id__in=sanad.narrators.all()).order_by('name')
    
    context = {
        'sanad': sanad,
        'hadith': sanad.hadith,
        'form': form,
        'current_narrators': sanad.sanadnarrator_set.all().order_by('order')
    }
    
    return render(request, 'hadith_app/add_sanad_narrator.html', context)


@require_POST
def add_sanad_narrator_submit(request, sanad_id):
    """
    Process form submission to add a narrator to a sanad
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    form = SanadNarratorForm(request.POST)
    
    # Exclude narrators already in this sanad
    form.fields['narrator'].queryset = Narrator.objects.exclude(id__in=sanad.narrators.all()).order_by('name')
    
    if form.is_valid():
        narrator = form.cleaned_data['narrator']
        order = form.cleaned_data['order']
        
        # If order is not specified, add to the end
        if not order:
            order = sanad.sanadnarrator_set.count() + 1
        
        # Shift existing narrators if needed
        if order <= sanad.sanadnarrator_set.count():
            SanadNarrator.objects.filter(sanad=sanad, order__gte=order).update(order=models.F('order') + 1)
        
        # Create the new sanad-narrator relationship
        SanadNarrator.objects.create(
            sanad=sanad,
            narrator=narrator,
            order=order,
            narration_method=form.cleaned_data.get('narration_method', '')
        )
        
        messages.success(request, f'تم إضافة الراوي {narrator.name} إلى السند بنجاح')
        return redirect('hadith_app:sanad_narrators', sanad_id=sanad.id)
    else:
        context = {
            'sanad': sanad,
            'hadith': sanad.hadith,
            'form': form,
            'current_narrators': sanad.sanadnarrator_set.all().order_by('order')
        }
        return render(request, 'hadith_app/add_sanad_narrator.html', context)


@require_POST
def remove_sanad_narrator(request, sanad_id, narrator_id):
    """
    Remove a narrator from a sanad
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    sanad_narrator = get_object_or_404(SanadNarrator, sanad=sanad, narrator_id=narrator_id)
    
    narrator_name = sanad_narrator.narrator.name
    removed_order = sanad_narrator.order
    
    # Remove the narrator
    sanad_narrator.delete()
    
    # Reorder remaining narrators
    SanadNarrator.objects.filter(sanad=sanad, order__gt=removed_order).update(order=models.F('order') - 1)
    
    messages.success(request, f'تم إزالة الراوي {narrator_name} من السند بنجاح')
    return redirect('hadith_app:sanad_narrators', sanad_id=sanad.id)


@require_POST
def reorder_sanad_narrators(request, sanad_id):
    """
    Reorder narrators in a sanad (AJAX endpoint)
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            narrator_orders = request.POST.getlist('narrator_orders[]')
            
            for item in narrator_orders:
                narrator_id, new_order = item.split(':')
                SanadNarrator.objects.filter(
                    sanad=sanad, 
                    narrator_id=narrator_id
                ).update(order=int(new_order))
            
            return JsonResponse({'success': True, 'message': 'تم إعادة ترتيب الرواة بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'طلب غير صالح'})


@require_POST
def update_sanad_narrator(request, sanad_id, narrator_id):
    """
    Update narrator details in a sanad
    """
    sanad = get_object_or_404(Sanad, id=sanad_id)
    sanad_narrator = get_object_or_404(SanadNarrator, sanad=sanad, narrator_id=narrator_id)
    
    if request.method == 'POST':
        narration_method = request.POST.get('narration_method', '')
        order = request.POST.get('order')
        
        # Update narration method
        if narration_method:
            sanad_narrator.narration_method = narration_method
        
        # Update order if changed
        if order and int(order) != sanad_narrator.order:
            old_order = sanad_narrator.order
            new_order = int(order)
            
            # Shift other narrators
            if new_order > old_order:
                SanadNarrator.objects.filter(
                    sanad=sanad, 
                    order__gt=old_order, 
                    order__lte=new_order
                ).update(order=models.F('order') - 1)
            else:
                SanadNarrator.objects.filter(
                    sanad=sanad, 
                    order__gte=new_order, 
                    order__lt=old_order
                ).update(order=models.F('order') + 1)
            
            sanad_narrator.order = new_order
        
        sanad_narrator.save()
        messages.success(request, f'تم تحديث بيانات الراوي بنجاح')
    
    return redirect('hadith_app:sanad_narrators', sanad_id=sanad.id)

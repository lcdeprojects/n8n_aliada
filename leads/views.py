from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.template.loader import render_to_string
import json

from .models import Lead, StatusHistory

def get_kanban_data(request):
    leads = Lead.objects.filter(is_active=True).order_by('-updated_at')
    
    # Group leads
    grouped_leads = {status: leads.filter(status=status) for status, label in Lead.STATUS_CHOICES}
    
    # Construct HTML for each column
    columns_html = {}
    
    for status, label in Lead.STATUS_CHOICES:
        leads_in_col = grouped_leads[status]
        html = ''
        for lead in leads_in_col:
            html += render_to_string('leads/includes/lead_card.html', {'lead': lead, 'status_choices': Lead.STATUS_CHOICES})
            
        columns_html[status] = {
            'html': html,
            'count': leads_in_col.count(),
            'total_value': leads_in_col.aggregate(total=Sum('value'))['total'] or 0.00
        }
        
    return JsonResponse({'columns': columns_html})

def lead_dashboard(request):
    status_choices = Lead.STATUS_CHOICES
    leads = Lead.objects.filter(is_active=True).order_by('-updated_at')
    
    columns_data = []
    for status, label in status_choices:
        qs = leads.filter(status=status)
        total_val = qs.aggregate(total=Sum('value'))['total'] or 0.00
        columns_data.append({
            'val': status,
            'label': label,
            'count': qs.count(),
            'total_value': total_val,
            'leads': qs
        })
    
    context = {
        'status_choices': status_choices,
        'columns_data': columns_data,
    }
    return render(request, 'leads/dashboard.html', context)


@require_POST
def update_lead_status(request):
    try:
        # Support JSON payloads for API/fetch requests
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        lead_id = data.get('lead_id')
        new_status = data.get('status')
        
        if not lead_id or not new_status:
            return JsonResponse({'success': False, 'error': 'Parâmetros ausentes.'}, status=400)
            
        lead = Lead.objects.get(id=lead_id)
        old_status = lead.status
        
        if old_status != new_status:
            # Update Lead and reset follow-up tracking
            lead.status = new_status
            lead.followup_stage = 0
            lead.last_followup_at = None
            lead.save()
            
            # Log history
            changed_by = request.user if request.user.is_authenticated else None
            StatusHistory.objects.create(
                lead=lead,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by
            )
            
        return JsonResponse({'success': True})
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def add_lead(request):
    try:
        if request.method == 'POST':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            status = request.POST.get('status', 'atendimento')
            is_active = request.POST.get('is_active', True)
            
            if name and phone:
                # Standardize phone number format (remove non-digits or keep simple)
                clean_phone = ''.join(filter(str.isdigit, phone))
                
                # Get or create lead by phone number
                lead, created = Lead.objects.get_or_create(
                    phone=clean_phone,
                    defaults={'name': name, 'status': status}
                )
                
                if not created:
                    # If lead already exists, just update name and status
                    lead.name = name
                    old_status = lead.status
                    if old_status != status:
                        lead.status = status
                        lead.followup_stage = 0
                        lead.last_followup_at = None
                        lead.is_active = True
                        lead.save()
                        StatusHistory.objects.create(
                            lead=lead,
                            old_status=old_status,
                            new_status=status,
                            changed_by=request.user if request.user.is_authenticated else None
                        )
                    else:
                        lead.save()
                        
            return redirect('lead_dashboard')
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)\

def delete_lead(request, lead_id):
    try:
        lead = Lead.objects.get(id=lead_id)
        lead.is_active = False
        lead.save()
        return JsonResponse({'success': True})
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def chatwoot_webhook(request):
    try:
        data = json.loads(request.body)
        
        # O webhook do Chatwoot envia o evento no campo 'event'
        event = data.get('event')
        
        if event in ['contact_created', 'conversation_created']:
            sender = data.get('meta', {}).get('sender', {})
            # Se for contact_created, os dados podem vir na raiz
            if not sender:
                sender = data
                
            chatwoot_id = sender.get('id')
            name = sender.get('name', 'Novo Paciente')
            phone = sender.get('phone_number', '')
            
            if not phone:
                return JsonResponse({'status': 'ignored', 'reason': 'Sem telefone'})
                
            # Limpa o telefone
            phone = ''.join(filter(str.isdigit, str(phone)))
            
            # Cria ou atualiza o lead
            lead, created = Lead.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'chatwoot_id': chatwoot_id,
                    'status': 'novo_lead'
                }
            )
            
            if not created and not lead.chatwoot_id:
                lead.chatwoot_id = chatwoot_id
                lead.save()
                
            return JsonResponse({'status': 'success', 'created': created})
            
        return JsonResponse({'status': 'ignored', 'event': event})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
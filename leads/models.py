from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import localtime
import json

class Lead(models.Model):
    STATUS_CHOICES = [
        ('novo_lead', 'Novo Lead'),
        ('qualificacao', 'Em Qualificação'),
        ('orcamento', 'Orçamento Enviado'),
        ('agendado', 'Consulta Agendada'),
        ('em_tratamento', 'Em Tratamento'),
        ('ganho', 'Tratamento Concluído'),
        ('perdido', 'Perdido / Não Converteu'),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome do Lead")
    phone = models.CharField(max_length=20, verbose_name="WhatsApp")
    status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='novo_lead',
        verbose_name="Status/Etapa"
    )
    
    # Novos campos de CRM Hubspot-like
    chatwoot_id = models.IntegerField(null=True, blank=True, verbose_name="ID no Chatwoot")
    next_followup_date = models.DateTimeField(null=True, blank=True, verbose_name="Próximo Follow-up")
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor Estimado (R$)")

    last_interaction = models.DateTimeField(auto_now=True, verbose_name="Última Interação")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Colunas de controle contra duplicidade de follow-ups
    followup_stage = models.IntegerField(default=0, verbose_name="Estágio de Follow-Up")
    last_followup_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Follow-Up em")

    class Meta:
        ordering = ['-last_interaction']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    @property
    def status_history(self):
        return self.status_histories.all()

    def __str__(self):
        return f"{self.name} ({self.phone}) - {self.get_status_display()}"


class StatusHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='status_histories', verbose_name="Lead")
    old_status = models.CharField(max_length=50, choices=Lead.STATUS_CHOICES, verbose_name="Status Anterior")
    new_status = models.CharField(max_length=50, choices=Lead.STATUS_CHOICES, verbose_name="Novo Status")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Alterado em")
    changed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Alterado por"
    )

    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Histórico de Status"
        verbose_name_plural = "Históricos de Status"

    def __str__(self):
        return f"{self.lead.name}: {self.old_status} → {self.new_status} em {self.changed_at.strftime('%d/%m/%Y %H:%M')}"

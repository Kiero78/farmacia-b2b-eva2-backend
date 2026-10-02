"""
============================================================================
ADMIN.PY - Registro de modelos en el Admin de Django (App 'usuarios')
============================================================================
Registra el modelo Perfil en el panel de administración de Django para
que los administradores puedan gestionar perfiles de usuario desde la
interfaz web del admin (/admin/).
============================================================================
"""

from django.contrib import admin
from .models import Tenant, Perfil


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Configuración admin para el modelo Tenant (Multi-Tenant)."""
    list_display = ('nombre', 'codigo', 'rut', 'telefono', 'activo', 'creado_en')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo', 'rut')


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    """Configuración admin para el modelo Perfil."""
    list_display = ('user', 'rol', 'tenant', 'nombre_institucion')
    list_filter = ('rol', 'tenant')
    search_fields = ('user__username', 'nombre_institucion', 'tenant__nombre')

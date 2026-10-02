"""
============================================================================
ADMIN.PY - Registro de modelos en el Admin de Django (App 'insumos')
============================================================================
Registra todos los modelos de la app 'insumos' en el panel de administración
de Django. Incluye configuración personalizada para cada modelo con
list_display, filtros, búsqueda e inlines.
============================================================================
"""

from django.contrib import admin
from .models import (
    CategoriaInsumo,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
    RecetaMedica,
)


# ============================================================================
# Admin: CategoriaInsumo
# ============================================================================
@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    """Configuración admin para CategoriaInsumo."""
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


# ============================================================================
# Admin: Insumo
# ============================================================================
@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    """Configuración admin para Insumo."""
    list_display = (
        'nombre_comercial', 'principio_activo', 'categoria', 'tenant',
        'tipo_venta', 'requiere_receta', 'es_medicamento_controlado',
        'lote', 'fecha_vencimiento', 'precio_unitario', 'stock_cajas'
    )
    list_filter = ('tipo_venta', 'requiere_receta', 'es_medicamento_controlado', 'categoria', 'tenant')
    search_fields = ('nombre_comercial', 'principio_activo', 'lote')


# ============================================================================
# Inline: ItemCarro (se muestra dentro del admin de Carro)
# ============================================================================
class ItemCarroInline(admin.TabularInline):
    model = ItemCarro
    extra = 0


# ============================================================================
# Admin: Carro
# ============================================================================
@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    list_display = ('user', 'estado')
    list_filter = ('estado',)
    inlines = [ItemCarroInline]


# ============================================================================
# Inline: ItemSolicitud y RecetaMedica
# ============================================================================
class ItemSolicitudInline(admin.TabularInline):
    model = ItemSolicitud
    extra = 0
    readonly_fields = ('precio_unitario_historico',)


class RecetaMedicaInline(admin.StackedInline):
    model = RecetaMedica
    extra = 0


# ============================================================================
# Admin: Solicitud
# ============================================================================
@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'tenant', 'estado', 'requiere_receta', 'total', 'creado_en')
    list_filter = ('estado', 'requiere_receta', 'tenant', 'creado_en')
    search_fields = ('user__username', 'tenant__nombre')
    inlines = [ItemSolicitudInline, RecetaMedicaInline]
    readonly_fields = ('creado_en',)


# ============================================================================
# Admin: RecetaMedica
# ============================================================================
@admin.register(RecetaMedica)
class RecetaMedicaAdmin(admin.ModelAdmin):
    list_display = ('pk', 'solicitud', 'usuario', 'folio_receta', 'medico_prescriptor', 'estado', 'revisado_por', 'fecha_revision')
    list_filter = ('estado', 'fecha_revision')
    search_fields = ('folio_receta', 'medico_prescriptor', 'rut_medico', 'usuario__username')

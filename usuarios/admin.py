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
from .models import Perfil


# ============================================================================
# Registro del modelo Perfil en el Admin
# ============================================================================
# @admin.register(Perfil): Decorador que registra el modelo Perfil con
# la clase PerfilAdmin como su configuración de admin personalizada.
# Es equivalente a: admin.site.register(Perfil, PerfilAdmin)
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    """
    Configuración del panel admin para el modelo Perfil.

    list_display: Columnas que se muestran en la lista de perfiles.
    list_filter: Filtros laterales disponibles para filtrar la lista.
    search_fields: Campos por los que se puede buscar en la barra de búsqueda.
    """
    # Columnas visibles en la tabla de listado del admin
    list_display = ('user', 'rol', 'nombre_institucion')

    # Filtro lateral por rol (dropdown con INSTITUCION/GESTOR)
    list_filter = ('rol',)

    # Barra de búsqueda: busca por username del usuario y nombre de institución
    # 'user__username' usa la notación de doble guion bajo de Django para
    # acceder a campos de modelos relacionados (JOIN implícito).
    search_fields = ('user__username', 'nombre_institucion')

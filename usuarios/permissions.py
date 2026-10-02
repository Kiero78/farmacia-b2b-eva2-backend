"""
============================================================================
PERMISSIONS.PY - Permisos RBAC (Role-Based Access Control) - App 'usuarios'
============================================================================
Este módulo implementa permisos personalizados basados en roles para el
sistema B2B de farmacia. Cada clase de permiso restringe el acceso a
los endpoints de la API según el rol del usuario autenticado.

¿Qué es RBAC (Role-Based Access Control)?
-------------------------------------------
RBAC es un modelo de control de acceso donde los permisos se asignan a
ROLES, no a usuarios individuales. Los usuarios se asignan a roles, y
heredan los permisos de ese rol. En nuestro sistema:

- Rol GESTOR: Puede gestionar catálogo (CRUD insumos/categorías),
  ver todas las solicitudes y cambiar su estado.
- Rol INSTITUCION: Puede ver catálogo, gestionar su carrito,
  crear solicitudes y ver solo sus propias solicitudes.

¿Cómo funcionan los permisos en DRF?
--------------------------------------
DRF evalúa los permisos en dos niveles:

1. PERMISOS DE VISTA (has_permission):
   Se evalúan ANTES de ejecutar la lógica de la vista.
   Determinan si el usuario puede ACCEDER al endpoint.
   Se evalúan para TODAS las peticiones (GET, POST, PUT, DELETE, etc.).
   Ejemplo: "¿Puede este usuario acceder a /api/insumos/?"

2. PERMISOS DE OBJETO (has_object_permission):
   Se evalúan DESPUÉS de obtener el objeto específico.
   Determinan si el usuario puede actuar sobre un OBJETO PARTICULAR.
   Solo se evalúan para vistas de detalle (retrieve, update, destroy).
   Ejemplo: "¿Puede este usuario modificar el Insumo #5?"

Flujo de evaluación:
   Request → has_permission() → [Si es True] → Vista obtiene objeto
   → has_object_permission() → [Si es True] → Ejecuta la acción

Si cualquier permiso retorna False, DRF responde con:
- 401 Unauthorized: Si el usuario no está autenticado.
- 403 Forbidden: Si el usuario está autenticado pero no tiene permiso.

Uso en las vistas:
-------------------
```python
class InsumoViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsGestorBodega]
```

Se pueden combinar múltiples permisos. DRF los evalúa con AND lógico:
todos deben retornar True para que el acceso sea permitido.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# permissions: Módulo de DRF que provee la clase base BasePermission.
# Todas las clases de permisos personalizados deben heredar de BasePermission
# y sobrescribir has_permission() y/o has_object_permission().
from rest_framework.permissions import BasePermission


# ============================================================================
# ============================================================================
# PERMISO: IsSuperAdmin
# ============================================================================
class IsSuperAdmin(BasePermission):
    """
    Permiso RBAC: Permite acceso a usuarios con rol 'SUPERADMIN' o superusuarios Django.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.es_superadmin
        )


# ============================================================================
# PERMISO: IsAdminPagina (Gestor del Tenant / Farmacéutico)
# ============================================================================
class IsAdminPagina(BasePermission):
    """
    Permiso RBAC: Permite acceso a administradores de página, gestores de bodega
    y superadministradores.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.es_admin_pagina
        )


# ============================================================================
# PERMISO: IsGestorBodega (Alias de compatibilidad con pauta EVA-2)
# ============================================================================
class IsGestorBodega(BasePermission):
    """
    Permiso RBAC: Permite acceso a gestores de bodega / administradores de página.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.es_admin_pagina
        )


# ============================================================================
# PERMISO: IsInstitucionMedica / IsUsuario
# ============================================================================
class IsInstitucionMedica(BasePermission):
    """
    Permiso RBAC: Permite acceso a usuarios clientes, instituciones o pacientes.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.es_usuario
        )


class IsUsuario(IsInstitucionMedica):
    """Alias semántico para usuarios finales/clientes del sistema."""
    pass

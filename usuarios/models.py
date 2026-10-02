"""
============================================================================
MODELS.PY - App 'usuarios'
============================================================================
Este módulo define el modelo Perfil que extiende al modelo User nativo de
Django mediante una relación OneToOneField.

Arquitectura de extensión del User:
------------------------------------
Django provee un modelo User con campos básicos (username, email, password,
first_name, last_name, is_active, is_staff, etc.). En lugar de reemplazarlo
con un modelo personalizado (AbstractUser / AbstractBaseUser), extendemos
su funcionalidad mediante un modelo Perfil vinculado con OneToOneField.

Ventajas de este enfoque:
- No altera las tablas de autenticación de Django.
- Compatible con el admin, permisos y sistema de autenticación sin cambios.
- Permite agregar campos específicos del dominio (rol, nombre_institucion).
- Un User siempre tiene exactamente UN Perfil (integridad 1:1 garantizada).

Señal post_save:
-----------------
Se utiliza una señal post_save de Django para crear automáticamente un Perfil
cada vez que se crea un nuevo User. Esto garantiza la integridad referencial:
nunca existirá un User sin su Perfil correspondiente.

Autor: Equipo EVA-2
Fecha: Septiembre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# models: Módulo de Django que provee las clases base para definir modelos ORM.
# Cada clase que hereda de models.Model se mapea a una tabla en la base de datos.
from django.db import models

# User: Modelo de usuario nativo de Django ubicado en django.contrib.auth.
# Contiene campos: id, username, password (hash), email, first_name, last_name,
# is_active, is_staff, is_superuser, date_joined, last_login.
# Lo importamos para crear la relación OneToOne con Perfil.
from django.contrib.auth.models import User

# post_save: Señal de Django que se emite DESPUÉS de que un modelo ejecuta
# su método save() (tanto para creación como actualización).
# receiver: Decorador que conecta una función a una señal específica.
from django.db.models.signals import post_save
from django.dispatch import receiver


# ============================================================================
# MODELO: Tenant
# ============================================================================
# Representa un Tenant (Organización, Farmacia, Clínica o Red Hospitalaria)
# que opera dentro del ecosistema B2B / Retail Farmacéutico.
# ============================================================================
class Tenant(models.Model):
    """
    Modelo Tenant: Entidad que aísla los recursos (catálogo, stock y solicitudes)
    de cada sucursal, clínica o cadena farmacéutica.
    """
    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Nombre del Tenant / Farmacia'
    )
    codigo = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='Código identificador único (Slug)'
    )
    rut = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='RUT Institucional'
    )
    direccion = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Dirección física'
    )
    telefono = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Teléfono de contacto'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Tenant Activo'
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )

    class Meta:
        verbose_name = 'Tenant / Farmacia'
        verbose_name_plural = 'Tenants / Farmacias'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


# ============================================================================
# MODELO: Perfil
# ============================================================================
# Extiende el modelo User de Django con información específica del dominio:
# rol del usuario (SUPERADMIN, ADMIN_PAGINA, USUARIO), pertenencia al Tenant
# e institución médica asociada.
# ============================================================================
class Perfil(models.Model):
    """
    Modelo Perfil: Extensión del modelo User de Django con soporte Multi-Tenant
    y Roles jerárquicos RBAC.
    """

    # -----------------------------------------------------------------------
    # CHOICES para el campo 'rol'
    # -----------------------------------------------------------------------
    # Roles del sistema:
    # - SUPERADMIN: Administrador global de toda la plataforma / plataforma SaaS.
    # - ADMIN_PAGINA: Administrador / Gestor de Bodega de un Tenant específico
    #   (controla stock, valida recetas médicas para aprobar o denegar ventas).
    # - USUARIO: Cliente / Paciente / Institución Compradora (compra, sube recetas).
    # - GESTOR / INSTITUCION: Alias de compatibilidad con la pauta base EVA-2.
    ROL_CHOICES = [
        ('SUPERADMIN', 'Superadministrador Global'),
        ('ADMIN_PAGINA', 'Administrador de Página / Farmacéutico'),
        ('USUARIO', 'Usuario / Paciente / Institución Médica'),
        ('GESTOR', 'Gestor de Bodega (Alias de Admin de Página)'),
        ('INSTITUCION', 'Institución Médica (Alias de Usuario)'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name='Usuario'
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='perfiles',
        verbose_name='Tenant / Farmacia Asociada'
    )

    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='USUARIO',
        verbose_name='Rol del usuario'
    )

    nombre_institucion = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Nombre de institución / Razón Social'
    )

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        tenant_str = f" [{self.tenant.codigo}]" if self.tenant else " [Global]"
        return f"{self.user.username} - {self.get_rol_display()}{tenant_str}"

    @property
    def es_superadmin(self):
        """Indica si el usuario tiene privilegios globales de superadmin."""
        return self.rol == 'SUPERADMIN' or self.user.is_superuser

    @property
    def es_admin_pagina(self):
        """Indica si es administrador de página / gestor del tenant."""
        return self.rol in ('ADMIN_PAGINA', 'GESTOR') or self.es_superadmin

    @property
    def es_usuario(self):
        """Indica si es usuario / cliente / comprador."""
        return self.rol in ('USUARIO', 'INSTITUCION')


# ============================================================================
# SEÑAL POST_SAVE: Crear Perfil automáticamente al crear un User
# ============================================================================
# Las señales (signals) de Django implementan el patrón Observer/Pub-Sub:
# cuando ocurre un evento (save, delete, etc.), Django notifica a todas
# las funciones "suscritas" a esa señal.
#
# Aquí usamos post_save del modelo User para GARANTIZAR que todo User
# recién creado tenga un Perfil asociado automáticamente.
#
# ¿Por qué es necesario?
# -----------------------
# Sin esta señal, un User podría existir sin Perfil, lo que causaría:
# 1. Errores al acceder a user.perfil (RelatedObjectDoesNotExist).
# 2. Violación de la regla de negocio: todo usuario DEBE tener un rol.
# 3. Necesidad de crear el Perfil manualmente en cada vista de registro.
#
# Con la señal, la creación es AUTOMÁTICA e INFALIBLE: funciona desde
# el admin, la shell, los serializers, los tests y cualquier otro código
# que cree un User.
#
# Decorador @receiver:
# - post_save: Señal a escuchar (se emite DESPUÉS del save).
# - sender=User: Solo escuchar saves del modelo User (no de otros modelos).
# ============================================================================
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Función receptora de la señal post_save del modelo User.

    Parámetros recibidos automáticamente por Django:
    - sender: La clase del modelo que envió la señal (User).
    - instance: La instancia específica del User que fue guardada.
    - created: Booleano. True si el User fue CREADO (INSERT).
                          False si fue ACTUALIZADO (UPDATE).
    - **kwargs: Argumentos adicionales de la señal (signal, using, etc.).

    Lógica:
    - Si created es True (nuevo User), crea un Perfil asociado.
    - Si created es False (User actualizado), guarda el Perfil existente
      para sincronizar cualquier cambio (ej: si el Perfil tiene campos
      que dependen del User).

    Perfil.objects.create(user=instance):
    - Crea una nueva fila en la tabla usuarios_perfil.
    - user=instance establece la FK al User recién creado.
    - Los demás campos toman sus valores por defecto:
      - rol = 'INSTITUCION' (default definido en el campo).
      - nombre_institucion = '' (string vacío por defecto).
    """
    if created:
        # User recién creado → asegurar su Perfil con valores por defecto
        Perfil.objects.get_or_create(user=instance)
    else:
        # User actualizado → guardar su Perfil existente para sincronizar
        try:
            instance.perfil.save()
        except Perfil.DoesNotExist:
            Perfil.objects.get_or_create(user=instance)

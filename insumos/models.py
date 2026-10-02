"""
============================================================================
MODELS.PY - App 'insumos'
============================================================================
Este módulo define los modelos del núcleo de negocio del sistema B2B de
farmacia. Implementa el flujo completo de un pedido de insumos médicos:

    Catálogo (CategoriaInsumo, Insumo)
        → Carrito de Compras (Carro, ItemCarro)
            → Solicitud de Pedido (Solicitud, ItemSolicitud)

Diagrama de relaciones (ER simplificado):
------------------------------------------
    CategoriaInsumo ──1:N──► Insumo
                                │
    User ──1:1──► Carro ──1:N──► ItemCarro ──N:1──┘
      │                                           │
      └──1:N──► Solicitud ──1:N──► ItemSolicitud ──N:1──► Insumo

Integridad referencial:
-----------------------
Todas las relaciones ForeignKey y OneToOneField utilizan on_delete=models.CASCADE,
lo que significa que al eliminar un registro padre, todos los registros hijos
se eliminan automáticamente. Esto previene registros huérfanos y mantiene
la consistencia de los datos.

Excepciones:
- Insumo usa on_delete=models.PROTECT en su FK a CategoriaInsumo para
  impedir la eliminación accidental de categorías que tienen insumos asociados.

Autor: Equipo EVA-2
Fecha: Septiembre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# models: Módulo ORM de Django para definir modelos que se mapean a tablas SQL.
from django.db import models

# User: Modelo de usuario nativo de Django (auth_user).
# Se importa para crear relaciones FK y OneToOne con los modelos del carrito
# y las solicitudes. Esto vincula cada carro/solicitud a un usuario específico.
from django.contrib.auth.models import User


# ============================================================================
# MODELO: CategoriaInsumo
# ============================================================================
# Representa una categoría de clasificación para los insumos médicos.
# Ejemplos: "Antibióticos", "Analgésicos", "Material Quirúrgico",
#           "Vacunas", "Equipos de Diagnóstico".
#
# Tabla generada en PostgreSQL: insumos_categoriainsumo
# Campos en la tabla:
#   - id (BigAutoField, PK) → Clave primaria autoincremental de 64 bits
#   - nombre (VARCHAR(100), UNIQUE) → Nombre único de la categoría
#   - descripcion (TEXT) → Descripción detallada de la categoría
#
# Propósito en el dominio:
# Las categorías permiten organizar el catálogo de insumos para facilitar
# la búsqueda y el filtrado por parte de las instituciones médicas.
# ============================================================================
class CategoriaInsumo(models.Model):
    """
    Modelo CategoriaInsumo: Clasificación jerárquica de insumos médicos.

    Cada insumo pertenece a exactamente una categoría (relación N:1).
    Las categorías son creadas y gestionadas por los gestores de bodega.
    """

    # -----------------------------------------------------------------------
    # Campo: nombre (CharField con unique=True)
    # -----------------------------------------------------------------------
    # Almacena el nombre de la categoría de insumo.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna 'nombre' de tipo VARCHAR(100).
    #   - Agrega un constraint UNIQUE, impidiendo categorías duplicadas.
    #     PostgreSQL crea un índice B-tree automáticamente para el UNIQUE.
    #
    # Parámetro unique=True:
    #   Garantiza que no existan dos categorías con el mismo nombre.
    #   Si se intenta insertar un duplicado, PostgreSQL lanza un error
    #   IntegrityError que Django convierte en una excepción Python.
    #   Esto es una restricción a nivel de BASE DE DATOS (no solo de app).
    nombre = models.CharField(
        max_length=100,                     # VARCHAR(100) en PostgreSQL
        unique=True,                        # Constraint UNIQUE en la BD
        verbose_name='Nombre de categoría'  # Etiqueta legible en el admin
    )

    # -----------------------------------------------------------------------
    # Campo: descripcion (TextField)
    # -----------------------------------------------------------------------
    # Almacena una descripción detallada de la categoría.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna 'descripcion' de tipo TEXT (sin límite de longitud).
    #   - TEXT en PostgreSQL almacena strings de hasta 1 GB.
    #
    # Parámetro blank=True:
    #   Permite enviar el campo vacío en formularios y serializers.
    #   blank es validación de FORMULARIO, no de base de datos.
    #
    # Parámetro default='':
    #   Valor por defecto: string vacío. Evita usar null=True para campos
    #   de texto (buena práctica Django: un solo valor para "sin dato").
    descripcion = models.TextField(
        blank=True,                     # Permitir vacío en validación
        default='',                     # Valor por defecto: string vacío
        verbose_name='Descripción'      # Etiqueta legible
    )

    # -----------------------------------------------------------------------
    # Meta: Configuración de metadatos del modelo
    # -----------------------------------------------------------------------
    class Meta:
        verbose_name = 'Categoría de Insumo'
        verbose_name_plural = 'Categorías de Insumos'
        # ordering: Define el orden por defecto de los querysets.
        # ['nombre'] ordena alfabéticamente por nombre (ASC).
        # Esto afecta a CategoriaInsumo.objects.all() y a relaciones FK.
        ordering = ['nombre']

    def __str__(self):
        """Representación string: muestra el nombre de la categoría."""
        return self.nombre


# ============================================================================
# MODELO: Insumo
# ============================================================================
# Representa un producto/insumo médico individual en el catálogo.
# Cada insumo pertenece a una categoría y tiene información de lote,
# vencimiento, precio y stock disponible.
#
# Tabla generada en PostgreSQL: insumos_insumo
# Campos en la tabla:
#   - id (BigAutoField, PK)
#   - categoria_id (BigInt, FK) → Referencia a insumos_categoriainsumo(id)
#   - nombre_comercial (VARCHAR(200))
#   - principio_activo (VARCHAR(200))
#   - lote (VARCHAR(50))
#   - fecha_vencimiento (DATE)
#   - precio_unitario (NUMERIC(10,2))
#   - stock_cajas (INTEGER, CHECK >= 0)
#
# Contexto farmacéutico:
# - nombre_comercial: Nombre de marca (ej: "Amoxil").
# - principio_activo: Compuesto químico activo (ej: "Amoxicilina").
# - lote: Identificador del lote de fabricación para trazabilidad.
# - fecha_vencimiento: Fecha hasta la cual el insumo es seguro para uso.
# ============================================================================
class Insumo(models.Model):
    """
    Modelo Insumo: Producto médico/farmacéutico en el catálogo B2B.

    Cada insumo tiene un nombre comercial, principio activo, información
    de lote y vencimiento, precio unitario por caja y stock disponible.
    Pertenece a exactamente una CategoriaInsumo (relación N:1).
    """

    # -----------------------------------------------------------------------
    # Campo: categoria (ForeignKey a CategoriaInsumo)
    # -----------------------------------------------------------------------
    # ForeignKey: Crea una relación muchos-a-uno (N:1) con CategoriaInsumo.
    # Muchos insumos pueden pertenecer a una misma categoría.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna 'categoria_id' de tipo BIGINT.
    #   - Agrega un constraint FOREIGN KEY que referencia
    #     insumos_categoriainsumo(id).
    #   - PostgreSQL crea un índice automático para optimizar JOINs.
    #
    # Parámetro on_delete=models.PROTECT:
    #   PROTECT impide la eliminación de una CategoriaInsumo si tiene
    #   insumos asociados. Al intentar eliminar una categoría con insumos,
    #   Django lanza una excepción ProtectedError.
    #
    #   ¿Por qué PROTECT y no CASCADE?
    #   - CASCADE eliminaría todos los insumos de la categoría, lo cual
    #     sería destructivo y podría afectar solicitudes existentes.
    #   - PROTECT obliga al gestor a reasignar los insumos a otra categoría
    #     antes de eliminar la categoría vacía. Esto es más seguro para
    #     un sistema de inventario médico donde la pérdida de datos es crítica.
    #
    # -----------------------------------------------------------------------
    # CHOICES para el régimen de venta / prescripción
    # -----------------------------------------------------------------------
    TIPO_VENTA_CHOICES = [
        ('LIBRE', 'Venta Directa / Sin Receta'),
        ('RECETA_SIMPLE', 'Receta Médica Simple'),
        ('RECETA_RETENIDA', 'Receta Retenida / Controlada'),
    ]

    # -----------------------------------------------------------------------
    # Campo: tenant (Multi-Tenancy)
    # -----------------------------------------------------------------------
    tenant = models.ForeignKey(
        'usuarios.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='insumos',
        verbose_name='Tenant / Farmacia'
    )

    categoria = models.ForeignKey(
        CategoriaInsumo,                    # Modelo referenciado
        on_delete=models.PROTECT,           # Impedir eliminación si hay insumos
        related_name='insumos',             # Acceso inverso: categoria.insumos
        verbose_name='Categoría'            # Etiqueta legible
    )

    # -----------------------------------------------------------------------
    # Campo: nombre_comercial (CharField)
    # -----------------------------------------------------------------------
    nombre_comercial = models.CharField(
        max_length=200,
        verbose_name='Nombre comercial'
    )

    # -----------------------------------------------------------------------
    # Campo: principio_activo (CharField)
    # -----------------------------------------------------------------------
    # Compuesto químico activo del medicamento según la DCI
    # (Denominación Común Internacional).
    # Ejemplos: "Amoxicilina", "Paracetamol", "Ibuprofeno".
    #
    # Para insumos no farmacéuticos (material quirúrgico, equipos),
    # este campo puede contener la descripción técnica.
    #
    # Parámetro blank=True:
    #   Permite vacío porque no todos los insumos médicos son medicamentos
    #   con principio activo (ej: gasas, guantes, equipos de diagnóstico).
    principio_activo = models.CharField(
        max_length=200,
        blank=True,                         # Opcional para insumos no farmacéuticos
        default='',                         # String vacío por defecto
        verbose_name='Principio activo'
    )

    # -----------------------------------------------------------------------
    # Campo: lote (CharField)
    # -----------------------------------------------------------------------
    # Número de lote de fabricación. Identificador único asignado por el
    # fabricante a un grupo de unidades producidas en las mismas condiciones.
    #
    # Importancia en el contexto farmacéutico:
    # - Trazabilidad: Permite rastrear el origen de cada unidad.
    # - Recall: Si un lote tiene problemas de calidad, se puede retirar
    #   del mercado identificando todas las unidades del lote.
    # - Regulación: Las autoridades sanitarias (ISP en Chile) exigen
    #   registro de lotes para medicamentos.
    lote = models.CharField(
        max_length=50,
        verbose_name='Número de lote'
    )

    # -----------------------------------------------------------------------
    # Campo: fecha_vencimiento (DateField)
    # -----------------------------------------------------------------------
    # Fecha de expiración del insumo. Después de esta fecha, el producto
    # no debe ser utilizado por seguridad del paciente.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna de tipo DATE (sin componente de hora).
    #   - Formato almacenado: YYYY-MM-DD (ISO 8601).
    #
    # En un sistema real, se implementarían alertas automáticas para
    # insumos próximos a vencer (ej: 90 días antes del vencimiento).
    fecha_vencimiento = models.DateField(
        verbose_name='Fecha de vencimiento'
    )

    # -----------------------------------------------------------------------
    # Campo: precio_unitario (DecimalField)
    # -----------------------------------------------------------------------
    # Precio por caja del insumo en la moneda local.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna de tipo NUMERIC(10,2).
    #   - NUMERIC es un tipo de precisión exacta (a diferencia de FLOAT
    #     que tiene errores de punto flotante).
    #
    # Parámetro max_digits=10:
    #   Número total de dígitos (incluyendo decimales).
    #   Permite valores hasta 99,999,999.99 (suficiente para precios).
    #
    # Parámetro decimal_places=2:
    #   Número de dígitos después del punto decimal.
    #   2 decimales es estándar para valores monetarios.
    #
    # ¿Por qué DecimalField y no FloatField?
    # - DecimalField usa el tipo Python Decimal (precisión arbitraria).
    # - FloatField usa float de IEEE 754 (puede tener errores como
    #   0.1 + 0.2 = 0.30000000000000004).
    # - Para valores monetarios, la precisión exacta es CRÍTICA.
    #   Un error de centavos multiplicado por miles de unidades puede
    #   resultar en diferencias significativas.
    precio_unitario = models.DecimalField(
        max_digits=10,                      # Hasta 10 dígitos totales
        decimal_places=2,                   # 2 decimales (centavos)
        verbose_name='Precio unitario'
    )

    # -----------------------------------------------------------------------
    # Campo: stock_cajas (PositiveIntegerField)
    # -----------------------------------------------------------------------
    # Cantidad de cajas disponibles en bodega.
    #
    # Implementación en PostgreSQL:
    #   - Crea una columna de tipo INTEGER.
    #   - Django agrega un constraint CHECK (stock_cajas >= 0) para
    #     garantizar que el stock nunca sea negativo.
    #
    # ¿Por qué PositiveIntegerField y no IntegerField?
    # - PositiveIntegerField agrega validación tanto en Django (formularios,
    #   serializers) como en PostgreSQL (CHECK constraint) para asegurar
    #   que el valor sea >= 0.
    # - Un stock negativo no tiene sentido en el mundo real y podría
    #   indicar un error de lógica en el sistema.
    #
    # Parámetro default=0:
    #   Los insumos nuevos comienzan con stock 0 hasta que el gestor
    #   de bodega registre las unidades recibidas.
    stock_cajas = models.PositiveIntegerField(
        default=0,
        verbose_name='Stock en cajas'
    )

    # -----------------------------------------------------------------------
    # Campos para Receta Médica y Regulación Sanitaria
    # -----------------------------------------------------------------------
    tipo_venta = models.CharField(
        max_length=20,
        choices=TIPO_VENTA_CHOICES,
        default='LIBRE',
        verbose_name='Régimen de Venta'
    )

    requiere_receta = models.BooleanField(
        default=False,
        verbose_name='Requiere Receta Médica'
    )

    es_medicamento_controlado = models.BooleanField(
        default=False,
        verbose_name='Control de Psicotrópicos/Estupefacientes'
    )

    # -----------------------------------------------------------------------
    # Meta
    # -----------------------------------------------------------------------
    class Meta:
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'
        # Ordenar por nombre comercial alfabéticamente por defecto.
        ordering = ['nombre_comercial']

    def __str__(self):
        """
        Representación string: nombre comercial + lote.
        Incluir el lote permite distinguir entre el mismo producto
        de diferentes lotes en listas y dropdowns del admin.
        """
        return f"{self.nombre_comercial} (Lote: {self.lote})"


# ============================================================================
# MODELO: Carro (Carrito de Compras)
# ============================================================================
# Representa el carrito de compras de un usuario. Cada usuario tiene
# exactamente un carrito activo (relación 1:1 con User).
#
# Tabla generada en PostgreSQL: insumos_carro
# Campos en la tabla:
#   - id (BigAutoField, PK)
#   - user_id (BigInt, FK UNIQUE) → Referencia a auth_user(id)
#   - estado (VARCHAR(20)) → Estado del carrito
#
# Flujo del carrito:
# 1. ACTIVO: El usuario está agregando/modificando items en el carrito.
# 2. CONVERTIDO: El carrito fue transformado en una Solicitud de pedido.
#    Al convertirse, se crea una Solicitud con los items del carrito,
#    y el carrito queda marcado como CONVERTIDO (historial).
#    Se puede crear un nuevo carrito ACTIVO para el usuario.
# ============================================================================
class Carro(models.Model):
    """
    Modelo Carro: Carrito de compras temporal para agrupar insumos antes
    de generar una solicitud formal de pedido.

    Relación con User: OneToOne (1:1)
    - Un User tiene a lo sumo UN Carro activo.
    - Cuando el carrito se convierte en solicitud, pasa a estado CONVERTIDO.
    """

    # -----------------------------------------------------------------------
    # CHOICES para el campo 'estado'
    # -----------------------------------------------------------------------
    # Estados posibles del carrito:
    #
    # ACTIVO: Carrito en uso. El usuario puede agregar, modificar o eliminar
    #   items. Solo puede existir un carrito ACTIVO por usuario a la vez.
    #
    # CONVERTIDO: El carrito fue transformado en una Solicitud de pedido.
    #   Los items del carrito se copiaron a ItemSolicitud y el carrito
    #   queda como registro histórico. El usuario puede crear un nuevo
    #   carrito ACTIVO después de la conversión.
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('CONVERTIDO', 'Convertido'),
    ]

    # -----------------------------------------------------------------------
    # Campo: user (OneToOneField a User)
    # -----------------------------------------------------------------------
    # Relación 1:1 con User. Cada usuario tiene un único carrito.
    #
    # Implementación en PostgreSQL:
    #   - Columna 'user_id' BIGINT con FK a auth_user(id).
    #   - Constraint UNIQUE en user_id (garantiza relación 1:1).
    #
    # on_delete=models.CASCADE:
    #   Si se elimina el usuario, su carrito se elimina automáticamente.
    #   Esto tiene sentido porque un carrito sin usuario no tiene propósito.
    #
    # related_name='carro':
    #   Acceso inverso: user.carro → instancia del carrito del usuario.
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,           # Eliminar carro si se elimina User
        related_name='carro',               # Acceso inverso: user.carro
        verbose_name='Usuario'
    )

    # -----------------------------------------------------------------------
    # Campo: estado (CharField con choices)
    # -----------------------------------------------------------------------
    # Estado actual del carrito. Determina si el carrito está en uso o
    # ya fue convertido en una solicitud.
    #
    # PostgreSQL: VARCHAR(20).
    # default='ACTIVO': Un carrito nuevo siempre inicia como activo.
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='ACTIVO',
        verbose_name='Estado del carro'
    )

    class Meta:
        verbose_name = 'Carro de Compras'
        verbose_name_plural = 'Carros de Compras'

    def __str__(self):
        """
        Muestra el username del dueño y el estado actual del carrito.
        get_estado_display() retorna la etiqueta legible del choice.
        """
        return f"Carro de {self.user.username} - {self.get_estado_display()}"


# ============================================================================
# MODELO: ItemCarro
# ============================================================================
# Representa un item (línea) dentro del carrito de compras.
# Vincula un Carro con un Insumo y especifica la cantidad deseada.
#
# Tabla generada en PostgreSQL: insumos_itemcarro
# Campos en la tabla:
#   - id (BigAutoField, PK)
#   - carro_id (BigInt, FK) → Referencia a insumos_carro(id)
#   - insumo_id (BigInt, FK) → Referencia a insumos_insumo(id)
#   - cantidad_cajas (INTEGER, CHECK >= 1)
#
# Constraint especial:
#   - UNIQUE(carro_id, insumo_id): Un insumo solo puede aparecer UNA VEZ
#     en un carrito. Si el usuario quiere más cantidad del mismo insumo,
#     debe actualizar la cantidad, no agregar otro item duplicado.
# ============================================================================
class ItemCarro(models.Model):
    """
    Modelo ItemCarro: Línea individual dentro de un carrito de compras.

    Relaciones:
    - FK a Carro (N:1): Muchos items pueden pertenecer a un carrito.
    - FK a Insumo (N:1): Muchos items de diferentes carros pueden
      referenciar al mismo insumo.

    Restricción unique_together:
    - La combinación (carro, insumo) es ÚNICA. Esto impide duplicados:
      un mismo insumo no puede aparecer dos veces en el mismo carrito.
    """

    # -----------------------------------------------------------------------
    # Campo: carro (ForeignKey a Carro)
    # -----------------------------------------------------------------------
    # Relación N:1 con Carro. Un carrito puede tener múltiples items.
    #
    # on_delete=models.CASCADE:
    #   Si se elimina el carrito, todos sus items se eliminan.
    #   Esto es lógico: los items no tienen sentido sin su carrito.
    #
    # related_name='items':
    #   Acceso inverso: carro.items.all() → todos los items del carrito.
    carro = models.ForeignKey(
        Carro,
        on_delete=models.CASCADE,           # Eliminar items si se elimina el Carro
        related_name='items',               # Acceso inverso: carro.items
        verbose_name='Carro'
    )

    # -----------------------------------------------------------------------
    # Campo: insumo (ForeignKey a Insumo)
    # -----------------------------------------------------------------------
    # Relación N:1 con Insumo. El mismo insumo puede estar en múltiples
    # carritos de diferentes usuarios.
    #
    # on_delete=models.CASCADE:
    #   Si se elimina el insumo del catálogo, se eliminan los items de
    #   carrito que lo referenciaban. Esto es aceptable para carritos
    #   temporales (no afecta solicitudes históricas, que tienen ItemSolicitud
    #   con precio_unitario_historico independiente).
    #
    # related_name='items_carro':
    #   Acceso inverso: insumo.items_carro.all() → items de carrito con este insumo.
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.CASCADE,           # Eliminar item si se elimina el Insumo
        related_name='items_carro',         # Acceso inverso: insumo.items_carro
        verbose_name='Insumo'
    )

    # -----------------------------------------------------------------------
    # Campo: cantidad_cajas (PositiveIntegerField)
    # -----------------------------------------------------------------------
    # Cantidad de cajas que el usuario desea pedir de este insumo.
    #
    # PositiveIntegerField: Garantiza valores >= 0 tanto en Django como
    # en PostgreSQL (CHECK constraint). Se usa default=1 porque al agregar
    # un insumo al carrito, el mínimo lógico es 1 caja.
    #
    # Nota: La validación de que cantidad_cajas <= insumo.stock_cajas
    # se implementa en la capa de serializers/views, no en el modelo,
    # porque es una regla de NEGOCIO que puede cambiar dinámicamente
    # (el stock cambia con cada transacción).
    cantidad_cajas = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad de cajas'
    )

    # -----------------------------------------------------------------------
    # Meta: unique_together
    # -----------------------------------------------------------------------
    class Meta:
        verbose_name = 'Item del Carro'
        verbose_name_plural = 'Items del Carro'

        # unique_together: Crea un constraint UNIQUE compuesto en PostgreSQL
        # sobre las columnas (carro_id, insumo_id).
        #
        # Esto significa que la COMBINACIÓN de carro + insumo debe ser única.
        # Un insumo puede estar en DIFERENTES carritos, y un carrito puede
        # tener DIFERENTES insumos, pero un insumo específico solo puede
        # aparecer UNA VEZ dentro de un carrito específico.
        #
        # PostgreSQL crea un índice compuesto B-tree para este constraint,
        # lo que también optimiza las consultas que filtran por ambos campos.
        #
        # Si se intenta insertar un duplicado, PostgreSQL lanza IntegrityError
        # que Django propaga como excepción.
        unique_together = ['carro', 'insumo']

    def __str__(self):
        """Muestra el insumo y la cantidad en el carrito."""
        return f"{self.cantidad_cajas}x {self.insumo.nombre_comercial}"


# ============================================================================
# MODELO: Solicitud (Pedido formal)
# ============================================================================
# Representa una solicitud formal de pedido de insumos médicos.
# Se crea a partir de un carrito de compras cuando la institución
# médica confirma su pedido.
#
# Tabla generada en PostgreSQL: insumos_solicitud
# Campos en la tabla:
#   - id (BigAutoField, PK)
#   - user_id (BigInt, FK) → Referencia a auth_user(id)
#   - estado (VARCHAR(20)) → Estado de la solicitud
#   - total (NUMERIC(12,2)) → Monto total del pedido
#   - creado_en (TIMESTAMPTZ) → Fecha/hora de creación
#
# Ciclo de vida de una solicitud:
# ┌───────────┐     ┌──────────┐     ┌────────────┐
# │ PENDIENTE │────►│  PAGADO  │────►│ ENTREGADO  │
# └─────┬─────┘     └──────────┘     └────────────┘
#       │
#       ▼
# ┌────────────┐
# │ CANCELADO  │
# └────────────┘
#
# PENDIENTE → PAGADO: La institución confirma el pago.
# PAGADO → ENTREGADO: El gestor de bodega confirma la entrega.
# PENDIENTE → CANCELADO: La institución o el gestor cancela el pedido.
# ============================================================================
class Solicitud(models.Model):
    """
    Modelo Solicitud: Pedido formal de insumos médicos.

    Representa la transacción B2B entre una institución médica y el
    proveedor (bodega). Contiene el estado del pedido, el monto total
    y la fecha de creación.

    Relación con User: ForeignKey (N:1)
    - Un usuario puede tener MÚLTIPLES solicitudes (historial de pedidos).
    - Cada solicitud pertenece a exactamente UN usuario.
    """

    # -----------------------------------------------------------------------
    # CHOICES para el campo 'estado'
    # -----------------------------------------------------------------------
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Pago/Confirmación'),
        ('EN_REVISION', 'En Revisión de Receta Médica'),
        ('PAGADO', 'Pagado / Venta Autorizada'),
        ('ENTREGADO', 'Despachado / Entregado'),
        ('CANCELADO', 'Cancelado / Venta Denegada'),
    ]

    # -----------------------------------------------------------------------
    # Campo: tenant (Multi-Tenancy)
    # -----------------------------------------------------------------------
    tenant = models.ForeignKey(
        'usuarios.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='solicitudes',
        verbose_name='Tenant / Farmacia'
    )

    # -----------------------------------------------------------------------
    # Campo: user (ForeignKey a User)
    # -----------------------------------------------------------------------
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='solicitudes',
        verbose_name='Usuario solicitante'
    )

    # -----------------------------------------------------------------------
    # Campo: estado (CharField con choices)
    # -----------------------------------------------------------------------
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado de la solicitud'
    )

    requiere_receta = models.BooleanField(
        default=False,
        verbose_name='Requiere Validación de Receta'
    )

    motivo_cancelacion = models.TextField(
        blank=True,
        default='',
        verbose_name='Motivo de Cancelación / Rechazo'
    )

    # -----------------------------------------------------------------------
    # Campo: total (DecimalField)
    # -----------------------------------------------------------------------
    # Monto total del pedido en la moneda local.
    # Se calcula como la suma de (precio_unitario × cantidad_cajas) de
    # todos los ItemSolicitud asociados.
    #
    # Implementación en PostgreSQL: NUMERIC(12,2).
    # max_digits=12: Permite totales hasta 9,999,999,999.99
    #   (suficiente para pedidos institucionales de gran volumen).
    # decimal_places=2: Precisión a centavos.
    #
    # default=0: Inicialmente 0, se actualiza al crear los items.
    #
    # ¿Por qué almacenar el total y no calcularlo dinámicamente?
    # - Rendimiento: Evita recalcular el total en cada consulta.
    # - Inmutabilidad: El total refleja los precios al momento de la
    #   solicitud, no los precios actuales (que pueden cambiar).
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Total del pedido'
    )

    # -----------------------------------------------------------------------
    # Campo: creado_en (DateTimeField)
    # -----------------------------------------------------------------------
    # Fecha y hora de creación de la solicitud.
    #
    # Implementación en PostgreSQL: TIMESTAMPTZ (timestamp with time zone).
    # Almacena la fecha/hora en UTC. Django la convierte a la zona horaria
    # configurada (America/Santiago) al mostrarla.
    #
    # Parámetro auto_now_add=True:
    #   Django asigna automáticamente la fecha/hora actual al CREAR el registro.
    #   Este campo no se puede modificar después de la creación (es inmutable).
    #   El campo se excluye automáticamente de formularios y serializers.
    #
    #   Diferencia con auto_now=True:
    #   - auto_now_add: Solo al crear (INSERT). Fecha de creación.
    #   - auto_now: Al crear Y actualizar (INSERT + UPDATE). Fecha de modificación.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )

    class Meta:
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        # Ordenar por fecha de creación descendente: las más recientes primero.
        ordering = ['-creado_en']

    def __str__(self):
        """
        Muestra el ID de la solicitud, el usuario y el estado.
        self.pk = Primary Key (ID autoincremental).
        """
        return f"Solicitud #{self.pk} - {self.user.username} ({self.get_estado_display()})"


# ============================================================================
# MODELO: ItemSolicitud
# ============================================================================
# Representa un item (línea) dentro de una solicitud de pedido.
# Similar a ItemCarro, pero con una diferencia clave:
# almacena el precio_unitario_historico para preservar el precio
# al momento de la solicitud, independientemente de cambios futuros.
#
# Tabla generada en PostgreSQL: insumos_itemsolicitud
# Campos en la tabla:
#   - id (BigAutoField, PK)
#   - solicitud_id (BigInt, FK) → Referencia a insumos_solicitud(id)
#   - insumo_id (BigInt, FK) → Referencia a insumos_insumo(id)
#   - precio_unitario_historico (NUMERIC(10,2))
#   - cantidad_cajas (INTEGER, CHECK >= 1)
#
# ¿Por qué precio_unitario_historico?
# ------------------------------------
# El precio de un insumo puede cambiar con el tiempo. Si solo se guardara
# la FK al insumo, el total de una solicitud pasada cambiaría cada vez
# que se actualice el precio del insumo. Esto violaría la integridad
# del registro contable/financiero.
#
# Al almacenar precio_unitario_historico, se "congela" el precio al
# momento de la solicitud, creando un registro inmutable que sirve como:
# - Factura/comprobante de la transacción.
# - Auditoría de precios históricos.
# - Base para reportes financieros precisos.
# ============================================================================
class ItemSolicitud(models.Model):
    """
    Modelo ItemSolicitud: Línea individual dentro de una solicitud de pedido.

    A diferencia de ItemCarro, este modelo almacena el precio histórico
    del insumo al momento de crear la solicitud, preservando la integridad
    del registro financiero ante cambios futuros de precios.

    Relaciones:
    - FK a Solicitud (N:1): Muchos items pueden pertenecer a una solicitud.
    - FK a Insumo (N:1): Referencia al insumo (para consultar nombre, lote, etc.).
    """

    # -----------------------------------------------------------------------
    # Campo: solicitud (ForeignKey a Solicitud)
    # -----------------------------------------------------------------------
    # Relación N:1 con Solicitud. Una solicitud puede tener múltiples items,
    # representando los diferentes insumos pedidos.
    #
    # on_delete=models.CASCADE:
    #   Si se elimina la solicitud, todos sus items se eliminan.
    #   Los items no tienen sentido sin su solicitud padre.
    #
    # related_name='items':
    #   Acceso inverso: solicitud.items.all() → todos los items del pedido.
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Solicitud'
    )

    # -----------------------------------------------------------------------
    # Campo: insumo (ForeignKey a Insumo)
    # -----------------------------------------------------------------------
    # Referencia al insumo del catálogo. Se mantiene para poder consultar
    # los datos del insumo (nombre, principio activo, lote, etc.) desde
    # la solicitud.
    #
    # on_delete=models.PROTECT:
    #   PROTECT impide eliminar un insumo que está referenciado en solicitudes.
    #   Esto es CRÍTICO para la integridad del historial de pedidos:
    #   - Las solicitudes son documentos financieros/contables.
    #   - Eliminar un insumo referenciado corrompería el historial.
    #   - El gestor debe marcar el insumo como "descontinuado" en lugar
    #     de eliminarlo (se podría agregar un campo 'activo' al modelo Insumo).
    #
    # related_name='items_solicitud':
    #   Acceso inverso: insumo.items_solicitud.all() → items de solicitud
    #   que incluyen este insumo (historial de ventas del producto).
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,           # Impedir eliminación si hay solicitudes
        related_name='items_solicitud',
        verbose_name='Insumo'
    )

    # -----------------------------------------------------------------------
    # Campo: precio_unitario_historico (DecimalField)
    # -----------------------------------------------------------------------
    # Precio del insumo al momento de crear la solicitud ("snapshot" del precio).
    #
    # Este campo es FUNDAMENTAL para la integridad financiera:
    # - Se copia de insumo.precio_unitario al crear el ItemSolicitud.
    # - Una vez guardado, NO se modifica aunque cambie el precio del insumo.
    # - Permite calcular el total correcto de la solicitud en cualquier
    #   momento futuro: total = Σ(precio_unitario_historico × cantidad_cajas).
    #
    # PostgreSQL: NUMERIC(10,2) - misma precisión que precio_unitario del Insumo.
    precio_unitario_historico = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio unitario (histórico)'
    )

    # -----------------------------------------------------------------------
    # Campo: cantidad_cajas (PositiveIntegerField)
    # -----------------------------------------------------------------------
    # Cantidad de cajas solicitadas de este insumo.
    # Se copia de ItemCarro.cantidad_cajas al convertir el carrito.
    #
    # PositiveIntegerField con default=1: Mismo comportamiento que en ItemCarro.
    # La cantidad mínima lógica es 1 caja.
    cantidad_cajas = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad de cajas'
    )

    class Meta:
        verbose_name = 'Item de Solicitud'
        verbose_name_plural = 'Items de Solicitud'

    def __str__(self):
        """
        Muestra la cantidad y el insumo del item.
        Incluye el nombre comercial para identificación rápida.
        """
        return f"{self.cantidad_cajas}x {self.insumo.nombre_comercial} @ ${self.precio_unitario_historico}"


# ============================================================================
# MODELO: RecetaMedica
# ============================================================================
# Representa una prescripción médica asociada a la compra de fármacos o insumos
# que exigen receta médica.
# El Administrador de Página / Farmacéutico audita esta receta antes de
# autorizar la venta o denegarla.
# ============================================================================
class RecetaMedica(models.Model):
    """
    Modelo RecetaMedica: Prescripción médica auditada por el Administrador/Farmacéutico.
    """
    ESTADO_RECETA_CHOICES = [
        ('PENDIENTE', 'Pendiente de Revisión'),
        ('APROBADA', 'Receta Aprobada (Venta Autorizada)'),
        ('RECHAZADA', 'Receta Rechazada (Venta Denegada)'),
    ]

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='recetas',
        verbose_name='Solicitud Asociada'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recetas_subidas',
        verbose_name='Paciente / Solicitante'
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='recetas_emitidas',
        verbose_name='Fármaco Prescrito'
    )
    folio_receta = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Folio / Código de Receta'
    )
    medico_prescriptor = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name='Médico Prescriptor'
    )
    rut_medico = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='RUT del Médico'
    )
    institucion_salud = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name='Centro de Salud Emisor'
    )
    archivo_receta = models.FileField(
        upload_to='recetas/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Documento / Foto de la Receta'
    )
    diagnostico = models.TextField(
        blank=True,
        default='',
        verbose_name='Diagnóstico / Indicaciones'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_RECETA_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado de la Receta'
    )
    observaciones_farmaceutico = models.TextField(
        blank=True,
        default='',
        verbose_name='Observaciones del Farmacéutico / Admin'
    )
    revisado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recetas_auditadas',
        verbose_name='Farmacéutico Revisor'
    )
    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Revisión'
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )

    class Meta:
        verbose_name = 'Receta Médica'
        verbose_name_plural = 'Recetas Médicas'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Receta #{self.pk} - {self.get_estado_display()} (Solicitud #{self.solicitud_id})"

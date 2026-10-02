"""
============================================================================
SERIALIZERS.PY - App 'insumos'
============================================================================
Este módulo define los serializadores para todos los modelos de la app
'insumos': catálogo de productos, carrito de compras y solicitudes de pedido.

Serializadores definidos:
--------------------------
- CategoriaInsumoSerializer: Serializa categorías de insumos médicos.
- InsumoSerializer: Serializa insumos con el nombre de la categoría.
- ItemCarroSerializer: Serializa items del carrito con subtotal calculado.
- CarroSerializer: Serializa el carrito completo con total estimado.
- ItemSolicitudSerializer: Serializa items de una solicitud con subtotal.
- SolicitudSerializer: Serializa solicitudes completas con sus items.

Campos calculados (SerializerMethodField):
-------------------------------------------
Algunos serializadores incluyen campos calculados que NO existen en el
modelo pero se calculan al momento de la serialización:
- subtotal: precio_unitario × cantidad_cajas (por cada item).
- total_estimado: Suma de subtotales de todos los items del carrito.
- nombre_categoria: Nombre legible de la categoría (en vez del ID).

Estos campos son de SOLO LECTURA y no se almacenan en la base de datos.
Se calculan en tiempo real para cada respuesta de la API.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# serializers: Módulo de DRF para definir serializadores.
from rest_framework import serializers

# Importamos todos los modelos de la app 'insumos' que serán serializados.
from insumos.models import (
    CategoriaInsumo,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
    RecetaMedica,
)


# ============================================================================
# SERIALIZADOR: CategoriaInsumoSerializer
# ============================================================================
# Serializa el modelo CategoriaInsumo para operaciones CRUD en la API.
# Es un serializador simple que expone todos los campos del modelo.
#
# Uso en la API:
# - GET /api/categorias/ → Lista todas las categorías.
# - POST /api/categorias/ → Crea una nueva categoría (solo GESTOR).
# - GET /api/categorias/1/ → Detalle de la categoría con ID 1.
# - PUT /api/categorias/1/ → Actualiza la categoría (solo GESTOR).
# - DELETE /api/categorias/1/ → Elimina la categoría (solo GESTOR, si no tiene insumos).
# ============================================================================
class CategoriaInsumoSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo CategoriaInsumo.

    Expone: id, nombre, descripcion.
    El constraint UNIQUE del campo 'nombre' se valida automáticamente
    por ModelSerializer, levantando ValidationError si se intenta crear
    una categoría con nombre duplicado.
    """

    class Meta:
        model = CategoriaInsumo
        # fields = '__all__': Incluye TODOS los campos del modelo.
        # Para CategoriaInsumo, esto equivale a: ['id', 'nombre', 'descripcion'].
        # '__all__' es conveniente para modelos simples donde queremos exponer
        # todos los campos sin excepción.
        fields = '__all__'


# ============================================================================
# SERIALIZADOR: InsumoSerializer
# ============================================================================
# Serializa el modelo Insumo para el catálogo de productos médicos.
# Incluye un campo calculado 'nombre_categoria' que muestra el nombre
# legible de la categoría en lugar de solo el ID numérico.
#
# Ejemplo de respuesta JSON:
# {
#     "id": 1,
#     "categoria": 3,
#     "nombre_categoria": "Antibióticos",
#     "nombre_comercial": "Amoxil 500mg",
#     "principio_activo": "Amoxicilina",
#     "lote": "LOT-2024-001",
#     "fecha_vencimiento": "2025-12-31",
#     "precio_unitario": "15000.00",
#     "stock_cajas": 50
# }
# ============================================================================
class InsumoSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Insumo.

    Expone todos los campos del modelo más un campo calculado
    'nombre_categoria' para facilitar la lectura en el frontend.
    """

    # -----------------------------------------------------------------------
    # Campo calculado: nombre_categoria (SerializerMethodField)
    # -----------------------------------------------------------------------
    # SerializerMethodField: Campo de SOLO LECTURA cuyo valor se calcula
    # mediante un método del serializador (get_<nombre_campo>).
    #
    # NO se almacena en la base de datos. Se calcula en tiempo real
    # durante la serialización (Model → JSON).
    #
    # ¿Por qué no usar StringRelatedField o SlugRelatedField?
    # - StringRelatedField: Solo lectura, usa __str__() del modelo relacionado.
    #   Podría funcionar, pero no permite control fino del formato.
    # - SlugRelatedField: Permite leer/escribir por un campo específico,
    #   pero reemplazaría el campo 'categoria' (que queremos mantener como ID).
    # - SerializerMethodField: Permite agregar un campo ADICIONAL sin
    #   modificar el campo FK original. Así tenemos tanto el ID (categoria)
    #   como el nombre legible (nombre_categoria).
    nombre_categoria = serializers.SerializerMethodField()

    class Meta:
        model = Insumo
        # Incluimos todos los campos del modelo + nombre_categoria calculado.
        # fields = '__all__' NO incluiría nombre_categoria porque no es un
        # campo del modelo, por eso listamos los campos explícitamente.
        fields = [
            'id',
            'tenant',
            'categoria',
            'nombre_categoria',
            'nombre_comercial',
            'principio_activo',
            'lote',
            'fecha_vencimiento',
            'precio_unitario',
            'stock_cajas',
            'tipo_venta',
            'requiere_receta',
            'es_medicamento_controlado',
        ]

    def get_nombre_categoria(self, obj):
        """
        Método que calcula el valor del campo 'nombre_categoria'.

        DRF invoca automáticamente get_<nombre_campo>(self, obj) para
        cada SerializerMethodField. La convención de nombre es estricta:
        el método DEBE llamarse get_ + nombre del campo.

        Args:
            obj: Instancia del modelo Insumo que se está serializando.
                 Es la fila actual de la tabla insumos_insumo.

        Returns:
            str: Nombre de la categoría del insumo.
                 Ej: "Antibióticos", "Analgésicos", etc.

        Implementación:
            obj.categoria → Accede a la instancia de CategoriaInsumo
                            relacionada (Django hace un JOIN automático).
            .nombre → Accede al campo 'nombre' de esa categoría.
        """
        return obj.categoria.nombre


# ============================================================================
# SERIALIZADOR: ItemCarroSerializer
# ============================================================================
# Serializa cada línea/item dentro del carrito de compras.
# Incluye campos calculados para mostrar información del insumo y el
# subtotal (precio × cantidad) sin necesidad de consultas adicionales.
#
# Ejemplo de respuesta JSON:
# {
#     "id": 1,
#     "insumo": 5,
#     "nombre_insumo": "Amoxil 500mg",
#     "precio_unitario_insumo": "15000.00",
#     "cantidad_cajas": 3,
#     "subtotal": "45000.00"
# }
# ============================================================================
class ItemCarroSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo ItemCarro (item del carrito).

    Incluye campos calculados de solo lectura:
    - nombre_insumo: Nombre comercial del insumo referenciado.
    - precio_unitario_insumo: Precio actual del insumo (puede cambiar).
    - subtotal: precio_unitario × cantidad_cajas.
    """

    # -----------------------------------------------------------------------
    # Campo calculado: nombre_insumo
    # -----------------------------------------------------------------------
    # Muestra el nombre comercial del insumo para que el frontend no
    # necesite hacer una segunda petición a /api/insumos/{id}/ para
    # obtener el nombre del producto en el carrito.
    nombre_insumo = serializers.SerializerMethodField()

    # -----------------------------------------------------------------------
    # Campo calculado: precio_unitario_insumo
    # -----------------------------------------------------------------------
    # Muestra el precio ACTUAL del insumo (no el histórico).
    # Este es el precio "en vivo" que puede cambiar si el gestor
    # actualiza los precios. El precio se "congela" solo cuando
    # el carrito se convierte en solicitud (precio_unitario_historico).
    precio_unitario_insumo = serializers.SerializerMethodField()

    # -----------------------------------------------------------------------
    # Campo calculado: subtotal
    # -----------------------------------------------------------------------
    # Calcula precio_unitario × cantidad_cajas para este item.
    # Es un cálculo en tiempo real que refleja el precio actual del insumo.
    # Cuando el carrito se convierta en solicitud, el subtotal se calculará
    # con el precio_unitario_historico (congelado) en ItemSolicitud.
    subtotal = serializers.SerializerMethodField()
    requiere_receta = serializers.BooleanField(source='insumo.requiere_receta', read_only=True)
    tipo_venta = serializers.CharField(source='insumo.tipo_venta', read_only=True)

    class Meta:
        model = ItemCarro
        fields = [
            'id',
            'insumo',
            'nombre_insumo',
            'precio_unitario_insumo',
            'cantidad_cajas',
            'subtotal',
            'requiere_receta',
            'tipo_venta',
        ]

    def get_nombre_insumo(self, obj):
        """
        Retorna el nombre comercial del insumo asociado a este item.

        Args:
            obj: Instancia de ItemCarro.

        Returns:
            str: Nombre comercial del insumo.
                 Ej: "Amoxil 500mg", "Paracetamol MK".
        """
        return obj.insumo.nombre_comercial

    def get_precio_unitario_insumo(self, obj):
        """
        Retorna el precio unitario ACTUAL del insumo.

        Args:
            obj: Instancia de ItemCarro.

        Returns:
            str: Precio unitario como string decimal.
                 Se retorna como string para preservar los 2 decimales.
                 Ej: "15000.00" (no 15000.0 ni 15000).
                 DRF serializa Decimal a string por defecto para
                 evitar problemas de precisión con JSON (que usa float).
        """
        return str(obj.insumo.precio_unitario)

    def get_subtotal(self, obj):
        """
        Calcula y retorna el subtotal para este item del carrito.

        Fórmula: subtotal = precio_unitario_actual × cantidad_cajas

        Args:
            obj: Instancia de ItemCarro.

        Returns:
            str: Subtotal como string decimal.
                 Ej: "45000.00" (15000.00 × 3 cajas).

        Nota:
            obj.insumo.precio_unitario es un Decimal de Python.
            obj.cantidad_cajas es un int de Python.
            Decimal × int = Decimal (precisión exacta, sin errores de float).
            Se convierte a string para la respuesta JSON.
        """
        return str(obj.insumo.precio_unitario * obj.cantidad_cajas)


# ============================================================================
# SERIALIZADOR: CarroSerializer
# ============================================================================
# Serializa el carrito de compras completo con todos sus items anidados
# y un total estimado calculado dinámicamente.
#
# Ejemplo de respuesta JSON:
# {
#     "id": 1,
#     "estado": "ACTIVO",
#     "items": [
#         {
#             "id": 1,
#             "insumo": 5,
#             "nombre_insumo": "Amoxil 500mg",
#             "precio_unitario_insumo": "15000.00",
#             "cantidad_cajas": 3,
#             "subtotal": "45000.00"
#         },
#         {
#             "id": 2,
#             "insumo": 8,
#             "nombre_insumo": "Paracetamol MK",
#             "precio_unitario_insumo": "5000.00",
#             "cantidad_cajas": 10,
#             "subtotal": "50000.00"
#         }
#     ],
#     "total_estimado": "95000.00"
# }
# ============================================================================
class CarroSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Carro (carrito de compras).

    Incluye:
    - items: Lista anidada de ItemCarroSerializer (todos los items del carrito).
    - total_estimado: Suma de subtotales de todos los items (campo calculado).
    - estado: Estado actual del carrito (ACTIVO/CONVERTIDO).
    """

    # -----------------------------------------------------------------------
    # Campo anidado: items (relación inversa)
    # -----------------------------------------------------------------------
    # ItemCarroSerializer(many=True, read_only=True):
    #
    # many=True: Indica que la relación es de uno-a-muchos (1:N).
    # Un carrito tiene MÚLTIPLES items. DRF serializa cada uno y retorna
    # una lista JSON de objetos.
    #
    # read_only=True: Los items se muestran en la respuesta pero no se
    # pueden crear/modificar a través del CarroSerializer. La gestión de
    # items (agregar, modificar cantidad, eliminar) se hace a través de
    # endpoints separados que usan ItemCarroSerializer directamente.
    #
    # source='items': DRF accede a carro.items.all() para obtener los items.
    # 'items' es el related_name definido en ItemCarro.carro FK.
    # Como el campo se llama igual que el related_name, no necesitamos
    # especificar source explícitamente (DRF lo resuelve por convención).
    items = ItemCarroSerializer(many=True, read_only=True)

    # -----------------------------------------------------------------------
    # Campo calculado: total_estimado
    # -----------------------------------------------------------------------
    # Suma de todos los subtotales de los items del carrito.
    # Es "estimado" porque usa precios actuales, no los precios congelados
    # que se guardarán en ItemSolicitud al confirmar el pedido.
    # Los precios pueden cambiar entre el momento de agregar al carrito
    # y el momento de confirmar la solicitud.
    total_estimado = serializers.SerializerMethodField()
    requiere_receta = serializers.SerializerMethodField()

    class Meta:
        model = Carro
        fields = ['id', 'estado', 'items', 'total_estimado', 'requiere_receta']

    def get_requiere_receta(self, obj):
        return any(item.insumo.requiere_receta for item in obj.items.all())

    def get_total_estimado(self, obj):
        """
        Calcula la suma de subtotales de todos los items del carrito.

        Fórmula: total = Σ(insumo.precio_unitario × item.cantidad_cajas)
                 para cada item en el carrito.

        Args:
            obj: Instancia del modelo Carro.

        Returns:
            str: Total estimado como string decimal.
                 Ej: "95000.00" (suma de todos los subtotales).

        Implementación:
            1. obj.items.all() → QuerySet de todos los ItemCarro del carrito.
               Ejecuta: SELECT * FROM insumos_itemcarro WHERE carro_id = obj.id
            2. Para cada item, calcula: item.insumo.precio_unitario × item.cantidad_cajas
               Esto ejecuta un JOIN con insumos_insumo para obtener el precio.
            3. sum() acumula todos los subtotales.

        Optimización posible:
            Para carros con muchos items, se podría usar aggregate() con
            Sum y F() expressions para calcular el total en una sola
            consulta SQL en lugar de iterar en Python. Ejemplo:
            obj.items.aggregate(total=Sum(F('insumo__precio_unitario') * F('cantidad_cajas')))
        """
        total = sum(
            item.insumo.precio_unitario * item.cantidad_cajas
            for item in obj.items.all()
        )
        return str(total)


# ============================================================================
# SERIALIZADOR: ItemSolicitudSerializer
# ============================================================================
# Serializa cada línea/item dentro de una solicitud de pedido.
# A diferencia de ItemCarroSerializer, aquí el precio es HISTÓRICO
# (congelado al momento de crear la solicitud), no el precio actual.
#
# Ejemplo de respuesta JSON:
# {
#     "id": 1,
#     "insumo": 5,
#     "nombre_insumo": "Amoxil 500mg",
#     "precio_unitario_historico": "15000.00",
#     "cantidad_cajas": 3,
#     "subtotal": "45000.00"
# }
# ============================================================================
class ItemSolicitudSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo ItemSolicitud (item de una solicitud).

    Incluye el precio_unitario_historico (congelado) y un subtotal calculado.
    El precio histórico NO cambia aunque se actualice el precio del insumo.
    """

    # -----------------------------------------------------------------------
    # Campo calculado: nombre_insumo
    # -----------------------------------------------------------------------
    # Muestra el nombre del insumo para referencia visual.
    nombre_insumo = serializers.SerializerMethodField()

    # -----------------------------------------------------------------------
    # Campo calculado: subtotal
    # -----------------------------------------------------------------------
    # Calcula precio_unitario_HISTORICO × cantidad_cajas.
    # Usa el precio congelado, NO el precio actual del insumo.
    # Esto garantiza que el total de la solicitud sea inmutable.
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemSolicitud
        # Campos expuestos. NO incluimos 'solicitud' porque el item
        # siempre se muestra anidado dentro de SolicitudSerializer.
        fields = [
            'id',
            'insumo',
            'nombre_insumo',
            'precio_unitario_historico',
            'cantidad_cajas',
            'subtotal',
        ]

    def get_nombre_insumo(self, obj):
        """
        Retorna el nombre comercial del insumo referenciado.

        Args:
            obj: Instancia de ItemSolicitud.

        Returns:
            str: Nombre comercial del insumo.
        """
        return obj.insumo.nombre_comercial

    def get_subtotal(self, obj):
        """
        Calcula el subtotal usando el precio HISTÓRICO (congelado).

        Fórmula: subtotal = precio_unitario_historico × cantidad_cajas

        IMPORTANTE: Usa precio_unitario_HISTORICO, no insumo.precio_unitario.
        El precio histórico se capturó al momento de crear la solicitud
        y NO cambia aunque el gestor actualice los precios del insumo.

        Args:
            obj: Instancia de ItemSolicitud.

        Returns:
            str: Subtotal como string decimal.
        """
        return str(obj.precio_unitario_historico * obj.cantidad_cajas)


# ============================================================================
# SERIALIZADOR: SolicitudSerializer
# ============================================================================
# Serializa una solicitud completa de pedido con todos sus items anidados.
# Incluye el nombre del solicitante, el estado, el total y la fecha.
#
# Ejemplo de respuesta JSON:
# {
#     "id": 1,
#     "usuario": "hospital_uc",
#     "estado": "PAGADO",
#     "total": "95000.00",
#     "creado_en": "2026-10-01T00:00:00-03:00",
#     "items": [
#         {
#             "id": 1,
#             "insumo": 5,
#             "nombre_insumo": "Amoxil 500mg",
#             "precio_unitario_historico": "15000.00",
#             "cantidad_cajas": 3,
#             "subtotal": "45000.00"
#         }
#     ]
# }
# ============================================================================
# ============================================================================
# SERIALIZADOR: RecetaMedicaSerializer
# ============================================================================
class RecetaMedicaSerializer(serializers.ModelSerializer):
    """
    Serializador para la auditoría y gestión de Recetas Médicas.
    """
    nombre_insumo = serializers.CharField(source='insumo.nombre_comercial', read_only=True)
    nombre_usuario = serializers.CharField(source='usuario.username', read_only=True)
    nombre_revisor = serializers.CharField(source='revisado_por.username', read_only=True)

    class Meta:
        model = RecetaMedica
        fields = [
            'id',
            'solicitud',
            'usuario',
            'nombre_usuario',
            'insumo',
            'nombre_insumo',
            'folio_receta',
            'medico_prescriptor',
            'rut_medico',
            'institucion_salud',
            'archivo_receta',
            'diagnostico',
            'estado',
            'observaciones_farmaceutico',
            'revisado_por',
            'nombre_revisor',
            'fecha_revision',
            'creado_en',
        ]
        read_only_fields = ['id', 'estado', 'revisado_por', 'fecha_revision', 'creado_en']


# ============================================================================
# SERIALIZADOR: SolicitudSerializer
# ============================================================================
class SolicitudSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Solicitud (pedido formal).

    Incluye:
    - items: Lista anidada de ItemSolicitudSerializer.
    - recetas: Lista anidada de RecetaMedicaSerializer.
    - usuario: Username del solicitante (campo calculado).
    - tenant_nombre: Nombre del Tenant de la venta.
    """
    items = ItemSolicitudSerializer(many=True, read_only=True)
    recetas = RecetaMedicaSerializer(many=True, read_only=True)
    usuario = serializers.SerializerMethodField()
    tenant_nombre = serializers.CharField(source='tenant.nombre', read_only=True)

    class Meta:
        model = Solicitud
        fields = [
            'id',
            'tenant',
            'tenant_nombre',
            'usuario',
            'estado',
            'requiere_receta',
            'motivo_cancelacion',
            'total',
            'creado_en',
            'items',
            'recetas',
        ]

    def get_usuario(self, obj):
        return obj.user.username

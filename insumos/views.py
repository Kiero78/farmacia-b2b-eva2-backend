"""
============================================================================
VIEWS.PY - App 'insumos'
============================================================================
Este módulo define los ViewSets y vistas de la API para la app 'insumos'.
Implementa la capa de endpoints HTTP que conecta las peticiones del
frontend con los modelos, serializadores y servicios transaccionales.

Arquitectura de vistas en DRF:
-------------------------------
DRF ofrece varios niveles de abstracción para vistas:

1. APIView: Nivel más bajo. Métodos HTTP manuales (get, post, put, delete).
2. GenericAPIView + Mixins: Combina vista genérica con mixins reutilizables.
3. ViewSet: Agrupa acciones CRUD en una sola clase. Se conecta a URLs
   mediante un Router que genera las rutas automáticamente.
4. ModelViewSet: ViewSet que incluye TODAS las acciones CRUD
   (list, create, retrieve, update, partial_update, destroy).

Usamos ModelViewSet para InsumoViewSet y SolicitudViewSet porque
necesitamos CRUD completo. Para el carrito, usamos vistas más
específicas porque la lógica no es CRUD estándar.

Control de acceso (RBAC):
--------------------------
Cada vista define sus permission_classes para restringir el acceso
según el rol del usuario:
- GESTOR: CRUD de insumos, ver/cambiar estado de todas las solicitudes.
- INSTITUCION: Leer insumos, gestionar carrito, crear/ver solicitudes propias.

Filtrado y búsqueda:
---------------------
InsumoViewSet implementa filtrado por categoría y búsqueda por texto
usando DjangoFilterBackend y SearchFilter de DRF.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# status: Constantes HTTP de DRF para respuestas (200, 201, 400, 404, etc.).
# Usar constantes en lugar de números mejora la legibilidad del código.
# Ejemplo: status.HTTP_201_CREATED en lugar de 201.
from rest_framework import status

# viewsets: Módulo con las clases base para ViewSets.
# ModelViewSet proporciona list, create, retrieve, update, partial_update, destroy.
from rest_framework import viewsets

# Response: Clase de DRF que genera respuestas HTTP con contenido JSON.
# A diferencia de HttpResponse de Django, Response negocia el formato
# de salida (JSON, XML, etc.) según el header Accept del cliente.
from rest_framework.response import Response

# decorators: action permite definir acciones custom en un ViewSet
# (endpoints adicionales más allá del CRUD estándar).
from rest_framework.decorators import action

# permissions: Clases de permisos integradas en DRF.
# IsAuthenticated: Solo usuarios autenticados (token JWT válido).
# AllowAny: Cualquier usuario (incluso no autenticados).
from rest_framework.permissions import IsAuthenticated, AllowAny

# views: APIView es la clase base para vistas basadas en clases en DRF.
from rest_framework.views import APIView

# filters: SearchFilter permite búsqueda por texto en campos especificados.
from rest_framework.filters import SearchFilter

# DjangoFilterBackend: Permite filtrado por campos exactos usando query params.
from django_filters.rest_framework import DjangoFilterBackend

# Importamos nuestros modelos.
from insumos.models import (
    CategoriaInsumo,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    RecetaMedica,
)

# Importamos nuestros serializadores.
from insumos.serializers import (
    CategoriaInsumoSerializer,
    InsumoSerializer,
    ItemCarroSerializer,
    CarroSerializer,
    SolicitudSerializer,
    RecetaMedicaSerializer,
)

# Importamos nuestros servicios transaccionales.
from insumos.services import confirmar_solicitud, cambiar_estado_solicitud, auditar_receta_solicitud

# Importamos nuestros permisos RBAC personalizados.
from usuarios.permissions import IsGestorBodega, IsInstitucionMedica, IsAdminPagina, IsSuperAdmin


# ============================================================================
# VIEWSET: CategoriaInsumoViewSet
# ============================================================================
# ViewSet para CRUD completo de categorías de insumos médicos.
#
# Endpoints generados automáticamente por el Router:
#   GET    /api/categorias/       → list()     → Lista todas las categorías.
#   POST   /api/categorias/       → create()   → Crea una categoría (GESTOR).
#   GET    /api/categorias/{id}/  → retrieve() → Detalle de una categoría.
#   PUT    /api/categorias/{id}/  → update()   → Actualiza una categoría (GESTOR).
#   PATCH  /api/categorias/{id}/  → partial_update() → Actualización parcial (GESTOR).
#   DELETE /api/categorias/{id}/  → destroy()  → Elimina una categoría (GESTOR).
#
# Permisos:
# - Lectura (GET): Cualquier usuario autenticado.
# - Escritura (POST, PUT, PATCH, DELETE): Solo GESTOR.
# ============================================================================
class CategoriaInsumoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de categorías de insumos médicos.

    Lectura disponible para usuarios autenticados.
    Escritura restringida a gestores de bodega.
    """

    # queryset: Define el conjunto base de datos que maneja este ViewSet.
    # .all() retorna todas las categorías. El Router usa este queryset
    # para resolver las URLs de detalle (ej: /categorias/1/).
    queryset = CategoriaInsumo.objects.all()

    # serializer_class: Serializador usado para convertir modelos a JSON
    # y viceversa. Se aplica a todas las acciones del ViewSet.
    serializer_class = CategoriaInsumoSerializer

    # -----------------------------------------------------------------------
    # get_permissions: Control de acceso dinámico por acción
    # -----------------------------------------------------------------------
    # Sobrescribimos get_permissions() para aplicar permisos DIFERENTES
    # según la acción HTTP que se está ejecutando.
    #
    # ¿Por qué no usar permission_classes directamente?
    # permission_classes se aplica a TODAS las acciones por igual.
    # Necesitamos reglas diferentes: GET es público, POST/PUT/DELETE es GESTOR.
    #
    # self.action: Atributo del ViewSet que indica la acción actual:
    #   'list', 'create', 'retrieve', 'update', 'partial_update', 'destroy'
    # -----------------------------------------------------------------------
    def get_permissions(self):
        """
        Retorna permisos según la acción del ViewSet.

        - list, retrieve: IsAuthenticated (cualquier usuario autenticado).
        - create, update, partial_update, destroy: IsGestorBodega.
        """
        if self.action in ['list', 'retrieve']:
            # Acciones de LECTURA: cualquier usuario autenticado.
            # IsAuthenticated verifica que request.user.is_authenticated == True.
            permission_classes = [IsAuthenticated]
        else:
            # Acciones de ESCRITURA: solo gestores de bodega.
            # IsGestorBodega verifica autenticación + rol == 'GESTOR'.
            permission_classes = [IsGestorBodega]
        # Instanciar cada clase de permiso y retornar la lista.
        # DRF requiere instancias, no clases.
        return [permission() for permission in permission_classes]


# ============================================================================
# VIEWSET: InsumoViewSet
# ============================================================================
# ViewSet para CRUD de insumos médicos con filtrado y búsqueda avanzada.
#
# Endpoints generados automáticamente por el Router:
#   GET    /api/insumos/         → list()     → Lista insumos (con filtros).
#   POST   /api/insumos/         → create()   → Crea un insumo (GESTOR).
#   GET    /api/insumos/{id}/    → retrieve() → Detalle de un insumo.
#   PUT    /api/insumos/{id}/    → update()   → Actualiza un insumo (GESTOR).
#   PATCH  /api/insumos/{id}/    → partial_update() → Actualización parcial.
#   DELETE /api/insumos/{id}/    → destroy()  → Elimina un insumo (GESTOR).
#
# Filtros disponibles (query params):
#   ?categoria=3                 → Insumos de la categoría con ID 3.
#   ?fecha_vencimiento=2025-12-31 → Insumos con esa fecha de vencimiento.
#   ?precio_unitario__gte=5000   → Insumos con precio >= 5000.
#   ?precio_unitario__lte=20000  → Insumos con precio <= 20000.
#   ?search=amoxicilina          → Búsqueda en nombre_comercial y principio_activo.
#
# Permisos:
# - Lectura (GET): Cualquier usuario autenticado.
# - Escritura (POST, PUT, PATCH, DELETE): Solo GESTOR.
# ============================================================================
class InsumoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de insumos médicos con filtrado y búsqueda.

    Filtros: categoría, fecha_vencimiento, rango de precio.
    Búsqueda: por nombre_comercial y principio_activo.
    Lectura: usuarios autenticados. Escritura: gestores de bodega.
    """

    # queryset: Todos los insumos, ordenados por nombre_comercial (definido
    # en el Meta del modelo con ordering = ['nombre_comercial']).
    queryset = Insumo.objects.all()

    # serializer_class: InsumoSerializer incluye el campo calculado
    # 'nombre_categoria' para legibilidad.
    serializer_class = InsumoSerializer

    # -----------------------------------------------------------------------
    # Backends de filtrado
    # -----------------------------------------------------------------------
    # filter_backends: Lista de clases que procesan los filtros de la petición.
    # Cada backend se ejecuta en orden y filtra el queryset resultante.
    #
    # DjangoFilterBackend: Filtrado EXACTO por campos.
    #   Genera cláusulas WHERE en SQL según los query params.
    #   Ejemplo: ?categoria=3 → WHERE categoria_id = 3
    #
    # SearchFilter: Búsqueda por TEXTO PARCIAL en campos.
    #   Genera cláusulas ILIKE/ICONTAINS en SQL.
    #   Ejemplo: ?search=amoxi → WHERE nombre_comercial ILIKE '%amoxi%'
    #            OR principio_activo ILIKE '%amoxi%'
    filter_backends = [DjangoFilterBackend, SearchFilter]

    # -----------------------------------------------------------------------
    # filterset_fields: Campos para filtrado exacto (DjangoFilterBackend)
    # -----------------------------------------------------------------------
    # Define qué campos del modelo se pueden usar como filtros en la URL.
    #
    # Formato: {campo_modelo: [lookups_permitidos]}
    #
    # Lookups de Django ORM usados:
    # - 'exact': Igualdad exacta (=). Ejemplo: ?categoria=3
    # - 'gte': Greater Than or Equal (>=). Ejemplo: ?precio_unitario__gte=5000
    # - 'lte': Less Than or Equal (<=). Ejemplo: ?precio_unitario__lte=20000
    #
    # Combinando gte y lte se logra un filtro de RANGO:
    #   ?precio_unitario__gte=5000&precio_unitario__lte=20000
    #   → WHERE precio_unitario >= 5000 AND precio_unitario <= 20000
    #
    # 'categoria': Filtra por ID de categoría (FK).
    # 'fecha_vencimiento': Filtra por fecha exacta, o rango con gte/lte.
    # 'precio_unitario': Filtra por precio exacto o rango con gte/lte.
    filterset_fields = {
        'categoria': ['exact'],
        'fecha_vencimiento': ['exact', 'gte', 'lte'],
        'precio_unitario': ['exact', 'gte', 'lte'],
    }

    # -----------------------------------------------------------------------
    # search_fields: Campos para búsqueda por texto (SearchFilter)
    # -----------------------------------------------------------------------
    # Define en qué campos se busca cuando el cliente envía ?search=texto.
    #
    # SearchFilter usa ICONTAINS por defecto (case-insensitive, parcial):
    #   ?search=amoxi → nombre_comercial ILIKE '%amoxi%'
    #                    OR principio_activo ILIKE '%amoxi%'
    #
    # El cliente solo necesita un parámetro 'search' y DRF busca en
    # TODOS los campos listados con OR lógico.
    search_fields = ['nombre_comercial', 'principio_activo']

    # -----------------------------------------------------------------------
    # get_permissions: Control de acceso dinámico
    # -----------------------------------------------------------------------
    def get_permissions(self):
        """
        Lectura: autenticados. Escritura: solo gestores.

        self.action puede ser:
        - 'list': GET /api/insumos/ (listar todos).
        - 'retrieve': GET /api/insumos/{id}/ (detalle).
        - 'create': POST /api/insumos/ (crear nuevo).
        - 'update': PUT /api/insumos/{id}/ (actualización completa).
        - 'partial_update': PATCH /api/insumos/{id}/ (actualización parcial).
        - 'destroy': DELETE /api/insumos/{id}/ (eliminar).
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsGestorBodega]
        return [permission() for permission in permission_classes]


# ============================================================================
# VISTA: CarroView (Carrito de compras)
# ============================================================================
# Vista basada en APIView para gestionar el carrito del usuario autenticado.
# No usamos ModelViewSet porque el carrito tiene lógica especial:
# - Cada usuario tiene UN solo carrito activo (se crea automáticamente).
# - GET retorna el carrito con todos sus items.
# - DELETE vacía el carrito (elimina todos los items, no el carrito).
#
# Esta vista es exclusiva para usuarios con rol INSTITUCION.
# ============================================================================
class CarroView(APIView):
    """
    Vista para obtener, agregar items y vaciar el carrito de compras del usuario.

    Endpoints:
        GET    /api/carro/ o /api/carro-insumos/  → Retorna el carrito con sus items.
        POST   /api/carro/ o /api/carro-insumos/  → Agrega o actualiza un item directamente.
        DELETE /api/carro/ o /api/carro-insumos/  → Vacía el carrito (elimina todos los items).

    Permisos: Solo usuarios clientes / instituciones (IsInstitucionMedica).
    """
    permission_classes = [IsInstitucionMedica]

    def _get_or_create_carro(self, user):
        carro, created = Carro.objects.get_or_create(
            user=user,
            defaults={'estado': 'ACTIVO'}
        )
        if carro.estado != 'ACTIVO':
            carro.estado = 'ACTIVO'
            carro.save()
        return carro

    def get(self, request):
        carro = self._get_or_create_carro(request.user)
        serializer = CarroSerializer(carro)
        return Response(serializer.data)

    def post(self, request):
        """
        Agrega un insumo al carrito de compras institucional.
        Permite invocar directamente POST /api/carro-insumos/ con {"insumo": id, "cantidad_cajas": n}.
        """
        carro = self._get_or_create_carro(request.user)
        insumo_id = request.data.get('insumo')
        cantidad = request.data.get('cantidad_cajas', 1)

        if not insumo_id:
            return Response(
                {'detalle': 'Debe proporcionar el ID del insumo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                return Response(
                    {'detalle': 'La cantidad de cajas debe ser mayor a 0.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'detalle': 'La cantidad de cajas debe ser un número entero.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item, created = ItemCarro.objects.update_or_create(
            carro=carro,
            insumo_id=insumo_id,
            defaults={'cantidad_cajas': cantidad}
        )

        serializer = ItemCarroSerializer(item)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=http_status)

    def delete(self, request):
        carro = Carro.objects.filter(user=request.user).first()
        if carro:
            carro.items.all().delete()

        return Response(
            {'detalle': 'El carro ha sido vaciado.'},
            status=status.HTTP_200_OK
        )


# ============================================================================
# VISTA: ItemCarroView (Items del carrito)
# ============================================================================
# Vista para gestionar items individuales dentro del carrito.
# Permite agregar insumos, ajustar cantidades y eliminar items específicos.
#
# A diferencia de CarroView (que gestiona el carrito como unidad),
# esta vista gestiona items individuales (líneas del carrito).
# ============================================================================
class ItemCarroView(APIView):
    """
    Vista para gestionar items individuales del carrito de compras.

    Endpoints:
        POST   /api/carro/items/           → Agrega un insumo al carrito.
        PUT    /api/carro/items/{item_id}/  → Ajusta la cantidad de un item.
        DELETE /api/carro/items/{item_id}/  → Elimina un item del carrito.

    Permisos: Solo usuarios con rol INSTITUCION.
    """
    permission_classes = [IsInstitucionMedica]

    def post(self, request):
        """
        Agrega un insumo al carrito o actualiza la cantidad si ya existe.

        Implementa lógica de "upsert" (update or insert):
        - Si el insumo NO está en el carrito → lo agrega (INSERT).
        - Si el insumo YA está en el carrito → actualiza la cantidad (UPDATE).

        Esto respeta el constraint unique_together=['carro', 'insumo']
        del modelo ItemCarro, evitando duplicados.

        Request body:
            {"insumo": 5, "cantidad_cajas": 3}

        Args:
            request: Petición HTTP. request.data contiene el body parseado.

        Returns:
            Response 201: Item creado/actualizado con sus datos serializados.
            Response 400: Datos inválidos (insumo no existe, cantidad inválida).
        """
        # Paso 1: Obtener o crear el carrito activo del usuario.
        carro, _ = Carro.objects.get_or_create(
            user=request.user,
            estado='ACTIVO'
        )

        # Paso 2: Extraer datos del request.
        # request.data es un diccionario con el body parseado por DRF.
        insumo_id = request.data.get('insumo')
        cantidad = request.data.get('cantidad_cajas', 1)

        # Paso 3: Validar que se proporcionó un insumo.
        if not insumo_id:
            return Response(
                {'detalle': 'Debe proporcionar el ID del insumo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Paso 4: Agregar o actualizar el item en el carrito.
        # update_or_create(): Método atómico de Django similar a get_or_create().
        # 1. Busca un ItemCarro con carro=carro AND insumo_id=insumo_id.
        # 2. Si EXISTE: actualiza con defaults (cantidad_cajas=cantidad).
        # 3. Si NO EXISTE: crea un nuevo ItemCarro con todos los parámetros.
        # Retorna (objeto, created) donde created es True si se creó nuevo.
        #
        # defaults: Diccionario de campos a establecer al crear O actualizar.
        # Los campos que NO están en defaults se usan solo como filtros.
        #
        # Esto reemplaza la lógica manual de try/except IntegrityError
        # y respeta el unique_together del modelo.
        item, created = ItemCarro.objects.update_or_create(
            carro=carro,
            insumo_id=insumo_id,
            defaults={'cantidad_cajas': cantidad}
        )

        # Paso 5: Serializar y retornar el item.
        serializer = ItemCarroSerializer(item)
        # 201 Created si es nuevo, 200 OK si se actualizó.
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=http_status)

    def put(self, request, item_id=None):
        """
        Actualiza la cantidad de cajas de un item específico del carrito.

        Solo modifica la cantidad, no cambia el insumo. Si se necesita
        cambiar el insumo, se debe eliminar el item y crear uno nuevo.

        URL: PUT /api/carro/items/{item_id}/
        Request body: {"cantidad_cajas": 5}

        Args:
            request: Petición HTTP con los nuevos datos.
            item_id: ID del ItemCarro a modificar (de la URL).

        Returns:
            Response 200: Item actualizado con sus datos serializados.
            Response 404: Item no encontrado en el carrito del usuario.
        """
        # Buscar el item verificando que pertenezca al carrito ACTIVO
        # del usuario autenticado. Esto previene que un usuario modifique
        # items del carrito de OTRO usuario (seguridad).
        item = ItemCarro.objects.filter(
            id=item_id,
            carro__user=request.user,
            carro__estado='ACTIVO'
        ).first()

        if not item:
            return Response(
                {'detalle': 'Item no encontrado en tu carro.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Actualizar la cantidad.
        # request.data.get('cantidad_cajas', item.cantidad_cajas):
        # Si no se envía 'cantidad_cajas' en el body, mantiene el valor actual.
        item.cantidad_cajas = request.data.get('cantidad_cajas', item.cantidad_cajas)
        item.save()

        serializer = ItemCarroSerializer(item)
        return Response(serializer.data)

    def delete(self, request, item_id=None):
        """
        Elimina un item específico del carrito del usuario.

        URL: DELETE /api/carro/items/{item_id}/

        Validación de seguridad: Solo se puede eliminar un item que
        pertenezca al carrito ACTIVO del usuario autenticado.

        Args:
            request: Petición HTTP.
            item_id: ID del ItemCarro a eliminar (de la URL).

        Returns:
            Response 200: Confirmación de eliminación.
            Response 404: Item no encontrado.
        """
        item = ItemCarro.objects.filter(
            id=item_id,
            carro__user=request.user,
            carro__estado='ACTIVO'
        ).first()

        if not item:
            return Response(
                {'detalle': 'Item no encontrado en tu carro.'},
                status=status.HTTP_404_NOT_FOUND
            )

        item.delete()
        return Response(
            {'detalle': 'Item eliminado del carro.'},
            status=status.HTTP_200_OK
        )


# ============================================================================
# VIEWSET: SolicitudViewSet
# ============================================================================
# ViewSet para gestionar solicitudes de pedido con acciones custom.
# Implementa RBAC dinámico: el queryset y los permisos cambian según
# el rol del usuario autenticado.
#
# Endpoints estándar del Router:
#   GET  /api/solicitudes/       → list() → Lista solicitudes (filtrada por rol).
#   GET  /api/solicitudes/{id}/  → retrieve() → Detalle de una solicitud.
#
# Acciones custom:
#   POST  /api/solicitudes/confirmar/              → Confirma el carrito.
#   PATCH /api/solicitudes/{id}/cambiar-estado/     → Cambia estado (GESTOR).
#
# Control de acceso por rol:
# - INSTITUCION: Ve solo SUS solicitudes. Puede confirmar carrito.
# - GESTOR: Ve TODAS las solicitudes. Puede cambiar estados.
# ============================================================================
class SolicitudViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de solicitudes de pedido.

    Queryset filtrado por rol:
    - INSTITUCION: Solo sus propias solicitudes.
    - GESTOR: Todas las solicitudes del sistema.

    Acciones custom:
    - confirmar: Convierte el carrito en solicitud.
    - cambiar_estado: Cambia el estado de una solicitud.
    """
    serializer_class = SolicitudSerializer

    # -----------------------------------------------------------------------
    # get_queryset: Queryset dinámico según el rol del usuario
    # -----------------------------------------------------------------------
    # Sobrescribimos get_queryset() en lugar de definir queryset como
    # atributo de clase porque el queryset depende del usuario autenticado.
    #
    # ¿Por qué no filtrar en get_permissions()?
    # Los permisos controlan el ACCESO al endpoint (permitir/denegar).
    # El queryset controla los DATOS visibles. Son responsabilidades
    # diferentes que se manejan en métodos diferentes.
    # -----------------------------------------------------------------------
    def get_queryset(self):
        """
        Retorna el queryset de solicitudes filtrado según el rol y Tenant:
        - SUPERADMIN: Todas las solicitudes del sistema.
        - ADMIN_PAGINA / GESTOR: Solicitudes del tenant asociado (o todas si no tiene tenant).
        - USUARIO / INSTITUCION: Solicitudes exclusivas del usuario autenticado.
        """
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'perfil'):
            return Solicitud.objects.none()

        qs = Solicitud.objects.select_related('user', 'tenant').prefetch_related(
            'items', 'items__insumo', 'recetas', 'recetas__insumo'
        )

        if user.perfil.es_superadmin:
            return qs.all()
        elif user.perfil.es_admin_pagina:
            if user.perfil.tenant:
                return qs.filter(tenant=user.perfil.tenant)
            return qs.all()
        elif user.perfil.es_usuario:
            return qs.filter(user=user)
        return Solicitud.objects.none()

    def get_permissions(self):
        """
        Define permisos según la acción:
        - confirmar, subir_receta: IsInstitucionMedica (compradores/pacientes).
        - cambiar_estado, revisar_receta: IsAdminPagina (farmacéuticos/gestores).
        - list, retrieve: IsAuthenticated (filtrado por get_queryset).
        """
        if self.action in ['confirmar', 'subir_receta']:
            permission_classes = [IsInstitucionMedica]
        elif self.action in ['cambiar_estado', 'revisar_receta']:
            permission_classes = [IsAdminPagina]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='confirmar')
    def confirmar(self, request):
        """
        Confirma el carrito del usuario generando la orden.
        Si incluye fármacos con receta médica, pasa a estado 'EN_REVISION'
        y genera la RecetaMedica para auditoría del administrador.
        """
        solicitud = confirmar_solicitud(request.user, datos_receta=request.data)
        serializer = SolicitudSerializer(solicitud)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='revisar-receta')
    def revisar_receta(self, request, pk=None):
        """
        Auditoría Farmacéutica de Receta Médica (solo Admin de Página / Superadmin).
        - decision: 'APROBAR' → Valida stock atómicamente, descuenta existencias y aprueba la orden a PAGADO.
        - decision: 'DENEGAR' → Rechaza la compra, cancela la orden sin descontar stock.
        """
        solicitud = self.get_object()
        decision = request.data.get('decision')
        observaciones = request.data.get('observaciones', '')

        if not decision:
            return Response(
                {'detalle': "Debe especificar 'decision': 'APROBAR' o 'DENEGAR'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        solicitud = auditar_receta_solicitud(
            solicitud=solicitud,
            admin_user=request.user,
            decision=decision,
            observaciones=observaciones
        )
        return Response(SolicitudSerializer(solicitud).data)

    @action(detail=True, methods=['post'], url_path='subir-receta')
    def subir_receta(self, request, pk=None):
        """
        Permite a un usuario asociar o actualizar los datos/documento de su receta médica
        en una solicitud en revisión.
        """
        solicitud = self.get_object()
        receta = solicitud.recetas.first()
        if not receta:
            receta = RecetaMedica.objects.create(solicitud=solicitud, usuario=request.user)

        for campo in ('folio_receta', 'medico_prescriptor', 'rut_medico', 'institucion_salud', 'diagnostico'):
            if campo in request.data:
                setattr(receta, campo, request.data[campo])

        if 'archivo_receta' in request.FILES:
            receta.archivo_receta = request.FILES['archivo_receta']

        receta.estado = 'PENDIENTE'
        receta.save()
        return Response(RecetaMedicaSerializer(receta).data)

    @action(detail=True, methods=['patch'], url_path='estado', url_name='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado de una solicitud (solo Gestor / Admin de Página).
        Repone stock automáticamente si la orden pasa a CANCELADO.
        """
        solicitud = self.get_object()
        nuevo_estado = request.data.get('estado')

        if not nuevo_estado:
            return Response(
                {'detalle': 'Debe proporcionar el nuevo estado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        estados_validos = [choice[0] for choice in Solicitud.ESTADO_CHOICES]
        if nuevo_estado not in estados_validos:
            return Response(
                {'detalle': f'Estado inválido. Opciones: {estados_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        solicitud = cambiar_estado_solicitud(solicitud, nuevo_estado)
        serializer = SolicitudSerializer(solicitud)
        return Response(serializer.data)


# ============================================================================
# VIEWSET: RecetaMedicaViewSet
# ============================================================================
class RecetaMedicaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la auditoría de Recetas Médicas por el Administrador de Página o Superadmin.
    """
    serializer_class = RecetaMedicaSerializer
    permission_classes = [IsAdminPagina]

    def get_queryset(self):
        user = self.request.user
        qs = RecetaMedica.objects.select_related(
            'solicitud', 'usuario', 'insumo', 'revisado_por'
        )
        if hasattr(user, 'perfil') and user.perfil.tenant and not user.perfil.es_superadmin:
            qs = qs.filter(solicitud__tenant=user.perfil.tenant)
        return qs.all()

    @action(detail=False, methods=['get'], url_path='pendientes')
    def pendientes(self, request):
        """Lista todas las recetas pendientes de revisión médica."""
        qs = self.get_queryset().filter(estado='PENDIENTE')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


from django.shortcuts import render
from .models import Insumo, Carro, Solicitud

def login_web(request):
    """Vista que renderiza la página de login con JWT (template)."""
    return render(request, 'insumos/login.html')

def catalogo_web(request):
    insumos = Insumo.objects.select_related('categoria').all()
    return render(request, 'insumos/catalogo.html', {'insumos': insumos})

def carro_web(request):
    carros = Carro.objects.filter(estado='ACTIVO').prefetch_related('items__insumo', 'user__perfil')
    return render(request, 'insumos/carro.html', {'carros': carros})

def solicitudes_web(request):
    solicitudes = Solicitud.objects.select_related('user__perfil').all().order_by('-creado_en')
    return render(request, 'insumos/solicitudes.html', {'solicitudes': solicitudes})

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)
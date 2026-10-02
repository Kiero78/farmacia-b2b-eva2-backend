"""
============================================================================
SERVICES.PY - Servicios Transaccionales de la App 'insumos'
============================================================================
Este módulo implementa la lógica de negocio TRANSACCIONAL del sistema B2B
de farmacia. Separa la lógica de negocio de las vistas (views.py) y los
serializadores (serializers.py), siguiendo el patrón Service Layer.

¿Por qué un Service Layer?
---------------------------
- Las VISTAS (views.py) manejan HTTP: reciben requests, retornan responses.
- Los SERIALIZADORES (serializers.py) manejan validación y conversión de datos.
- Los SERVICIOS (services.py) manejan la LÓGICA DE NEGOCIO compleja que
  involucra múltiples modelos, transacciones y reglas de dominio.

Separar la lógica en servicios permite:
1. Reutilizar la misma lógica desde diferentes vistas o comandos.
2. Testear la lógica de negocio de forma aislada (unit tests).
3. Mantener las vistas y serializadores simples y enfocados.

Funciones en este módulo:
--------------------------
- confirmar_solicitud(usuario): Convierte el carrito en solicitud formal.
- cambiar_estado_solicitud(solicitud, nuevo_estado): Cambia el estado de
  una solicitud con lógica de reposición de stock si se cancela.

Conceptos clave de base de datos usados:
------------------------------------------

1. transaction.atomic():
   ---------------------
   Crea un bloque transaccional ACID en la base de datos.
   ACID = Atomicidad, Consistencia, Aislamiento, Durabilidad.

   - ATOMICIDAD: Todas las operaciones dentro del bloque se ejecutan como
     una UNIDAD INDIVISIBLE. Si cualquier operación falla (error, excepción),
     TODAS las operaciones se revierten (ROLLBACK). Si todas tienen éxito,
     se confirman (COMMIT). No hay estados intermedios.

     Ejemplo: Si al descontar stock de 5 insumos, el 4to falla por stock
     insuficiente, los 3 descuentos anteriores se revierten automáticamente.
     La base de datos queda como si nada hubiera pasado.

   - CONSISTENCIA: La base de datos pasa de un estado válido a otro estado
     válido. Las constraints (FK, UNIQUE, CHECK) se verifican al hacer COMMIT.

   - AISLAMIENTO: Las operaciones dentro de la transacción son invisibles
     para otras transacciones concurrentes hasta que se hace COMMIT.
     Nivel por defecto en PostgreSQL: READ COMMITTED.

   - DURABILIDAD: Una vez que se hace COMMIT, los datos persisten incluso
     si el servidor se cae inmediatamente después (WAL = Write-Ahead Log).

   Sintaxis:
   ```python
   with transaction.atomic():
       # Todas las operaciones aquí son atómicas.
       # Si hay una excepción, se hace ROLLBACK automático.
       modelo1.save()
       modelo2.save()
       # Si modelo2.save() falla, modelo1.save() se revierte.
   ```

2. select_for_update():
   ---------------------
   Agrega una cláusula FOR UPDATE a la consulta SQL SELECT.
   Esto BLOQUEA las filas seleccionadas a nivel de base de datos,
   impidiendo que otras transacciones concurrentes las modifiquen
   hasta que la transacción actual termine (COMMIT o ROLLBACK).

   ¿Por qué es necesario?
   Sin select_for_update(), existe una CONDICIÓN DE CARRERA (race condition):

   Escenario sin bloqueo (PELIGROSO):
   -----------------------------------
   Tiempo  | Transacción A              | Transacción B
   --------+----------------------------+----------------------------
   T1      | Lee stock = 10             |
   T2      |                            | Lee stock = 10
   T3      | stock -= 8 → guarda 2     |
   T4      |                            | stock -= 5 → guarda 5  ← ¡INCORRECTO!
   Resultado: Stock debería ser -3 (error) o rechazar B, pero queda en 5.

   Escenario con select_for_update() (SEGURO):
   ---------------------------------------------
   Tiempo  | Transacción A              | Transacción B
   --------+----------------------------+----------------------------
   T1      | Lee stock = 10 (LOCK)      |
   T2      |                            | Intenta leer → BLOQUEADA (espera)
   T3      | stock -= 8 → guarda 2     |
   T4      | COMMIT → libera LOCK      |
   T5      |                            | Lee stock = 2 (LOCK)
   T6      |                            | stock -= 5 → FALLA (2 < 5)
   Resultado: A éxito, B rechazada correctamente. Integridad preservada.

   Sintaxis:
   ```python
   insumos = Insumo.objects.select_for_update().filter(id__in=ids)
   # Las filas están bloqueadas hasta que termine la transacción.
   ```

   IMPORTANTE: select_for_update() SOLO funciona dentro de un bloque
   transaction.atomic(). Fuera de una transacción, no tiene efecto.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError

from insumos.models import (
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
    Insumo,
    RecetaMedica,
)


def confirmar_solicitud(usuario, datos_receta=None):
    """
    Convierte el carrito activo del usuario en una solicitud formal de pedido.
    
    Lógica de Negocio y Regulación Sanitaria:
    1. Si algún insumo requiere receta médica:
       - La solicitud se crea en estado 'EN_REVISION'.
       - Se crea la RecetaMedica asociada.
       - El stock NO se descuenta hasta que el Administrador de Página/Farmacéutico
         audite la receta y autorice la venta.
    2. Si los insumos son de venta libre (sin receta):
       - Se valida y descuenta el stock de forma atómica con select_for_update().
       - La solicitud pasa directamente a estado 'PAGADO'.
    3. Liquidación del Carro:
       - Se eliminan los items del carro para dejarlo limpio y activo para futuros pedidos,
         garantizando la unicidad 1:1 de la relación Carro-User.
    """
    if datos_receta is None:
        datos_receta = {}

    with transaction.atomic():
        # 1. Obtener el carrito del usuario
        carro = Carro.objects.filter(user=usuario).first()
        if not carro:
            raise ValidationError({'detalle': 'No tienes un carro de compras activo.'})

        items_carro = carro.items.select_related('insumo').all()
        if not items_carro.exists():
            raise ValidationError({'detalle': 'El carro de compras está vacío.'})

        # 2. Determinar si algún insumo requiere receta médica
        requiere_receta = any(
            item.insumo.requiere_receta or item.insumo.tipo_venta in ('RECETA_SIMPLE', 'RECETA_RETENIDA')
            for item in items_carro
        )

        insumo_ids = [item.insumo_id for item in items_carro]
        insumos_bloqueados = Insumo.objects.select_for_update().in_bulk(insumo_ids)

        # 3. Validar disponibilidad previa de stock
        for item in items_carro:
            insumo = insumos_bloqueados[item.insumo_id]
            if insumo.stock_cajas < item.cantidad_cajas:
                raise ValidationError({
                    'detalle': (
                        f'Stock insuficiente para "{insumo.nombre_comercial}". '
                        f'Disponible: {insumo.stock_cajas} cajas, '
                        f'solicitado: {item.cantidad_cajas} cajas.'
                    )
                })

        # 4. Asignar Tenant si corresponde
        perfil = getattr(usuario, 'perfil', None)
        tenant_obj = perfil.tenant if (perfil and perfil.tenant) else None
        if not tenant_obj and items_carro.first().insumo.tenant:
            tenant_obj = items_carro.first().insumo.tenant

        # 5. Crear la Solicitud
        # Si requiere receta queda 'EN_REVISION'. Si es venta libre pasa a 'PAGADO'.
        estado_inicial = 'EN_REVISION' if requiere_receta else 'PAGADO'

        solicitud = Solicitud.objects.create(
            user=usuario,
            tenant=tenant_obj,
            estado=estado_inicial,
            requiere_receta=requiere_receta,
            total=0
        )

        # 6. Crear ItemSolicitud (congelando precios históricos)
        total_calculado = 0
        for item in items_carro:
            insumo = insumos_bloqueados[item.insumo_id]

            ItemSolicitud.objects.create(
                solicitud=solicitud,
                insumo=insumo,
                precio_unitario_historico=insumo.precio_unitario,
                cantidad_cajas=item.cantidad_cajas,
            )

            # Si NO requiere receta, se descuenta stock de inmediato
            if not requiere_receta:
                insumo.stock_cajas -= item.cantidad_cajas
                insumo.save()

            total_calculado += insumo.precio_unitario * item.cantidad_cajas

        solicitud.total = total_calculado
        solicitud.save()

        # 7. Si requiere receta, registrar la RecetaMedica para posterior auditoría
        if requiere_receta:
            # Buscar el primer insumo que requirió receta
            insumo_con_receta = next(
                (item.insumo for item in items_carro if item.insumo.requiere_receta or item.insumo.tipo_venta != 'LIBRE'),
                None
            )
            RecetaMedica.objects.create(
                solicitud=solicitud,
                usuario=usuario,
                insumo=insumo_con_receta,
                folio_receta=datos_receta.get('folio_receta', ''),
                medico_prescriptor=datos_receta.get('medico_prescriptor', ''),
                rut_medico=datos_receta.get('rut_medico', ''),
                institucion_salud=datos_receta.get('institucion_salud', ''),
                diagnostico=datos_receta.get('diagnostico', ''),
                archivo_receta=datos_receta.get('archivo_receta', None),
                estado='PENDIENTE'
            )

        # 8. Liquidar los items del carro y asegurar que siga activo para futuras compras
        carro.items.all().delete()
        carro.estado = 'ACTIVO'
        carro.save()

        return solicitud


def auditar_receta_solicitud(solicitud, admin_user, decision, observaciones=""):
    """
    Permite al Administrador de Página / Farmacéutico auditar una receta médica
    para APROBAR la venta (descontando stock atómicamente) o DENEGAR la compra.

    Args:
        solicitud: Instancia de Solicitud en estado 'EN_REVISION'.
        admin_user: Instancia de User con rol ADMIN_PAGINA, GESTOR o SUPERADMIN.
        decision: 'APROBAR' o 'DENEGAR'.
        observaciones: Comentario o justificación del farmacéutico.
    """
    decision_normalizada = decision.strip().upper()
    if decision_normalizada not in ('APROBAR', 'DENEGAR', 'RECHAZAR'):
        raise ValidationError({'detalle': "La decisión debe ser 'APROBAR' o 'DENEGAR'."})

    with transaction.atomic():
        receta = solicitud.recetas.first()

        if decision_normalizada == 'APROBAR':
            # Bloquear insumos y validar existencias al momento de aprobar la venta
            items = solicitud.items.select_related('insumo').all()
            insumo_ids = [item.insumo_id for item in items]
            insumos_bloqueados = Insumo.objects.select_for_update().in_bulk(insumo_ids)

            # Validar stock
            for item in items:
                insumo = insumos_bloqueados[item.insumo_id]
                if insumo.stock_cajas < item.cantidad_cajas:
                    raise ValidationError({
                        'detalle': (
                            f'No es posible aprobar la venta: Stock insuficiente para "{insumo.nombre_comercial}". '
                            f'Disponible: {insumo.stock_cajas} cajas, requerido: {item.cantidad_cajas}.'
                        )
                    })

            # Descontar stock atómicamente
            for item in items:
                insumo = insumos_bloqueados[item.insumo_id]
                insumo.stock_cajas -= item.cantidad_cajas
                insumo.save()

            # Actualizar Solicitud y Receta
            solicitud.estado = 'PAGADO'
            solicitud.save()

            if receta:
                receta.estado = 'APROBADA'
                receta.revisado_por = admin_user
                receta.fecha_revision = timezone.now()
                receta.observaciones_farmaceutico = observaciones
                receta.save()

        else:
            # DENEGAR / RECHAZAR compra
            solicitud.estado = 'CANCELADO'
            solicitud.motivo_cancelacion = observaciones or 'Venta denegada tras auditoría de receta médica.'
            solicitud.save()

            if receta:
                receta.estado = 'RECHAZADA'
                receta.revisado_por = admin_user
                receta.fecha_revision = timezone.now()
                receta.observaciones_farmaceutico = observaciones
                receta.save()

        return solicitud


def cambiar_estado_solicitud(solicitud, nuevo_estado):
    """
    Cambia el estado de una solicitud con reposición atómica de stock si se cancela.
    """
    with transaction.atomic():
        if solicitud.estado in ('CANCELADO', 'ENTREGADO'):
            raise ValidationError({
                'detalle': f'No se puede cambiar el estado de una solicitud que ya está "{solicitud.get_estado_display()}".'
            })

        # Si se cancela una orden que ya había descontado stock ('PAGADO'), se repone
        if nuevo_estado == 'CANCELADO' and solicitud.estado == 'PAGADO':
            items = solicitud.items.select_related('insumo').all()
            insumo_ids = [item.insumo_id for item in items]
            insumos_bloqueados = Insumo.objects.select_for_update().in_bulk(insumo_ids)

            for item in items:
                insumo = insumos_bloqueados[item.insumo_id]
                insumo.stock_cajas += item.cantidad_cajas
                insumo.save()

        solicitud.estado = nuevo_estado
        solicitud.save()

        return solicitud

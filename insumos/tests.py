from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from usuarios.models import Tenant, Perfil
from insumos.models import CategoriaInsumo, Insumo, Carro, ItemCarro, Solicitud, ItemSolicitud, RecetaMedica


class BaseFarmaciaTestCase(TestCase):
    """Clase base con fixtures comunes para tests del sistema B2B."""

    def setUp(self):
        self.client = APIClient()

        # 1. Tenants
        self.tenant_central = Tenant.objects.create(
            nombre='CENABAST Central',
            codigo='CENABAST-01',
            rut='61.608.000-K',
            activo=True
        )
        self.tenant_privado = Tenant.objects.create(
            nombre='Red Salud Norte',
            codigo='SALUD-NORTE-02',
            rut='76.111.222-3',
            activo=True
        )

        # 2. Usuarios
        self.superadmin = User.objects.create_user(
            username='super_usr',
            password='Password123!',
            email='super@cenabast.cl'
        )
        p_sup = self.superadmin.perfil
        p_sup.rol = 'SUPERADMIN'
        p_sup.tenant = self.tenant_central
        p_sup.nombre_institucion = 'Dirección General'
        p_sup.save()

        self.admin_cenabast = User.objects.create_user(
            username='admin_cenabast',
            password='Password123!',
            email='admin@cenabast.cl'
        )
        p_adm = self.admin_cenabast.perfil
        p_adm.rol = 'ADMIN_PAGINA'
        p_adm.tenant = self.tenant_central
        p_adm.nombre_institucion = 'Farmacia CENABAST'
        p_adm.save()

        self.usuario_comprador = User.objects.create_user(
            username='hospital_regional',
            password='Password123!',
            email='compras@hospitalregional.cl'
        )
        p_usr = self.usuario_comprador.perfil
        p_usr.rol = 'USUARIO'
        p_usr.tenant = self.tenant_central
        p_usr.nombre_institucion = 'Hospital Regional'
        p_usr.save()

        # 3. Categorías
        self.cat_farmacos = CategoriaInsumo.objects.create(
            nombre='Medicamentos Generales',
            descripcion='Fármacos orales e intravenosos'
        )

        # 4. Insumos
        vencimiento = timezone.now().date() + timedelta(days=365)

        # Insumo de Venta Libre
        self.insumo_libre = Insumo.objects.create(
            nombre_comercial='Paracetamol 500mg',
            principio_activo='Paracetamol',
            categoria=self.cat_farmacos,
            tenant=self.tenant_central,
            lote='LOT-PAR-001',
            fecha_vencimiento=vencimiento,
            precio_unitario=Decimal('3000.00'),
            stock_cajas=100,
            tipo_venta='LIBRE',
            requiere_receta=False
        )

        # Insumo con Receta Médica Obligatoria
        self.insumo_receta = Insumo.objects.create(
            nombre_comercial='Amoxicilina + Ácido Clavulánico 875mg',
            principio_activo='Amoxicilina/Clavulánico',
            categoria=self.cat_farmacos,
            tenant=self.tenant_central,
            lote='LOT-AMX-002',
            fecha_vencimiento=vencimiento,
            precio_unitario=Decimal('25000.00'),
            stock_cajas=50,
            tipo_venta='RECETA_SIMPLE',
            requiere_receta=True
        )

        # Insumo Controlado (Receta Retenida)
        self.insumo_controlado = Insumo.objects.create(
            nombre_comercial='Clonazepam 2mg',
            principio_activo='Clonazepam',
            categoria=self.cat_farmacos,
            tenant=self.tenant_central,
            lote='LOT-CLO-003',
            fecha_vencimiento=vencimiento,
            precio_unitario=Decimal('18000.00'),
            stock_cajas=30,
            tipo_venta='RECETA_RETENIDA',
            requiere_receta=True,
            es_medicamento_controlado=True
        )

    def login_como(self, user):
        """Autentica al cliente con token JWT."""
        response = self.client.post('/api/token/', {
            'username': user.username,
            'password': 'Password123!'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class CarroInsumosTests(BaseFarmaciaTestCase):
    """Pruebas del carrito de compras y control de stock en tiempo real."""

    def test_agregar_item_al_carro(self):
        """Verifica que un usuario pueda agregar insumos al carrito."""
        self.login_como(self.usuario_comprador)

        response = self.client.post('/api/carro/items/', {
            'insumo': self.insumo_libre.id,
            'cantidad_cajas': 5
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cantidad_cajas'], 5)

        # Verificar consulta del carro completo
        carro_res = self.client.get('/api/carro/')
        self.assertEqual(carro_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(carro_res.data['items']), 1)
        self.assertFalse(carro_res.data['requiere_receta'])
        self.assertEqual(Decimal(carro_res.data['total_estimado']), Decimal('15000.00'))

    def test_carro_detecta_requerimiento_de_receta(self):
        """Verifica que el carrito detecte cuando un insumo requiere receta médica."""
        self.login_como(self.usuario_comprador)

        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_receta.id,
            'cantidad_cajas': 2
        }, format='json')

        carro_res = self.client.get('/api/carro/')
        self.assertEqual(carro_res.status_code, status.HTTP_200_OK)
        self.assertTrue(carro_res.data['requiere_receta'])


class SolicitudRecetaAuditTests(BaseFarmaciaTestCase):
    """
    Pruebas integrales del flujo de auditoría médica:
    - Venta bajo receta pasa a estado EN_REVISION sin descontar stock.
    - Administrador de página puede ver la receta, aprobar o denegar.
    - Al aprobar: se descuenta el stock atómicamente y se pasa a PAGADO.
    - Al denegar: la compra se cancela y el stock permanece intacto.
    """

    def test_compra_venta_libre_descuenta_stock_inmediatamente(self):
        """Venta de insumos libres de receta se aprueba y descuenta stock al confirmar."""
        self.login_como(self.usuario_comprador)

        # Agregar 10 cajas de Paracetamol
        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_libre.id,
            'cantidad_cajas': 10
        }, format='json')

        stock_inicial = self.insumo_libre.stock_cajas

        # Confirmar solicitud
        conf_res = self.client.post('/api/solicitudes/confirmar/')
        self.assertEqual(conf_res.status_code, status.HTTP_201_CREATED)
        sol_id = conf_res.data['id']

        solicitud = Solicitud.objects.get(id=sol_id)
        self.assertEqual(solicitud.estado, 'PAGADO')
        self.assertFalse(solicitud.requiere_receta)

        # Verificar que el stock se haya descontado
        self.insumo_libre.refresh_from_db()
        self.assertEqual(self.insumo_libre.stock_cajas, stock_inicial - 10)

    def test_compra_con_receta_pasa_a_en_revision_sin_descontar_stock(self):
        """Venta de medicamentos con receta entra en estado EN_REVISION y NO rebaja stock."""
        self.login_como(self.usuario_comprador)

        # Agregar Amoxicilina (requiere receta)
        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_receta.id,
            'cantidad_cajas': 5
        }, format='json')

        stock_inicial = self.insumo_receta.stock_cajas

        # Confirmar solicitud
        conf_res = self.client.post('/api/solicitudes/confirmar/')
        self.assertEqual(conf_res.status_code, status.HTTP_201_CREATED)
        sol_id = conf_res.data['id']

        solicitud = Solicitud.objects.get(id=sol_id)
        self.assertEqual(solicitud.estado, 'EN_REVISION')
        self.assertTrue(solicitud.requiere_receta)

        # El stock AÚN NO debe estar descontado
        self.insumo_receta.refresh_from_db()
        self.assertEqual(self.insumo_receta.stock_cajas, stock_inicial)

        # Se debe haber generado el registro de RecetaMedica pendiente
        self.assertTrue(solicitud.recetas.filter(estado='PENDIENTE').exists())

    def test_admin_aprueba_receta_y_descuenta_stock(self):
        """El administrador de página audita y aprueba la receta médica, descontando stock."""
        # 1. Crear solicitud con receta por el usuario
        self.login_como(self.usuario_comprador)
        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_receta.id,
            'cantidad_cajas': 4
        }, format='json')
        conf_res = self.client.post('/api/solicitudes/confirmar/')
        sol_id = conf_res.data['id']

        stock_antes = self.insumo_receta.stock_cajas

        # 2. Login como Administrador de Página / Farmacéutico
        self.login_como(self.admin_cenabast)

        # 3. Aprobar receta médica
        audit_res = self.client.post(f'/api/solicitudes/{sol_id}/revisar-receta/', {
            'decision': 'APROBAR',
            'observaciones': 'Receta verificada con médico tratante Dr. González'
        }, format='json')

        self.assertEqual(audit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(audit_res.data['estado'], 'PAGADO')

        # 4. Verificar que el stock sí fue rebajado
        self.insumo_receta.refresh_from_db()
        self.assertEqual(self.insumo_receta.stock_cajas, stock_antes - 4)

        # 5. Verificar estado de la receta
        receta = RecetaMedica.objects.get(solicitud_id=sol_id)
        self.assertEqual(receta.estado, 'APROBADA')
        self.assertEqual(receta.revisado_por, self.admin_cenabast)

    def test_admin_deniega_receta_y_no_descuenta_stock(self):
        """El administrador de página deniega la compra por receta inválida, cancelando el pedido."""
        # 1. Crear solicitud con receta
        self.login_como(self.usuario_comprador)
        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_controlado.id,
            'cantidad_cajas': 3
        }, format='json')
        conf_res = self.client.post('/api/solicitudes/confirmar/')
        sol_id = conf_res.data['id']

        stock_inicial = self.insumo_controlado.stock_cajas

        # 2. Login como Administrador
        self.login_como(self.admin_cenabast)

        # 3. Denegar compra
        audit_res = self.client.post(f'/api/solicitudes/{sol_id}/revisar-receta/', {
            'decision': 'DENEGAR',
            'observaciones': 'Receta ilegible y folio no registrado en la base del MINSAL'
        }, format='json')

        self.assertEqual(audit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(audit_res.data['estado'], 'CANCELADO')

        # 4. El stock debe permanecer intacto
        self.insumo_controlado.refresh_from_db()
        self.assertEqual(self.insumo_controlado.stock_cajas, stock_inicial)

        # 5. La receta debe estar rechazada
        receta = RecetaMedica.objects.get(solicitud_id=sol_id)
        self.assertEqual(receta.estado, 'RECHAZADA')

    def test_usuario_comun_no_puede_auditar_recetas(self):
        """Un usuario normal no tiene permisos para aprobar o denegar recetas médicas."""
        self.login_como(self.usuario_comprador)
        self.client.post('/api/carro/items/', {
            'insumo': self.insumo_receta.id,
            'cantidad_cajas': 1
        }, format='json')
        conf_res = self.client.post('/api/solicitudes/confirmar/')
        sol_id = conf_res.data['id']

        # Intentar auditar con credenciales de usuario normal
        audit_res = self.client.post(f'/api/solicitudes/{sol_id}/revisar-receta/', {
            'decision': 'APROBAR'
        }, format='json')

        # Debe retornar 403 Forbidden
        self.assertEqual(audit_res.status_code, status.HTTP_403_FORBIDDEN)

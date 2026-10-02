from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from usuarios.models import Perfil, Tenant
from insumos.models import CategoriaInsumo, Insumo, Carro, ItemCarro

class Command(BaseCommand):
    help = 'Puebla la base de datos PostgreSQL con Tenants, Roles jerárquicos y catálogo de fármacos con recetas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando poblado de la base de datos multi-tenant...'))

        # 1. Tenants (Empresas / Instituciones Clínicas)
        tenant_cenabast, _ = Tenant.objects.update_or_create(
            codigo='CENABAST-01',
            defaults={
                'nombre': 'Red Central CENABAST B2B',
                'rut': '61.608.000-K',
                'direccion': 'Av. Libertador Bernardo O Higgins 1449, Santiago',
                'telefono': '+56 2 2574 8000',
                'activo': True
            }
        )

        tenant_privado, _ = Tenant.objects.update_or_create(
            codigo='CLIN-BIC-02',
            defaults={
                'nombre': 'Red Salud Bicentenario',
                'rut': '76.890.123-5',
                'direccion': 'Av. Vitacura 5093, Las Condes',
                'telefono': '+56 2 2480 9000',
                'activo': True
            }
        )

        # 2. Superadmin Global (Acceso total a todos los tenants y administración Django)
        super_user, created = User.objects.get_or_create(
            username='superadmin',
            defaults={
                'email': 'superadmin@farmaciab2b.cl',
                'first_name': 'Vicente',
                'last_name': 'Flores (Superadmin)',
                'is_staff': True,
                'is_superuser': True
            }
        )
        super_user.set_password('SuperAdmin2026!')
        super_user.is_staff = True
        super_user.is_superuser = True
        super_user.save()

        Perfil.objects.update_or_create(
            user=super_user,
            defaults={
                'rol': 'SUPERADMIN',
                'tenant': tenant_cenabast,
                'nombre_institucion': 'Superintendencia de Salud / CENABAST',
                'telefono_contacto': '+56 9 8888 7777'
            }
        )

        # 3. Administrador de Página / Farmacéutico Auditor (Tenant CENABAST)
        admin_pag, created = User.objects.get_or_create(
            username='admin_farmacia',
            defaults={
                'email': 'farmacia@cenabast.cl',
                'first_name': 'Q.F. Carlos',
                'last_name': 'Navarro',
                'is_staff': True,
                'is_superuser': False
            }
        )
        admin_pag.set_password('AdminFarmacia2026!')
        admin_pag.is_staff = True
        admin_pag.save()

        Perfil.objects.update_or_create(
            user=admin_pag,
            defaults={
                'rol': 'ADMIN_PAGINA',
                'tenant': tenant_cenabast,
                'nombre_institucion': 'Farmacia Central CENABAST',
                'telefono_contacto': '+56 2 2574 8120'
            }
        )

        # Gestor de Bodega de respaldo (Mapeado a ADMIN_PAGINA para compatibilidad)
        gestor_user, _ = User.objects.get_or_create(
            username='gestor_bodega',
            defaults={'email': 'gestor@farmaciab2b.cl', 'first_name': 'Carlos', 'last_name': 'Gestor'}
        )
        gestor_user.set_password('Admin1234!')
        gestor_user.save()
        Perfil.objects.update_or_create(
            user=gestor_user,
            defaults={'rol': 'ADMIN_PAGINA', 'tenant': tenant_cenabast, 'nombre_institucion': 'Bodega Central CENABAST'}
        )

        # 4. Usuario Comprador Institucional (Hospital UC - Tenant CENABAST)
        institucion_user, _ = User.objects.get_or_create(
            username='hospital_uc',
            defaults={'email': 'abastecimiento@hospitaluc.cl', 'first_name': 'Dra. Patricia', 'last_name': 'López'}
        )
        institucion_user.set_password('Cliente1234!')
        institucion_user.save()
        Perfil.objects.update_or_create(
            user=institucion_user,
            defaults={'rol': 'USUARIO', 'tenant': tenant_cenabast, 'nombre_institucion': 'Hospital Clínico UC Christus'}
        )

        # Usuario 2 de respaldo
        user_davila, _ = User.objects.get_or_create(
            username='clinica_santa_maria',
            defaults={'email': 'compras@clinicasantamaria.cl', 'first_name': 'Dra. María', 'last_name': 'Compras'}
        )
        user_davila.set_password('Cliente1234!')
        user_davila.save()
        Perfil.objects.update_or_create(
            user=user_davila,
            defaults={'rol': 'USUARIO', 'tenant': tenant_cenabast, 'nombre_institucion': 'Clínica Santa María'}
        )

        # 5. Categorías
        cat_quirofano, _ = CategoriaInsumo.objects.get_or_create(
            nombre='Material Quirúrgico',
            defaults={'descripcion': 'Insumos estériles para pabellón'}
        )
        cat_farmacos, _ = CategoriaInsumo.objects.get_or_create(
            nombre='Medicamentos Generales',
            defaults={'descripcion': 'Fármacos esenciales y de venta controlada'}
        )
        cat_antibioticos, _ = CategoriaInsumo.objects.get_or_create(
            nombre='Antibióticos y Antimicrobianos',
            defaults={'descripcion': 'Fármacos con receta médica obligatoria'}
        )
        cat_controlados, _ = CategoriaInsumo.objects.get_or_create(
            nombre='Fármacos Psicotrópicos y Estupefacientes',
            defaults={'descripcion': 'Medicamentos con receta médica retenida y control'}
        )

        # 6. Insumos con Lotes, Vencimientos, Tipos de Venta y Recetas
        vencimiento_base = timezone.now().date() + timedelta(days=365)
        insumos_datos = [
            # Venta Libre
            {
                'nombre_comercial': 'Paracetamol 500mg Comprimidos',
                'principio_activo': 'Paracetamol',
                'categoria': cat_farmacos,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-PAR-2026-01',
                'fecha_vencimiento': vencimiento_base,
                'precio_unitario': Decimal('3500.00'),
                'stock_cajas': 80,
                'tipo_venta': 'LIBRE',
                'requiere_receta': False,
                'es_medicamento_controlado': False
            },
            {
                'nombre_comercial': 'Ibuprofeno 400mg Comprimidos Recubiertos',
                'principio_activo': 'Ibuprofeno',
                'categoria': cat_farmacos,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-IBU-2026-02',
                'fecha_vencimiento': vencimiento_base + timedelta(days=90),
                'precio_unitario': Decimal('4200.00'),
                'stock_cajas': 60,
                'tipo_venta': 'LIBRE',
                'requiere_receta': False,
                'es_medicamento_controlado': False
            },
            {
                'nombre_comercial': 'Guantes Quirúrgicos Estériles Talla M',
                'principio_activo': 'Látex Libre de Polvo',
                'categoria': cat_quirofano,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-GUA-2026-01',
                'fecha_vencimiento': vencimiento_base + timedelta(days=180),
                'precio_unitario': Decimal('28900.00'),
                'stock_cajas': 120,
                'tipo_venta': 'LIBRE',
                'requiere_receta': False,
                'es_medicamento_controlado': False
            },
            # Requiere Receta Simple
            {
                'nombre_comercial': 'Amoxicilina + Ácido Clavulánico 875/125mg',
                'principio_activo': 'Amoxicilina / Clavulanato',
                'categoria': cat_antibioticos,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-AMX-2026-RX',
                'fecha_vencimiento': vencimiento_base + timedelta(days=240),
                'precio_unitario': Decimal('24500.00'),
                'stock_cajas': 50,
                'tipo_venta': 'RECETA_SIMPLE',
                'requiere_receta': True,
                'es_medicamento_controlado': False
            },
            {
                'nombre_comercial': 'Ciprofloxacino 500mg Comprimidos',
                'principio_activo': 'Ciprofloxacino Clorhidrato',
                'categoria': cat_antibioticos,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-CIP-2026-RX',
                'fecha_vencimiento': vencimiento_base + timedelta(days=300),
                'precio_unitario': Decimal('19800.00'),
                'stock_cajas': 35,
                'tipo_venta': 'RECETA_SIMPLE',
                'requiere_receta': True,
                'es_medicamento_controlado': False
            },
            # Requiere Receta Retenida / Controlado
            {
                'nombre_comercial': 'Clonazepam 2mg Comprimidos',
                'principio_activo': 'Clonazepam (Benzodiacepina)',
                'categoria': cat_controlados,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-CLO-2026-RET',
                'fecha_vencimiento': vencimiento_base + timedelta(days=400),
                'precio_unitario': Decimal('16500.00'),
                'stock_cajas': 25,
                'tipo_venta': 'RECETA_RETENIDA',
                'requiere_receta': True,
                'es_medicamento_controlado': True
            },
            {
                'nombre_comercial': 'Morfina Clorhidrato 10mg/ml Ampollas',
                'principio_activo': 'Morfina Clorhidrato',
                'categoria': cat_controlados,
                'tenant': tenant_cenabast,
                'lote': 'LOTE-MOR-2026-RET',
                'fecha_vencimiento': vencimiento_base + timedelta(days=500),
                'precio_unitario': Decimal('58900.00'),
                'stock_cajas': 20,
                'tipo_venta': 'RECETA_RETENIDA',
                'requiere_receta': True,
                'es_medicamento_controlado': True
            }
        ]

        insumos_guardados = []
        for item in insumos_datos:
            insumo, _ = Insumo.objects.update_or_create(
                lote=item['lote'],
                defaults=item
            )
            insumos_guardados.append(insumo)

        # 7. Carro activo con items para la Institución
        carro, _ = Carro.objects.get_or_create(user=institucion_user, estado='ACTIVO')
        carro.items.all().delete()  # Limpiar estado previo
        ItemCarro.objects.create(
            carro=carro,
            insumo=insumos_guardados[0], # Paracetamol (Libre)
            cantidad_cajas=4
        )
        ItemCarro.objects.create(
            carro=carro,
            insumo=insumos_guardados[3], # Amoxicilina (Requiere Receta)
            cantidad_cajas=2
        )

        self.stdout.write(self.style.SUCCESS('Base de datos multi-tenant poblada exitosamente.'))
        self.stdout.write('========================================================================')
        self.stdout.write('CREDENCIALES DISPONIBLES:')
        self.stdout.write('1. SUPERADMIN (Control Total / Multi-Tenant):')
        self.stdout.write('   Usuario:    superadmin')
        self.stdout.write('   Contraseña: SuperAdmin2026!')
        self.stdout.write('------------------------------------------------------------------------')
        self.stdout.write('2. ADMINISTRADOR DE PÁGINA (Auditor Farmacéutico - Aprueba/Deniega recetas):')
        self.stdout.write('   Usuario:    admin_farmacia')
        self.stdout.write('   Contraseña: AdminFarmacia2026!')
        self.stdout.write('------------------------------------------------------------------------')
        self.stdout.write('3. USUARIO / INSTITUCIÓN DE SALUD (Compra insumos y sube recetas):')
        self.stdout.write('   Usuario:    hospital_uc')
        self.stdout.write('   Contraseña: Cliente1234!')
        self.stdout.write('========================================================================')
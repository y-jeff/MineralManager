from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin,BaseUserManager


# Tabla: AREA
class Area(models.Model):
    nombre_area = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre_area

# Tabla: CATEGORIA
class Categoria(models.Model):
    nombre_categoria_item = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_categoria_item

# Tabla: ARTICULOS
class Articulo(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT)
    nombre_articulo = models.CharField(max_length=50)
    descripcion_articulo = models.CharField(max_length=2000)

    def __str__(self):
        return self.nombre_articulo

# Tabla: BODEGA
class Bodega(models.Model):
    nombre_bodega = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_bodega

# Tabla: INVENTARIO_ARTICULOS_BODEGA
class InventarioArticuloBodega(models.Model):
    articulo = models.ForeignKey(Articulo, on_delete=models.RESTRICT)
    bodega = models.ForeignKey(Bodega, on_delete=models.RESTRICT)
    cantidad_articulos = models.IntegerField()
    en_bodega = models.BooleanField()

    def __str__(self):
        return f"{self.articulo} en {self.bodega}"

# Tabla: CAPACITACION
class Capacitacion(models.Model):
    nombre_capacitacion = models.CharField(max_length=256)

    def __str__(self):
        return self.nombre_capacitacion

# Tabla: CARGO_TRABAJADOR
class CargoTrabajador(models.Model):
    nombre_cargo = models.CharField(max_length=256)

    def __str__(self):
        return self.nombre_cargo

# Tabla: TRABAJADORES
class Trabajador(models.Model):
    nombre_trabajador = models.CharField(max_length=256)
    rut = models.CharField(max_length=9, primary_key=True)
    horario = models.ForeignKey('HorarioTrabajo', on_delete=models.RESTRICT)
    area = models.ForeignKey(Area, on_delete=models.RESTRICT)
    cargo = models.ForeignKey(CargoTrabajador, on_delete=models.RESTRICT)
    horas_esperadas_totales = models.IntegerField()

    def __str__(self):
        return self.nombre_trabajador

# Tabla: HORARIO_TRABAJO
class HorarioTrabajo(models.Model):
    jornada_trabajador = models.ForeignKey('JornadaTrabajador', on_delete=models.RESTRICT)
    turno_trabajador = models.ForeignKey('TurnoTrabajador', on_delete=models.RESTRICT)

    def __str__(self):
        return f"Jornada {self.jornada_trabajador} - Turno {self.turno_trabajador}"

# Tabla: JORNADA_TRABAJADOR
class JornadaTrabajador(models.Model):
    tipo_jornada = models.CharField(max_length=10)

    def __str__(self):
        return self.tipo_jornada

# Tabla: TURNO_TRABAJADOR
class TurnoTrabajador(models.Model):
    tipo_turno = models.CharField(max_length=256)

    def __str__(self):
        return self.tipo_turno

# Tabla: REGISTRO_ASISTENCIA_TRABAJADOR
class RegistroAsistenciaTrabajador(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.RESTRICT)
    asistencia = models.ForeignKey('Asistencia', on_delete=models.RESTRICT)

    def __str__(self):
        return f"Asistencia de {self.trabajador} - {self.asistencia.fecha_trabajada}"

# Tabla: ASISTENCIA
class Asistencia(models.Model):
    fecha_trabajada = models.DateField()
    hora_trabajada = models.IntegerField()

    def __str__(self):
        return f"{self.fecha_trabajada} - {self.hora_trabajada} horas"

# Tabla: ASIGNACION_ARTICULO
class AsignacionArticulo(models.Model):
    panol = models.ForeignKey('Panol', on_delete=models.RESTRICT)
    inventario = models.ForeignKey(InventarioArticuloBodega, on_delete=models.RESTRICT)
    cantidad_asignada_stock = models.IntegerField()

    def __str__(self):
        return f"Asignación en {self.panol} - {self.inventario.articulo}"

# Tabla: CAPACITACION_TRABAJADOR
class CapacitacionTrabajador(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.RESTRICT)
    capacitacion = models.ForeignKey(Capacitacion, on_delete=models.RESTRICT)
    fecha_de_capacitacion = models.DateField()

    def __str__(self):
        return f"{self.capacitacion} - {self.trabajador}"

# Tabla: JORNADA_EQUIPO
class JornadaEquipo(models.Model):
    tipo_jornada_equipo = models.CharField(max_length=256)

    def __str__(self):
        return self.tipo_jornada_equipo

# Tabla: PANOL
class Panol(models.Model):
    nombre_panol = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_panol

# Tabla: RETIRO_ARTICULOS
class RetiroArticulo(models.Model):
    panol = models.ForeignKey(Panol, on_delete=models.RESTRICT)
    trabajador = models.ForeignKey(Trabajador, on_delete=models.RESTRICT)
    cantidad_retirada = models.IntegerField()
    fecha_retiro_articulo = models.DateField()
    motivo_retiro_articulo = models.CharField(max_length=2000)

    def __str__(self):
        return f"Retiro por {self.trabajador} - {self.cantidad_retirada}"

# Tabla: REGISTRO_ENTREGA
class RegistroEntrega(models.Model):
    inventario = models.ForeignKey(InventarioArticuloBodega, on_delete=models.RESTRICT)
    panol = models.ForeignKey(Panol, on_delete=models.RESTRICT)
    fecha_registro_entrega = models.DateTimeField()
    enviado_panol = models.BooleanField()
    regresado_bodega = models.BooleanField()
    fecha_registro_despacho = models.DateTimeField()

    def __str__(self):
        return f"Entrega en {self.panol} - {self.inventario.articulo}"

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico.")
        if not username:
            raise ValueError("El usuario debe tener un nombre de usuario.")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        user = self.create_user(
            email=email,
            username=username,
            password=password,
        )
        user.is_admin = True
        user.is_staff = True  # Asegúrate de que is_staff esté en True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=60, unique=True)
    is_approved = models.BooleanField(default=False)
    email_confirmed = models.BooleanField(default=False)  # Para la confirmación de correo (opcional)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def save(self, *args, **kwargs):
        # Verifica si el usuario estaba pendiente de aprobación y ahora está aprobado
        if self.pk:  # Si el usuario ya existe (no es una creación nueva)
            original_user = CustomUser.objects.get(pk=self.pk)
            if not original_user.is_approved and self.is_approved:
                # Enviar correo al usuario notificando que ha sido aprobado
                send_mail(
                    'Cuenta aprobada',
                    f'Hola {self.username}, tu cuenta ha sido aprobada. Ya puedes iniciar sesión.',
                    settings.DEFAULT_FROM_EMAIL,  # De esta dirección se envía el correo
                    [self.email],  # Dirección del usuario aprobado
                )

        # Llama al método `save` original para que el usuario se guarde normalmente
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    @property
    def is_staff(self):
        return self.is_admin
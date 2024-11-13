from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Custom user manager
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
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=60, unique=True)
    email_confirmed = models.BooleanField(default=False)  # Agregar el campo aquí
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username
# Área
class Area(models.Model):
    nombre_area = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre_area

# Cargo
class Cargo(models.Model):
    nombre_cargo = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.nombre_cargo

# Jornada
class Jornada(models.Model):
    tipo_jornada = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.tipo_jornada

# Turno
class Turno(models.Model):
    tipo_turno = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')])

    def __str__(self):
        return f"Turno {self.tipo_turno}"

# Horario (Ciclo de Trabajo)
class Horario(models.Model):
    ciclo = models.CharField(max_length=10)
    def __str__(self):
        return f"Ciclo {self.ciclo}"

# Trabajador
class Trabajador(models.Model):
    rut = models.CharField(max_length=9, primary_key=True)
    nombre_trabajador = models.CharField(max_length=256)
    area = models.ForeignKey(Area, on_delete=models.RESTRICT)
    cargo = models.ForeignKey(Cargo, on_delete=models.RESTRICT)
    jornada = models.ForeignKey(Jornada, on_delete=models.RESTRICT)
    turno = models.ForeignKey(Turno, on_delete=models.RESTRICT)
    horario = models.ForeignKey(Horario, on_delete=models.RESTRICT)
    horas_esperadas_totales = models.IntegerField(default=40)

    def __str__(self):
        return self.nombre_trabajador

# Capacitacion
class Capacitacion(models.Model):
    nombre_capacitacion = models.CharField(max_length=256)
    es_renovable = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_capacitacion

# CapacitacionTrabajador
class CapacitacionTrabajador(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.RESTRICT)
    capacitacion = models.ForeignKey(Capacitacion, on_delete=models.RESTRICT)
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)  # Opcional

    def __str__(self):
        return f"{self.capacitacion} - {self.trabajador}"

# Panol
class Panol(models.Model):
    nombre_panol = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre_panol

# Bodega
class Bodega(models.Model):
    nombre_bodega = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre_bodega
class Producto(models.Model):
    disponibilidad_choices = [
        ('si', 'Sí'),
        ('no', 'No'),
    ]
    disponibilidad = models.CharField(
        max_length=2,
        choices=disponibilidad_choices,
        default='no',
    )

    def __str__(self):
        return f'{self.disponibilidad}'
# Articulo en Panol
class ArticuloPanol(models.Model):
    panol = models.ForeignKey(Panol, on_delete=models.RESTRICT)
    nombre_articulo = models.CharField(max_length=50)
    descripcion_articulo = models.CharField(max_length=2000)
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.nombre_articulo} en {self.panol}"

# Articulo en Bodega
class ArticuloBodega(models.Model):
    bodega = models.ForeignKey(Bodega, on_delete=models.RESTRICT)
    nombre_articulo = models.CharField(max_length=50)
    descripcion_articulo = models.CharField(max_length=2000)
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.nombre_articulo} en {self.bodega}"

# Maquinaria
class Maquinaria(models.Model):
    codigo_maquinaria = models.CharField(max_length=100, unique=True)
    nombre_maquinaria = models.CharField(max_length=100)
    fecha_adquisicion = models.DateField()
    estado = models.CharField(max_length=50)
    area = models.ForeignKey(Area, on_delete=models.RESTRICT)

    def __str__(self):
        return f"{self.nombre_maquinaria} ({self.codigo_maquinaria})"

# Mantenimiento Maquinaria
class MantenimientoMaquinaria(models.Model):
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_mantenimiento = models.DateField()
    descripcion = models.TextField()
    realizado_por = models.CharField(max_length=100)

    def __str__(self):
        return f"Mantenimiento de {self.maquinaria} el {self.fecha_mantenimiento}"

# Movimiento de Articulo
class MovimientoArticulo(models.Model):
    articulo = models.ForeignKey(ArticuloBodega, on_delete=models.RESTRICT)
    origen = models.ForeignKey(Bodega, on_delete=models.RESTRICT, related_name='origen_bodega')
    destino = models.ForeignKey(Panol, on_delete=models.RESTRICT, related_name='destino_panol')
    cantidad = models.IntegerField()
    fecha_movimiento = models.DateField(default=timezone.now)
    motivo = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Movimiento de {self.cantidad} de {self.articulo} desde {self.origen} a {self.destino}"

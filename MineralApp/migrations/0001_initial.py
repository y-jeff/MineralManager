# Generated by Django 4.2.4 on 2024-11-07 03:11

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_area', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='ArticuloBodega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_articulo', models.CharField(max_length=50)),
                ('descripcion_articulo', models.CharField(max_length=2000)),
                ('cantidad', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Bodega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_bodega', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Capacitacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_capacitacion', models.CharField(max_length=256)),
                ('es_renovable', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Cargo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_cargo', models.CharField(max_length=256, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Horario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ciclo', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Jornada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_jornada', models.CharField(max_length=10, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Panol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_panol', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Turno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_turno', models.CharField(choices=[('A', 'A'), ('B', 'B')], max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(max_length=50, unique=True)),
                ('email', models.EmailField(max_length=60, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_admin', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Trabajador',
            fields=[
                ('rut', models.CharField(max_length=9, primary_key=True, serialize=False)),
                ('nombre_trabajador', models.CharField(max_length=256)),
                ('horas_esperadas_totales', models.IntegerField(default=40)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.area')),
                ('cargo', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.cargo')),
                ('horario', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.horario')),
                ('jornada', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.jornada')),
                ('turno', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.turno')),
            ],
        ),
        migrations.CreateModel(
            name='MovimientoArticulo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.IntegerField()),
                ('fecha_movimiento', models.DateField(default=django.utils.timezone.now)),
                ('motivo', models.CharField(blank=True, max_length=200, null=True)),
                ('articulo', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.articulobodega')),
                ('destino', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='destino_panol', to='MineralApp.panol')),
                ('origen', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='origen_bodega', to='MineralApp.bodega')),
            ],
        ),
        migrations.CreateModel(
            name='Maquinaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_maquinaria', models.CharField(max_length=100, unique=True)),
                ('nombre_maquinaria', models.CharField(max_length=100)),
                ('fecha_adquisicion', models.DateField()),
                ('estado', models.CharField(max_length=50)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.area')),
            ],
        ),
        migrations.CreateModel(
            name='MantenimientoMaquinaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_mantenimiento', models.DateField()),
                ('descripcion', models.TextField()),
                ('realizado_por', models.CharField(max_length=100)),
                ('maquinaria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MineralApp.maquinaria')),
            ],
        ),
        migrations.CreateModel(
            name='CapacitacionTrabajador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(default=django.utils.timezone.now)),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('capacitacion', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.capacitacion')),
                ('trabajador', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.trabajador')),
            ],
        ),
        migrations.CreateModel(
            name='ArticuloPanol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_articulo', models.CharField(max_length=50)),
                ('descripcion_articulo', models.CharField(max_length=2000)),
                ('cantidad', models.IntegerField()),
                ('panol', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.panol')),
            ],
        ),
        migrations.AddField(
            model_name='articulobodega',
            name='bodega',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.bodega'),
        ),
    ]

# Generated by Django 4.2.4 on 2024-10-24 06:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MineralApp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MantenimientoMaquinaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_mantenimiento', models.DateField()),
                ('descripcion', models.TextField()),
                ('realizado_por', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Maquinaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_maquinaria', models.CharField(max_length=100)),
                ('fecha_adquisicion', models.DateField()),
                ('estado', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='MovimientoInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_movimiento', models.DateField()),
                ('cantidad', models.IntegerField()),
                ('motivo', models.CharField(blank=True, max_length=200, null=True)),
                ('articulo', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='MineralApp.inventarioarticulobodega')),
                ('destino', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='movimiento_destino', to='MineralApp.bodega')),
                ('origen', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='movimiento_origen', to='MineralApp.bodega')),
            ],
        ),
        migrations.CreateModel(
            name='RegistroCambios',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tabla_afectada', models.CharField(max_length=100)),
                ('campo_modificado', models.CharField(max_length=100)),
                ('valor_anterior', models.CharField(blank=True, max_length=255, null=True)),
                ('valor_nuevo', models.CharField(max_length=255)),
                ('fecha_modificacion', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RetiroMaquinaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_retiro', models.DateField()),
                ('motivo', models.CharField(max_length=500)),
                ('maquinaria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MineralApp.maquinaria')),
            ],
        ),
        migrations.RemoveField(
            model_name='asignacionarticulo',
            name='inventario',
        ),
        migrations.RemoveField(
            model_name='asignacionarticulo',
            name='panol',
        ),
        migrations.DeleteModel(
            name='JornadaEquipo',
        ),
        migrations.AddField(
            model_name='capacitacion',
            name='es_renovable',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='capacitacion',
            name='fecha_fin',
            field=models.DateField(default='2024-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='capacitacion',
            name='fecha_inicio',
            field=models.DateField(default='2024-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='capacitacion',
            name='fecha_renovacion',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='capacitaciontrabajador',
            name='renovacion_fecha',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='registroasistenciatrabajador',
            name='observaciones',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.DeleteModel(
            name='AsignacionArticulo',
        ),
        migrations.AddField(
            model_name='mantenimientomaquinaria',
            name='maquinaria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MineralApp.maquinaria'),
        ),
    ]

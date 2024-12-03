# Generated by Django 4.2.4 on 2024-12-03 05:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MineralApp', '0013_remove_maquinaria_horas_esperadas_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='maquinaria',
            name='area',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='MineralApp.area'),
        ),
        migrations.AlterField(
            model_name='maquinaria',
            name='codigo_maquinaria',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='maquinaria',
            name='estado',
            field=models.CharField(choices=[('activo', 'Activo'), ('mantenimiento', 'En Mantenimiento'), ('inactivo', 'Inactivo')], default='activo', max_length=20),
        ),
    ]

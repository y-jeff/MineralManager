# Generated by Django 4.2.4 on 2024-11-27 04:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MineralApp', '0010_alter_trabajador_rut'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trabajador',
            name='horas_esperadas_totales',
        ),
        migrations.AlterField(
            model_name='registrohoras',
            name='horas_esperadas',
            field=models.IntegerField(default=40),
        ),
    ]

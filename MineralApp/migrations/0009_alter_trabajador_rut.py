# Generated by Django 4.2.4 on 2024-11-27 04:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MineralApp', '0008_trabajador_activo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trabajador',
            name='rut',
            field=models.CharField(max_length=256, primary_key=True, serialize=False),
        ),
    ]
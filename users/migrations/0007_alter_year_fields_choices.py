from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_faculty_fa_subject_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='year',
            field=models.CharField(blank=True, choices=[('FY', 'First Year'), ('SY', 'Second Year'), ('TY', 'Third Year'), ('Final', 'Final Year')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='faculty_fa_year',
            field=models.CharField(blank=True, choices=[('FY', 'First Year'), ('SY', 'Second Year'), ('TY', 'Third Year'), ('Final', 'Final Year')], max_length=10, null=True, verbose_name='Faculty (FA) Year'),
        ),
        migrations.AlterField(
            model_name='user',
            name='subject_holder_year',
            field=models.CharField(blank=True, choices=[('FY', 'First Year'), ('SY', 'Second Year'), ('TY', 'Third Year'), ('Final', 'Final Year')], max_length=10, null=True, verbose_name='Subject Holder Year'),
        ),
    ]

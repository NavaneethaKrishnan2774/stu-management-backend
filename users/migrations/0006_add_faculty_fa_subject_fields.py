from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_add_user_admin_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_faculty_fa',
            field=models.BooleanField(default=False, help_text='Mark this user as Faculty (FA) advisor'),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_fa_department',
            field=models.CharField(blank=True, choices=[('CSE', 'CSE'), ('ECE', 'ECE'), ('MECH', 'MECH'), ('CIVIL', 'CIVIL'), ('EEE', 'EEE'), ('MECHANICAL', 'MECHANICAL')], max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_fa_from_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_fa_section',
            field=models.CharField(blank=True, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_fa_to_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_fa_year',
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_subject_holder',
            field=models.BooleanField(default=False, help_text='Mark this user as Faculty (Subject Holder)'),
        ),
        migrations.AddField(
            model_name='user',
            name='subject_holder_class_count',
            field=models.PositiveIntegerField(blank=True, null=True, help_text='Number of classes handled as a subject holder'),
        ),
        migrations.AddField(
            model_name='user',
            name='subject_holder_department',
            field=models.CharField(blank=True, choices=[('CSE', 'CSE'), ('ECE', 'ECE'), ('MECH', 'MECH'), ('CIVIL', 'CIVIL'), ('EEE', 'EEE'), ('MECHANICAL', 'MECHANICAL')], max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='subject_holder_section',
            field=models.CharField(blank=True, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='subject_holder_year',
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
    ]

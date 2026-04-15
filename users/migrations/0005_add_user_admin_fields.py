from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_user_title_alter_user_department_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='salutation',
            field=models.CharField(blank=True, choices=[('mr', 'Mr'), ('ms', 'Ms'), ('mrs', 'Mrs')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='faculty_advisor_class',
            field=models.CharField(blank=True, help_text='Faculty advisor class or section managed by this user', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='designation',
            field=models.CharField(blank=True, choices=[('assistant_professor', 'Assistant Professor'), ('associate_professor', 'Associate Professor'), ('professor', 'Professor'), ('hod', 'HOD'), ('other', 'Other')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='department',
            field=models.CharField(blank=True, choices=[('CSE', 'CSE'), ('ECE', 'ECE'), ('MECH', 'MECH'), ('CIVIL', 'CIVIL'), ('EEE', 'EEE'), ('MECHANICAL', 'MECHANICAL')], max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='section',
            field=models.CharField(blank=True, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1, null=True),
        ),
    ]

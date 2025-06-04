from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('username', models.CharField(max_length=50, unique=True, verbose_name='用户名')),
                ('nickname', models.CharField(blank=True, max_length=50, verbose_name='昵称')),
                ('email', models.EmailField(blank=True, max_length=100, verbose_name='邮箱')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('is_staff', models.BooleanField(default=False, verbose_name='是否为员工')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='是否为超级用户')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='注册时间')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')),
                ('department', models.CharField(blank=True, max_length=50, verbose_name='部门')),
                ('position', models.CharField(blank=True, max_length=50, verbose_name='职位')),
            ],
            options={
                'verbose_name': '用户',
                'verbose_name_plural': '用户',
                'db_table': 'sys_users',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='角色名称')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='角色编码')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='角色描述')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '角色',
                'verbose_name_plural': '角色',
                'db_table': 'sys_roles',
            },
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='system.role', verbose_name='角色')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='system.user', verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户角色关联',
                'verbose_name_plural': '用户角色关联',
                'db_table': 'sys_user_roles',
                'unique_together': {('user', 'role')},
            },
        ),
    ]
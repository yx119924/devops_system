from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('用户名不能为空')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField('用户名', max_length=50, unique=True)
    nickname = models.CharField('昵称', max_length=50, blank=True)
    email = models.EmailField('邮箱', max_length=100, blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    is_staff = models.BooleanField('是否为员工', default=False)
    date_joined = models.DateTimeField('注册时间', default=timezone.now)
    last_login = models.DateTimeField('最后登录时间', null=True, blank=True)
    department = models.CharField('部门', max_length=50, blank=True)
    position = models.CharField('职位', max_length=50, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        db_table = 'sys_users'

    def __str__(self):
        return self.username


class Role(models.Model):
    name = models.CharField('角色名称', max_length=50)
    code = models.CharField('角色编码', max_length=50, unique=True)
    description = models.CharField('角色描述', max_length=200, blank=True)
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = verbose_name
        db_table = 'sys_roles'

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色')
    created_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户角色关联'
        verbose_name_plural = verbose_name
        db_table = 'sys_user_roles'
        unique_together = ['user', 'role']

    def __str__(self):
        return f'{self.user.username} - {self.role.name}'

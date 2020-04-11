from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """自定义用户模型类"""
    mobile = models.CharField(max_length=11,unique=True,verbose_name="手机号")
    #如果模型已经迁移建表，并且表中已经有数据，那么后面追加的字段必须给默认值或允许为空，不然迁移会报错
    email_active = models.BooleanField(default=False, verbose_name="邮箱验证状态")
    class Meta:
        db_table = "tb_users"
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


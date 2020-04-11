# # celery启动文件
# from celery import Celery
#
#
# # 为celery使用django配置文件进行设置
# import os
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings.dev')
#
# # 创建celery实例
# celery_app = Celery('meiduo')
# # 加载celery配置
# celery_app.config_from_object('celery_tasks.config')
# # 自动注册celery任务
# celery_app.autodiscover_tasks(['celery_tasks.sms'])

# celery 启动文件
from celery import Celery
import os

# 让celery在启动时提前加载django配置文件
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 创建celery客户端对象
celery_app = Celery('meiduo')

# 加载celery配置,指定celery生产的任务存放到那里
celery_app.config_from_object('celery_tasks.config')

# 注册celery可以生产什么任务
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])
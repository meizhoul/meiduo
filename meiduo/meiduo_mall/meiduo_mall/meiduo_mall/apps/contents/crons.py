import time

from django.shortcuts import render
from django.conf import settings

import os

from .models import ContentCategory
from .utils import get_categories

def generate_static_index_html():
    """主页静态化"""
    print('%s: generate_static_index_html' % time.ctime())

    contents = {} #用来包装所有广告的大字典

    #查询出所有的广告类别数据
    content_cat_qs = ContentCategory.objects.all()
    for content_cat in content_cat_qs:
        contents[content_cat.key] = content_cat.content_set.filter(status=True).order_by("sequence")

    #准备模型渲染数据
    context = {
        'categories': get_categories(),
        'contents': contents
    }
    response = render(None, 'index.html', context)
    htm_str = response.content.decode()
    file_path = os.path.join(settings.STATICFILES_DIRS[0],'index.html') #拼接路径
    f = open(file_path, 'w', encoding='utf-8')
    f.write(htm_str)
    f.close()



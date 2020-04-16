from django.shortcuts import render

from django.shortcuts import render, redirect
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import authenticate
from django.contrib.auth import login, logout
from django.views import View
from django import http
from django.contrib.auth import mixins
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin


from .models import User

import re
import json

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequired
from celery_tasks.email.tasks import send_verify_email
from .utils import generate_verify_email_url,check_verify_email


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        """
        实现用户注册
        :param request: 请求对象
        :return: 注册结果
        """
        # 1.接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 2.校验参数
        # 2.1 判断参数是否齐全
        if not all([username, password, password2, mobile, sms_code_client, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 2.2 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 2.3 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 2.4 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 2.5 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')


        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 3. 保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        # 4. 登入用户，实现状态保持
        login(request, user)

        # 5. 响应注册结果
        response = redirect(reverse('contents:index'))

        return response


class UsernameCountView(View):
    """判断用户名是否重复"""
    def get(self, request, username):

        # 查询user表, 查询username的数量
        count = User.objects.filter(username=username).count()

        # 包装响应数据
        data = {
            'count': count,
            'code': RETCODE.OK,  # 自定义状态码
            'errmsg': 'OK'
        }
        # 响应
        return http.JsonResponse(data)


class MobileCountView(View):
    """判断手机号是否重复"""
    def get(self, request, mobile):

        # 查询user表, 查询mobile的数量
        count = User.objects.filter(mobile=mobile).count()

        # 包装响应数据
        data = {
            'count': count,
            'code': RETCODE.OK,  # 自定义状态码
            'errmsg': 'OK'
        }
        # 响应
        return http.JsonResponse(data)

class LoginView(View):
    """用户登陆 """

    def get(self,request):
        """www.baidu.com"
        提供登陆界面
        :param request: 请求对象
        :return: 登陆界面
        """
        return render(request,"login.html")

    def post(self,request):
        """
        登陆逻辑
        :param request:
        :return:
        """
        #接受请求参数
        username = request.POST.get("username")
        password = request.POST.get("password")
        remembered = request.POST.get("remembered")
        #校验参数
        #2.1判断参数是否齐全
        if not all([username,password]):
            return http.HttpResponseForbidden("缺少必传参数")
        #2.2判断用户名是否5-20个字符
        if not re.match(r'^[a-zA-z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden("请输入正确的用户名或手机号")
        #2.3判断秘密是否8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return http.HttpResponseForbidden("密码最少8位，最长20位")

        # 认证成功
        """authentica封装好了一系列的用户验证 查询数据库，所以直接调用就可以"""
        user = authenticate(username=username,password=password)
        if user is None:
            return render(request,"login.html",{"accouny_errmsg":"用户名或密码错误"})

        # 保持登陆状态
        login(request,user)

        #设置状态保持的周期
        if remembered != 'on':
            #没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        #获取用户界面来源
        next = request.GET.get("next")
        response = redirect(next or '/')
        # response = redirect((reverse('contents:index')))#创建重定向响应对象
        response.set_cookie('username', user.username, max_age=remembered and settings.SESSION_COOKIE_AGE)
        return response


class LogoutView(View):
    """退出登录"""

    def get(self,request):
        """退出登陆逻辑"""
        #清除session
        logout(request)
        #退出登陆重定向到登陆页
        response = redirect('/login/')#重定向到login
        # response = redirect(reverse('users:login'))#报错
        # response = redirect(reverse('contents:index'))#不报错重定向到index首页
        # response = redirect('/')#不报错重定向到index首页
        #推出登陆时清楚cookie中的username
        response.delete_cookie("username")
        return response

class UserInfoView(mixins.LoginRequiredMixin,View):
    """用户中心"""

    def get(self,request):
        '''提供邮箱验证信息'''

        return render(request, "user_center_info.html")


class EmailView(LoginRequired):
    """设置用户邮箱"""

    def put(self,request):
        #接受数据
        json_dict = json.loads(request.body.decode())
        email = json_dict.get("email")
        #校验
        if email is None:
            return http.HttpResponseForbidden("缺少必传参数")
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden("邮箱格式不正确")
        #业务处理
        user = request.user
        User.objects.filter(id=user.id, email="").update(email=email)
        # #生成激活url
        # verify_url = generate_verify_email_url(user)
        # #异步发送邮件
        # send_verify_email.delay(email, verify_url)
        # #响应
        # return http.JsonResponse({"code":RETCODE.OK,"errmsg":"OK"})
        verify_url = generate_verify_email_url(user)
        # celery异步发邮件
        send_verify_email.delay(email, verify_url)
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class VerifyEmaiView(View):
    """激活用户邮箱"""
    def get(self,request):
        #获取查询参数中的token
        token = request.GET.get("token")
        #校验
        if token is None:
            return http.HttpResponseForbidden("缺少token")
        #解密
        user = check_verify_email(token)
        if user is None:
            return http.HttpResponseForbidden("token无效")
        #修改字段
        user.email_active = True
        user.save()
        #响应
        return redirect("/info/")


class AddressViwe(LoginRequired, View):
    """用户收货地址"""

    def get(self,request):
        return render(request, "user_center_site.html")
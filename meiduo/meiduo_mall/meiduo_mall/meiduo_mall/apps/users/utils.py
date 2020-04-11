from django.contrib.auth.backends import ModelBackend
from django.conf import settings
import re

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from .models import User


def get_user_by_account(account):
    """
    通过帐号获取用户模型对象
    :param account: mobile/username
    :return:  uers or None
    """
    try:
        if re.match(r'1[3-9]\d{9}',account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
        return user
    except User.DoesNotExist:
        return None


# sernameMobileAuthBackend
class UsernameMobileAuthBackend(ModelBackend):
    """自定义认证后端类实现多账号登陆"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        #根据用户名或手机号查询user
        user = get_user_by_account(username)
        #校验用户密码
        if user and user.check_password(password) and user.is_active:
            #返回user 或none
            return user


def generate_verify_email_url(user):
    """生成用户激活邮箱"""
    serializer = Serializer(settings.SECRET_KEY, 3600 * 24)
    data = {"user_id":user.id, "email":user.email}
    token =serializer.dumps(data).decode()

    # 拼接激活url   'http://www.meiduo.site:8000/emails/verification/' + '?token=' + 'xxxxdfsajadsfljdlskaj'
    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token
    return verify_url


def check_verify_email(token):
    """传入token解密后查询用户"""
    serializer =Serializer(settings.SECRET_KEY, 3600*24)
    try:
        data = serializer.loads(token)
        user_id = data.get("user_id")
        email = data.get("email")
        try:
            user = User.objects.get(id=user_id,email=email)
            return user
        except User.DoesNotExist:
            return None
    except BadData:
        return None
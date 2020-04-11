# 发送短信的异步任务
from celery_tasks.sms.yuntongxun.ccp_sms import CCP
from celery_tasks.sms import constants
from celery_tasks.main import celery_app
import logging

# 日志记录器
logger = logging.getLogger('django')


# bind：保证task对象会作为第一个参数自动传入
# name：异步任务别名
# retry_backoff：异常自动重试的时间间隔 第n次(retry_backoff×2^(n-1))s
# max_retries：异常自动重试次数的上限
@celery_app.task(name='ccp_send_sms_code')
def ccp_send_sms_code(mobile, sms_code):
    """
    发送短信异步任务
    :param mobile: 手机号
    :param sms_code: 短信验证码
    :return: 成功0 或 失败-1
    """

    send_ret = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60],
                                       constants.SEND_SMS_TEMPLATE_ID)


    return send_ret


# from celery_tasks.sms.yuntongxun.ccp_sms import CCP
# from celery_tasks.sms import constants
# # from verifications import constants
# from celery_tasks.main import celery_app
#
# # name=自定义任务名字
# @celery_app.task(name='send_sms_code')
# def send_sms_code(mobile, sms_code):
#     # CCP().send_template_sms('接收短信手机号', ['短信验证码', '提示用户短信验证码多久过期单位分钟'], '模板id')
#     CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_EXPIRE // 60], 1)
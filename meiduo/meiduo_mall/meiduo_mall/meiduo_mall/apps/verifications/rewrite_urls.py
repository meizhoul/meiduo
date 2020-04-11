class MobileConverter:
    # 匹配手机号码的正则
    regex = '1[3-9]\d{9}'

    def to_python(self, value):
        # 将匹配结果传递到视图内部时使用
         return int(value)

    def to_url(self, value):
        # 将匹配结果用于反向解析传值时使用
        return str(value)
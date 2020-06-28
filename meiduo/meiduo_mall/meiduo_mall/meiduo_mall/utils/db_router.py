class MasterSlaveDBRouter(object):

    """数据库读写分离路由"""


    def db_for_read(self, model, **hints):
        """mysql读写分离中的从机（读）负责查询操作"""
        return "slave"


    def db_for_write(self, model, **hints):
        '''myslq读写分离中的主机（写）负责增删改操作'''
        return "default"


    def allow_relation(self, obj1, obj2, **hints):
        """是否运行关联操作"""
        return True
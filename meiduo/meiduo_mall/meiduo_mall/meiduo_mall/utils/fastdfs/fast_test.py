from fdfs_client.client import Fdfs_client


#创建客户端
fdst_client =Fdfs_client("./client.conf")


ret = fdst_client.upload_by_filename("/home/python/Desktop/timg.jpg")

print(ret)

"""
getting connection
<fdfs_client.connection.Connection object at 0x7fa1d57ed198>
<fdfs_client.fdfs_protol.Tracker_header object at 0x7fa1d57ed160>
{'Group name': 'group1',
 'Remote file_id': 'group1/M00/00/00/wKhKn17DqTWAMI_iAACrpgiOZw0672.jpg', 
 'Status': 'Upload successed.', 
 'Local file name': '/home/python/Desktop/timg.jpg',
  'Uploaded size': '42.00KB', 
  'Storage IP': '192.168.74.159'}

"""
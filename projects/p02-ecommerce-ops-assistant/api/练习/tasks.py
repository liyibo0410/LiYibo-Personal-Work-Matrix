from celery import Celery                                               # 导入Celery类
import os                                                             # 导入os模块，用于判断当前环境

celery_app = Celery("demo", broker="redis://127.0.0.1:6379/0")          # 创建Celery应用实例

#windows环境需要配置的兼容内容
if os.name == 'nt':                                                     # 如果是windows环境        
    celery_app.conf.update(                                             # 更新Celery应用实例的配置
        worker_pool='solo',                                             # 设置worker池为solo，用于在windows环境下运行Celery
    )

@celery_app.task                                                        # 定义Celery任务
def add(left: int, right: int) -> int:                                  # 定义任务函数，用于计算两个整数的和                            
    return left + right                                                 # 返回两个整数的和
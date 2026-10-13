# 日志配置的工具模块

import logging
import colorlog # uv add colorlog

# 初始化全局日志对象
logger = logging.getLogger()

# 设置日志的默认的级别
logger.setLevel(logging.DEBUG)

# 加载彩色日志处理器
handler = colorlog.StreamHandler()
# 定义日志输出的格式
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',  # INFO 显示为绿色
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))

# 应用日志配置信息
logger.addHandler(handler)


def configure_project_logging():
    """初始化/配置项目全局日志（彩色输出）。幂等，可重复调用。

    源文件（教程 2.深度搜索项目.md）的 api/server.py 与 agent/main_agent.py
    入口均调用本函数，故在此提供实现。
    """
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        _handler = colorlog.StreamHandler()
        _handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        ))
        logger.addHandler(_handler)
    return logger

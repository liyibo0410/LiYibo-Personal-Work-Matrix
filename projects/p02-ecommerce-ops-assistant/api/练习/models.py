from sqlalchemy import String                                       # 导入String类型
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column   # 导入DeclarativeBase、Mapped、mapped_column类型


#1. 定义基类
class Base(DeclarativeBase):                                         # 定义基类，继承DeclarativeBase         
    pass                                                             # 空类，用于定义模型类的基类

#2. 定义模型类 => 对照mysql中的表格
class User(Base):                                                    # 定义模型类，继承Base         
    __tablename__ = "users"                                          # 定义表名为users   

    id: Mapped[int] = mapped_column(primary_key=True)                # 定义主键列，类型为int
    name: Mapped[str] = mapped_column(String(50))                    # 定义姓名列，类型为String(50)
    # email: Mapped[str] = mapped_column(String(100), unique=True)   # 定义邮箱列，类型为String(100)，唯一


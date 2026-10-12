from fastapi import FastAPI          # 导入FastAPI类

app = FastAPI(title="API Hello")     # 创建FastAPI实例  

# 新增根路径接口
@app.get("/")                        # 定义根路径为 /，方法为 GET
def index():                         # 定义函数为 index，返回值为字典
    return {"msg": "hello fastapi，访问 /health 查看健康检查"}      
# 返回字典，包含 msg 键，值为字符串 hello fastapi，访问 /health 查看健康检查

@app.get("/health")                  # 定义根路径为 /health，方法为 GET
def health() -> dict[str, str]:      # 定义函数为 health，返回值为字典
    return {"status": "ok"}          # 返回字典，包含 status 键，值为字符串 ok


# 启动：
# uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 另开一个 PowerShell 窗口验证：
# Invoke-RestMethod http://127.0.0.1:8000/health

# 预期输出：`status : ok`。浏览器访问 `http://127.0.0.1:8000/docs` 可以看到 FastAPI 自动生成的接口文档。

# | 代码                  | 作用                           | 初学者要记住什么                    |
# | --------------------- | ------------------------------ | ----------------------------------- |
# | `app = FastAPI(...)`  | 创建整个 API 应用              | 一个后端项目通常只有一个主应用对象  |
# | `@app.get("/health")` | 把下方函数绑定到 GET `/health` | GET 通常用于读取或健康检查          |
# | `def health()`        | 收到请求后执行的 Python 函数   | 函数名可读性比 URL 更方便开发者理解 |
# | `-> dict[str, str]`   | 描述返回值类型                 | 让编辑器和框架更早发现不一致        |
# | `{"status": "ok"}`    | JSON 响应内容                  | 浏览器、前端和脚本都能读取          |

# uv run uvicorn main:app --reload       # 开发模式启动 main.py 中的 app
# Invoke-RestMethod http://127.0.0.1:8000/health

print('------------------'*20)              

from pydantic import BaseModel, Field                           # 导入 BaseModel 和 Field 类


class ProductCreate(BaseModel):                                 # 定义 ProductCreate 类，继承 BaseModel
    name: str = Field(min_length=1, max_length=100)             # 定义 name 字段，类型为 str，最小长度为 1，最大长度为 100
    price: float = Field(gt=0)                                  # 定义 price 字段，类型为 float，必须大于 0


@app.post("/products")                                          # 定义 products 路径，方法为 POST
def create_product(product: ProductCreate) -> ProductCreate:    # 定义函数为 create_product，参数为 product，返回值为 ProductCreate
    return product                                              # 返回 product 参数


# 验证：

# ```powershell
# Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/products `
#   -ContentType 'application/json' `
#   -Body '{"name":"低糖燕麦饼干","price":29.9}'
# ```

# 把 `price` 改成 `0` 再试一次，会得到 422 校验错误。这就是后续课程中 Schema 的原型。

# 请求成功时，FastAPI 会先把 JSON 转成 `ProductCreate` 对象，再执行 `create_product`。请求失败时函数根本不会执行；这就是“把不合法数据挡在业务代码外面”。正式项目把这类模型集中放在 `api/app/schemas.py`，不与 SQLAlchemy 数据库模型混写。

# ### 常用写法速记

# | 写法                  | 含义                | 例子                              |
# | --------------------- | ------------------- | --------------------------------- |
# | `str`、`int`、`float` | 基础类型            | `quantity: int`                   |
# | `str | None`          | 可以缺失或为 `null` | `remark: str | None = None`       |
# | `list[str]`           | 字符串列表          | `tags: list[str] = []`            |
# | `Field(gt=0)`         | 数值必须大于 0      | `price: float = Field(gt=0)`      |
# | `Field(min_length=1)` | 文本至少一个字符    | `name: str = Field(min_length=1)` |

# > **不要混淆：** Pydantic Schema 是“接口输入/输出合同”；SQLAlchemy Model 是“数据库表蓝图”。它们字段常常相似，但职责不同，正式项目两者都会存在。


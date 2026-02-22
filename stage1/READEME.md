## 1. 框架选择
 
- 核心框架：纯Python + 千问API（qwen-max模型）

- 选择原因：Python生态丰富，千问API调用便捷，无需复杂框架即可快速实现Agent核心逻辑，适合入门学习。
 
## 2. 工具设计思路
 
- 围绕生活场景设计三个高频工具：天气查询、快递费计算、购物清单管理，覆盖用户日常需求。

- 每个工具明确输入参数、输出格式和功能描述，确保可独立调用，便于调试和复用。

- 工具注册表采用千问API要求的格式，包含 type: "function" 和 function 字段，保证LLM能正确解析工具信息。
## 3. 遇到的问题及解决方法

- ImportError: cannot import name 'TOOLS'  文件名与目录名冲突,Python优先导入目录而非文件。 解决：重命名冲突目录，或修改导入语句为相对导入。

-InternalError: Algo.InvalidParameter  工具格式不符合千问API要求。 解决：为每个工具添加 type: "function" ，并将 name 、 description 等字段包裹在 function 字典内。 

-天气工具无法获取数据，心知天气API Key配置错误或城市名格式不支持。 解决：更换为 wttr.in 公开接口，无需Key且支持中文城市名。

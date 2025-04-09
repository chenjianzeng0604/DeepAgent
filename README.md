# DeepAgent (深度智能代理)

一个结合智能规划、深度研究和联网搜索的智能分析系统，专注于任何领域的深度分析与内容挖掘。提供友好的Web界面，可以实时获取多平台信息并生成专业分析报告。支持在线爬取功能，可以获取最新信息，并通过邮件发送结果。

## 目录

- [功能特点](#功能特点)
- [系统架构](#系统架构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
  - [Web界面](#web界面)
  - [多平台爬虫](#多平台爬虫)
  - [作为Python库使用](#作为python库使用)
- [项目结构](#项目结构)
- [核心模块介绍](#核心模块介绍)
- [开发指南](#开发指南)
- [问题排查](#问题排查)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系方式](#联系方式)

## 功能特点

- **智能规划**: 基于用户需求自动规划分析步骤和策略
- **深度研究**: 针对任何领域进行专业化分析和信息提取
- **多平台爬取**: 支持Web站点、GitHub、arXiv、搜索引擎等多平台内容获取
- **实时爬虫**: 支持设置关键词和平台，实时爬取内容并存入知识库
- **联网搜索**: 实时获取最新动态、研究成果和相关案例
- **对话式交互**: 提供自然、连贯的对话体验，支持流式输出
- **专业知识库**: 内置领域专业知识和分析框架
- **可视化分析**: 生成直观的数据可视化报告
- **邮件分发**: 支持将生成的报告通过邮件发送给用户
- **Web界面**: 提供友好的Web交互界面，支持WebSocket实时通信

## 系统架构

DeepAgent采用模块化设计，主要包含以下核心组件：

- **智能体模块**: 基于大语言模型的智能代理，负责规划和执行研究任务
- **爬虫模块**: 多平台内容获取系统，支持常规网站、GitHub、arXiv等
- **向量数据库**: 使用Milvus存储和检索文本嵌入，实现高效的语义搜索
- **搜索模块**: 集成多种搜索引擎，获取实时信息
- **邮件模块**: 支持将生成的报告通过邮件发送给用户
- **Web服务**: 基于FastAPI的Web界面，提供用户友好的交互体验

## 环境要求

- Python 3.8+
- 足够的网络带宽以支持实时搜索和内容爬取
- OpenAI API密钥（或兼容的API服务，如阿里云通义千问）
- Milvus向量数据库（用于知识库存储和检索）
- SMTP电子邮件发送服务（用于发送报告）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/chenjianzeng0604/deepagent.git
cd deepagent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 环境配置

复制`.env_example`文件为`.env`并根据自己的环境进行配置：

```bash
cp .env_example .env
# 使用编辑器打开.env文件进行配置
```

主要配置项包括：

```
# LLM API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 应用配置
HOST=127.0.0.1
PORT=8000
DEBUG=true

# 应用信息
APP_NAME=deepagent
APP_VERSION=0.1.0
LOG_LEVEL=INFO

# LLM模型配置
LLM_MODEL=deepseek-r1                       # 深度总结模型
LLM_TEMPERATURE=0.7                         # 模型温度参数
LLM_MAX_TOKENS=4096                         # 最大生成token数
LLM_USE_TOOL_MODEL=qwen2.5-72b-instruct     # 工具调用模型
ARTICLE_QUALITY_MODEL=qwq-plus-latest       # 文章质量评估模型
EVALUATE_INFORMATION_MODEL=qwq-plus-latest  # 信息量评估与规划模型
COMPRESSION_MODEL=qwq-plus-latest           # 文章压缩模型

# 爬虫配置
CRAWLER_MAX_LINKS_RESULT=30                # 每次爬取的最大链接数
CRAWLER_EXTRACT_PDF_TIMEOUT=8              # PDF提取超时时间（秒）
CRAWLER_FETCH_URL_TIMEOUT=18               # URL获取超时时间（秒）
CRAWLER_FETCH_ARTICLE_WITH_SEMAPHORE=3     # 最大并发任务数
CLOUDFLARE_BYPASS_WAIT_FOR_TIMEOUT=600     # Cloudflare绕过等待超时（毫秒）

# Milvus向量数据库配置
MILVUS_URI=http://localhost:19530    # Milvus服务地址
MILVUS_USER=your_milvus_user         # Milvus用户名
MILVUS_PASSWORD=your_milvus_password # Milvus密码

# 向量数据库检索配置
VECTORDB_LIMIT=2                     # 向量数据库检索限制

# 邮件配置
EMAIL_SMTP_SERVER=smtp.example.com   # SMTP服务器地址
EMAIL_SMTP_PORT=587                  # SMTP端口
EMAIL_SMTP_USERNAME=your_email_username  # SMTP用户名
EMAIL_SMTP_PASSWORD=your_email_password  # SMTP密码
EMAIL_SENDER=your_email@example.com  # 发件人
EMAIL_RECIPIENT=user1_email@example.com,user2_email@example.com # 收件人
EMAIL_USE_TLS=True                   # 是否使用TLS

# 研究配置
RESEARCH_MAX_ITERATIONS=6            # 最大研究迭代次数
```

### 4. 安装Milvus向量数据库

本项目使用Milvus作为向量数据库，用于存储和检索文本嵌入。您可以通过Docker快速安装：

```bash
# 安装Docker（如果尚未安装）
# Windows: 下载并安装Docker Desktop
# Linux: sudo apt-get install docker.io docker-compose

# 拉取并启动Milvus（单机版）
docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.3.3 standalone
```

### 5. 初始化浏览器自动化工具

部分复杂网站的爬取需要使用Playwright进行浏览器模拟：

```bash
python -m playwright install
```

### 6. 启动应用

启动Web服务：

```bash
python -m uvicorn src.app.main_web:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000 即可使用Web界面。

## 使用指南

### Web界面

DeepAgent提供了直观的Web界面，支持以下功能：

1. **研究分析**：输入研究主题，系统会自动规划研究步骤并执行
2. **实时对话**：与智能体进行实时对话，获取分析结果
3. **在线爬取**：实时爬取网络内容，获取最新信息
4. **报告生成**：生成专业分析报告，支持多种格式导出

### 多平台爬虫

DeepAgent支持从多个平台获取信息：

- **Web站点**：支持爬取一般网页内容
- **GitHub**：获取开源项目信息和代码分析
- **arXiv**：获取学术论文和研究成果
- **搜索引擎**：通过搜索引擎API获取实时信息



### 作为Python库使用

您也可以将DeepAgent作为Python库集成到自己的项目中：

```python
from deepagent.agents import DeepResearchAgent
from deepagent.tools.crawler import WebCrawler

# 初始化智能体
agent = DeepResearchAgent()

# 执行研究任务
result = await agent.research("量子计算最新进展")

# 使用爬虫工具
crawler = WebCrawler()
data = await crawler.fetch("https://example.com/quantum-computing")
```

## 项目结构

```
├── logs/                  # 日志文件
├── src/                   # 源代码
│   ├── agents/            # 智能体模块
│   │   └── deepresearch_agent.py  # 深度研究智能体
│   ├── app/               # 应用模块
│   │   ├── chat_bean.py   # 聊天消息模型
│   │   └── main_web.py    # Web界面主程序
│   ├── config/            # 配置模块
│   │   └── app_config.py  # 应用配置
│   ├── database/          # 数据库模块
│   │   └── vectordb/      # 向量数据库
│   ├── log/               # 日志模块
│   ├── memory/            # 内存管理
│   ├── model/             # 模型模块
│   │   ├── embeddings/    # 嵌入模型
│   │   └── llm_client.py  # LLM客户端
│   ├── prompts/           # 提示词模板
│   ├── session/           # 会话管理
│   ├── tools/             # 工具模块
│   │   ├── crawler/       # 爬虫工具
│   │   ├── distribution/  # 分发工具
│   │   └── search/        # 搜索工具
│   └── utils/             # 工具函数
├── templates/             # Web模板文件
│   └── app/               # 应用界面模板
├── .env                   # 环境变量配置
├── .env_example           # 环境变量配置示例
└── requirements.txt       # 项目依赖
```

## 核心模块介绍

### 智能体模块 (src/agents)

智能体模块是DeepAgent的核心，负责规划和执行研究任务。主要功能包括：

- **任务规划**：根据用户需求自动规划研究步骤
- **工具调用**：调用爬虫、搜索等工具获取信息
- **内容分析**：分析获取的信息，提取关键内容
- **报告生成**：生成专业分析报告

### 爬虫模块 (src/tools/crawler)

爬虫模块负责从多个平台获取信息，支持以下功能：

- **网页爬取**：支持爬取一般网页内容
- **GitHub爬取**：获取开源项目信息
- **arXiv爬取**：获取学术论文
- **实时爬取**：根据用户需求实时爬取内容

### 向量数据库模块 (src/database/vectordb)

向量数据库模块负责存储和检索文本嵌入，实现高效的语义搜索：

- **文本嵌入**：将文本转换为向量表示
- **向量存储**：将向量存入Milvus数据库
- **语义搜索**：基于语义相似度检索内容

### Web服务模块 (src/app)

Web服务模块提供用户友好的Web界面：

- **WebSocket通信**：支持实时对话和流式输出
- **任务管理**：管理研究任务和爬取任务

### 分发模块 (src/tools/distribution)

分发模块负责将生成的报告分发给用户：

- **邮件发送**：通过邮件发送报告
- **报告格式化**：支持多种格式的报告生成

## 开发指南

### 自定义扩展

您可以通过扩展以下组件来自定义系统的行为：

#### 1. 添加新的爬虫

在`src/tools/crawler`目录下创建新的爬虫类，继承WebCrawler类并实现必要的方法：

```python
from src.tools.crawler.web_crawlers import WebCrawler

class CustomCrawler(WebCrawler):
    async def extract_content(self, url: str) -> str:
        """自定义内容提取逻辑"""
        # 实现特定网站的内容提取逻辑
        return content
        
    async def fetch_article_and_save2milvus(self, query: str, links: list):
        """实现内容获取和存储逻辑"""
        # 自定义内容获取和向量数据库存储逻辑
        pass
```

#### 2. 自定义智能体行为

您可以通过继承DeepresearchAgent类来自定义智能体的行为：

```python
from src.agents.deepresearch_agent import DeepresearchAgent
from src.app.chat_bean import ChatMessage
from typing import AsyncGenerator

class CustomAgent(DeepresearchAgent):
    async def process_stream(self, message: ChatMessage) -> AsyncGenerator[dict, None]:
        """自定义处理流程"""
        query = message.message
        self.memory_manager.save_chat_history(self.session_id, [{"role": "user", "content": query}])
        
        # 执行研究并生成结果
        async for chunk in self._research(message):
            yield chunk
```

#### 3. 自定义邮件发送

您可以通过继承EmailSender类来自定义邮件的格式和发送逻辑：

```python
from src.tools.distribution.email_sender import EmailSender
from typing import List

class CustomEmailSender(EmailSender):
    async def send_email(self, 
                    subject: str, 
                    body: str, 
                    is_html: bool = True,
                    additional_recipients: List[str] = None):
        """自定义邮件发送逻辑"""
        # 检查配置
        if not self._check_config():
            return False
        
        # 自定义邮件格式和发送逻辑
        return success
```



#### 3. 自定义智能体行为

您可以通过修改`src/agents/deepresearch_agent.py`文件来自定义智能体的行为：

```python
# 自定义智能体行为
class CustomAgent(DeepresearchAgent):
    async def process_stream(self, message: ChatMessage) -> AsyncGenerator[dict, None]:
        """自定义处理流程"""
        query = message.message
        self.memory_manager.save_chat_history(self.session_id, [{"role": "user", "content": query}])
        
        # 自定义研究逻辑
        research_results = {"results": []}
        async for chunk in self._research(message):
            # 处理研究结果
            pass
            
        # 生成深度总结
        response_content = ""
        async for chunk in self._deep_summary(message, research_results):
            # 处理总结结果
            pass
            
        return response_content
```

#### 4. 自定义邮件发送

您可以通过修改`src/tools/distribution/email_sender.py`文件来自定义邮件的格式和发送逻辑：

```python
# 自定义邮件发送逻辑
async def send_email(self, 
                    subject: str, 
                    body: str, 
                    is_html: bool = True,
                    additional_recipients: List[str] = None):
    # 检查配置
    if not self._check_config():
        return False
    
    # 合并默认收件人和额外收件人
    recipients = list(self.recipient_emails)  # 创建默认收件人的副本
    if additional_recipients:
        for email in additional_recipients:
            if email and isinstance(email, str) and email.strip():
                email = email.strip()
                if email not in recipients:
                    recipients.append(email)
    
    # 发送邮件逻辑
    # ...
```

## 问题排查

### 常见问题及解决方案

1. **API密钥错误**
   - 错误信息: "API key not valid"
   - 解决方案: 检查`.env`文件中的`OPENAI_API_KEY`是否正确设置

2. **Milvus连接失败**
   - 错误信息: "Failed to connect to Milvus"
   - 解决方案: 
     - 确认Milvus容器是否运行
     - 检查Milvus连接参数是否正确

3. **爬虫错误**
   - 错误信息: "Failed to parse URL" 或 "Timeout"
   - 解决方案:
     - 增加超时时间 `CRAWLER_FETCH_URL_TIMEOUT=120`
     - 配置代理服务

4. **邮件发送失败**
   - 错误信息: "Failed to send email" 或 "Authentication error"
   - 解决方案:
     - 确认SMTP配置是否正确
     - 检查邮件提供商是否允许应用程序访问

5. **Web服务启动失败**
   - 错误信息: "Address already in use"
   - 解决方案:
     - 检查端口是否被占用
     - 更改端口号 `--port 8001`

### 日志和调试

开启详细日志以便调试：

```
# 在.env文件中设置
LOG_LEVEL=DEBUG
```

日志文件位于 `logs/app.log`

## 贡献指南

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

此项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

项目维护者: chenjianzeng - 372285925@qq.com

项目链接: [https://github.com/chenjianzeng0604/DeepAgent](https://github.com/chenjianzeng0604/DeepAgent)

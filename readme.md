# 文件说明

方案说明，本项目为一个自动编码Agent，实现了三种编程模式

1. 直接编码并修复
2. 使用题目向量召回文档并编码修复
3. 使用简单的自建搜索引擎查询编码修复

为了辅助编程，实现了一个递归获取当前运行环境函数文档的辅助功能。

以下是文件说明：

### 1. [get_package_doc.py](get_package_doc.py)
递归获取某个包的所有函数文档

### 2. [get_embedding.py](get_embedding.py)
将函数文档转换成embedding


### 3. [main.py](main.py)
直接书写函数，走修改函数流程直到正确（最好成绩）

### 4. [rag_main.py](rag_main.py)[main.py](main.py)
使用题目和函数文档匹配后书写代码，然后修改

### 5. [super_rag_main.py](super_rag_main.py)
大模型生成查询query后进行书写代码，然后修改

### 6. [llm.py](llm.py)

比赛使用的微软GPT-4o 实测和openai相同。


其他开源项目：

[第三届琶洲算法大赛-GLM法律行业大模型挑战赛道第五名方案](https://github.com/MetaGLM/LawGLM/tree/tangtang/APIWeaver-lawGLM)
[后续优化](https://github.com/MeiPixel/APIWeaver)




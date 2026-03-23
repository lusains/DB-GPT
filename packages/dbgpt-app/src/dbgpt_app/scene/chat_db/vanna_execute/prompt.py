"""ChatWithDbVanna Prompt Template.

This module defines the Vanna-enhanced prompt with DDL, SQL examples,
and documentation sections aligned with Vanna's official approach.
"""

import json

from dbgpt._private.config import Config
from dbgpt.core import (
    ChatPromptTemplate,
    HumanPromptTemplate,
    MessagesPlaceholder,
    SystemPromptTemplate,
)
from dbgpt_app.scene import AppScenePromptTemplateAdapter, ChatScene
from dbgpt_app.scene.chat_db.auto_execute.out_parser import DbChatOutputParser

CFG = Config()


_PROMPT_SCENE_DEFINE_EN = "You are a database expert with access to trained schema and SQL examples. "
_PROMPT_SCENE_DEFINE_ZH = "你是一个数据库专家，可以访问训练过的数据库结构和SQL示例。"

_DEFAULT_TEMPLATE_EN = """
You are a {dialect} expert. Please help to generate a SQL query to answer the question. \
Your response should ONLY be based on the given context and follow the response guidelines and format instructions.

===Domain Background & Business Rules
{domain_rule}

===Domain Knowledge (Ontology)
{vanna_ontology}

===Tables
{vanna_ddl}

===Additional Context
{vanna_documentation}

===Business Documentation
{vanna_business_docs}

{table_info}

===Response Guidelines
1. If the provided context is sufficient, please generate a valid SQL query without any explanations for the question.
2. If the provided context is almost sufficient but requires knowledge of a specific string in a particular column, please generate an intermediate SQL query to find the distinct strings in that column. Prepend the query with a comment saying intermediate_sql.
3. If the provided context is insufficient, please explain why it can't be generated.
4. Please use the most relevant table(s).
5. If the question has been asked and answered before, please repeat the answer exactly as it was given before.
6. Ensure that the output SQL is {dialect}-compliant and executable, and free of syntax errors.
7. Always limit the query to a maximum of {top_k} results unless the user specifies in the question the specific number of rows of data he wishes to obtain.
8. Please choose the best one from the display methods given below for data rendering, and put the type name into the name parameter value that returns the required format. If you cannot find the most suitable one, use 'Table' as the display method. The available data display methods are as follows: {display_type}

===Previously Successful Answers (Agent Memory)
{vanna_memory}

===Question-SQL Examples
{vanna_sql_examples}

User Question:
    {user_input}

Please think step by step and respond according to the following JSON format:
    {response}
Ensure the response is correct json and can be parsed by Python json.loads.

"""

_DEFAULT_TEMPLATE_ZH = """
你是一个{dialect}专家。请帮助生成一个SQL查询来回答问题。\
你的回答应该仅基于给定的上下文，并遵循响应指南和格式说明。

===领域背景与业务规则
{domain_rule}

===领域知识（本体）
{vanna_ontology}

===表结构
{vanna_ddl}

===附加上下文
{vanna_documentation}

===业务文档
{vanna_business_docs}

{table_info}

===响应指南
1. 如果提供的上下文足够，请生成一个有效的SQL查询，无需任何解释。
2. 如果提供的上下文几乎足够，但需要知道特定列中的特定字符串，请生成一个中间SQL查询来查找该列中的不同字符串。在查询前加上注释 intermediate_sql。
3. 如果提供的上下文不足，请解释为什么无法生成。
4. 请使用最相关的表。
5. 如果问题之前已被问过并回答过，请完全重复之前给出的答案。
6. 确保输出的SQL符合{dialect}语法规范，可执行且没有语法错误。
7. 除非用户在问题中指定了他希望获得的具体数据行数，否则始终将查询限制为最多{top_k}个结果。
8. 请从如下给出的展示方式中选择最优的一种用以进行数据渲染，将类型名称放入返回要求格式的name参数值中，如果找不到最合适的则使用'Table'作为展示方式，可用数据展示方式如下: {display_type}

===之前成功的回答（Agent记忆）
{vanna_memory}

===问题-SQL示例
{vanna_sql_examples}

用户问题:
    {user_input}

请一步步思考并按照以下JSON格式回复：
    {response}
确保返回正确的json并且可以被Python json.loads方法解析。

"""

_DEFAULT_TEMPLATE = (
    _DEFAULT_TEMPLATE_EN if CFG.LANGUAGE == "en" else _DEFAULT_TEMPLATE_ZH
)

PROMPT_SCENE_DEFINE = (
    _PROMPT_SCENE_DEFINE_EN if CFG.LANGUAGE == "en" else _PROMPT_SCENE_DEFINE_ZH
)

RESPONSE_FORMAT_SIMPLE = {
    "thoughts": "thoughts summary to say to user",
    "direct_response": "If the context is sufficient to answer user, reply directly "
    "without sql",
    "sql": "SQL Query to run",
    "display_type": "Data display method",
}


PROMPT_TEMPERATURE = 0.5

prompt = ChatPromptTemplate(
    messages=[
        SystemPromptTemplate.from_template(
            _DEFAULT_TEMPLATE,
            response_format=json.dumps(
                RESPONSE_FORMAT_SIMPLE, ensure_ascii=False, indent=4
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanPromptTemplate.from_template("{user_input}"),
    ]
)

prompt_adapter = AppScenePromptTemplateAdapter(
    prompt=prompt,
    template_scene=ChatScene.ChatWithDbVanna.value(),
    stream_out=True,
    output_parser=DbChatOutputParser(),
    temperature=PROMPT_TEMPERATURE,
)
CFG.prompt_template_registry.register(prompt_adapter, is_default=True)

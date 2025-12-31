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


_PROMPT_SCENE_DEFINE_EN = "You are a database expert. "
_PROMPT_SCENE_DEFINE_ZH = "你是一个数据库专家. "

_DEFAULT_TEMPLATE_EN = """
Please answer the user's question based on the database selected by the user, the ontology schema from the knowledge graph, the source mapping information and some \
of the available table structure definitions of the database.
Database name:
     {db_name}
Ontology Schema (from Knowledge Graph):
     {graph_schema}
Source mapping:
     {source_mapping}
Table structure definition:
     {table_info}
{semantic_context}
{domain_rules}

Constraint:
    1.Please understand the user's intention based on the user's question, the ontology \
    schema, the source mapping, Semantic Context, and Domain Rules above. \
    The Semantic Context provides: \
    - Chinese term translations to actual column names \
    - Business meanings and allowed values for fields \
    - Table relationships for JOIN operations \
    The Domain Rules provide business background, process flows, and query examples. \
    Use this knowledge to create a grammatically correct {dialect} sql. \
    If sql is not required, answer the user's question directly.
    2.Always limit the query to a maximum of {top_k} results unless the user specifies \
    in the question the specific number of rows of data he wishes to obtain.
    3.Schema sources: (a) Table structure definition (b) Source mapping (MySQL tables). \
    If table_info is empty/incomplete, use Source mapping for table/column names. \
    Only refuse if BOTH sources lack needed tables. Never fabricate information.
    4.Please be careful not to mistake the relationship between tables and columns when\
     generating SQL. Use the Semantic Context's table relationships and the source mapping's \
     ObjectProperty (Foreign Key) information to guide JOIN operations correctly.
    5.Please check the correctness of the SQL and ensure that the query performance is\
     optimized under correct conditions. IMPORTANT: For MySQL, NEVER use double quotes for \
     identifiers (table names, column names). Use backticks (`) or no quotes. \
     Example: SELECT `column_name` FROM `table_name` or SELECT column_name FROM table_name
    6. For text fields such as names, titles, descriptions, types, etc., prefer using LIKE \
    for fuzzy matching unless the user explicitly requests exact matching. Users often \
    provide partial names or abbreviations. \
    IMPORTANT: When the Semantic Context's [Term Normalization Hints] section indicates \
    that the user's input is an alias/abbreviation for a term, you MUST use the canonical \
    (normalized) form for the LIKE fuzzy match. \
    Example: If user says "二开" and the hint says it's an alias for "二次开发", \
    use WHERE contractor_work_type LIKE '%二次开发%', NOT LIKE '%二开%'. \
    Example: If user says "长江存储", the actual data might be "长江存储责任有限公司", \
    so use WHERE column_name LIKE '%长江存储%'.
    7. Please choose the best one from the display methods given below for data \
    rendering, and put the type name into the name parameter value that returns \
    the required format. If you cannot find the most suitable one, use 'Table' as \
    the display method. , the available data display methods are as follows: \
    {display_type}

User Question:
    {user_input}
Please think step by step and respond according to the following JSON format:
    {response}
Ensure the response is correct json and can be parsed by Python json.loads.

"""

_DEFAULT_TEMPLATE_ZH = """
请根据用户选择的数据库、知识图谱中的本体模式、源映射信息和该库的部分可用表结构定义来回答用户问题.
数据库名:
    {db_name}
本体模式（来自知识图谱）:
    {graph_schema}
源映射信息:
    {source_mapping}
表结构定义:
    {table_info}
{semantic_context}
{domain_rules}

约束:
    1. 请根据用户问题、本体模式、源映射、语义上下文以及领域规则来理解用户意图。\
    语义上下文提供了以下关键信息：\
    - 中文术语到实际列名的映射（如"项目负责人"对应pj_leader列）\
    - 字段的业务含义和可选枚举值\
    - 表之间的关联关系用于指导JOIN操作\
    领域规则提供了业务背景、业务流程和查询示例，请务必参考这些规则来理解业务逻辑和成本计算方式。\
    利用这些知识创建一个语法正确的{dialect} sql。如果不需要sql，则直接回答用户问题。
    2. 除非用户在问题中指定了他希望获得的具体数据行数，否则始终将查询限制为最多\
     {top_k} 个结果。
    3. Schema来源：(a)表结构定义 (b)源映射(MySQL表)。\
    若表结构为空/不完整，使用源映射中的表和列名。仅当两者都缺少所需表时才拒绝生成。禁止捏造信息。
    4. 请注意生成SQL时不要弄错表和列的关系。使用语义上下文中的表关联关系和源映射中的\
    ObjectProperty（外键）信息来正确指导JOIN操作。
    5. 请检查SQL的正确性，并保证正确的情况下优化查询性能。重要提示：对于MySQL数据库，\
    千万不要使用双引号来引用标识符（表名、列名），请使用反引号(`)或不使用引号。\
    示例：SELECT `column_name` FROM `table_name` 或 SELECT column_name FROM table_name
    6. 对于名称、标题、描述、类型等文本字段的查询条件，除非用户明确要求精确匹配，\
    否则优先使用 LIKE 进行模糊匹配。用户通常提供的是简称或部分名称。\
    重要：当语义上下文中的【术语规范化提示】指出用户输入的是某个术语的简称/别名时，\
    必须使用规范化后的完整名称进行LIKE模糊匹配。\
    例如：用户输入"二开"，实际数据库值是"二次开发"，\
    应使用 WHERE contractor_work_type LIKE '%二次开发%'，而不是 LIKE '%二开%'。\
    又如：用户输入"长江存储"，实际数据可能是"长江存储责任有限公司"，\
    应使用 WHERE column_name LIKE '%长江存储%'。
    7. 请从如下给出的展示方式种选择最优的一种用以进行数据渲染，\
    将类型名称放入返回要求格式的name参数值中，如果找不到最合适的\
    则使用'Table'作为展示方式，可用数据展示方式如下: {display_type}
用户问题:
    {user_input}
请一步步思考并按照以下JSON格式回复：
      {response}
确保返回正确的json并且可以被Python json.loads方法解析.

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


# Temperature is a configuration hyperparameter that controls the randomness of
# language model output.
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
    template_scene=ChatScene.ChatWithDbExecuteOntology.value(),
    stream_out=True,
    output_parser=DbChatOutputParser(),
    temperature=PROMPT_TEMPERATURE,
)
CFG.prompt_template_registry.register(
    prompt_adapter, language=CFG.LANGUAGE, is_default=True
)

import os
import logging

from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_types
from sc_client.client import template_search, search_links_by_contents

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScStructure, ScSet
from sc_kpm.utils import get_link_content_data, get_system_idtf
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    get_action_result,
    execute_agent,
)
from sc_kpm import ScKeynodes
from sc_kpm.identifiers import CommonIdentifiers
from together import Together  # Import TogetherAI library

from .search_module_idtfs import SearchModuleIdentifiers


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]")

# Global variable to store API key (for simplicity in this example, consider more secure methods in production)
# TOGETHER_AI_API_KEY = os.environ.get("TOGETHER_AI_API_KEY") # No longer global, get inside run()


def get_together_ai_response(api_key, prompt):
    """
    Sends a prompt to Together AI API and returns the response.
    """
    try:
        client = Together(api_key=api_key)
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",  # Or choose another model from Together AI
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error getting response from Together AI: {e}"


class CallAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_call_agent")

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("CallAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:

        link, = get_action_arguments(action_node, 1)
        link_query = get_link_content_data(link)

        api_key = "814aaa3d65cd5cd6dedbab7f8685889419ad93285155ae2d7c1a94869343faa4"

        if not api_key:
            error_message = "TOGETHER_AI_API_KEY is not set in environment variables!"
            self.logger.error(error_message)
            return ScResult.ERROR
        
        subject_area_prompt = f"""
          Определи, к какой из следующих предметных областей относится запрос пользователя.  Выбери ТОЧНОЕ НАЗВАНИЕ ПРЕДМЕТНОЙ ОБЛАСТИ из списка и верни только это название в качестве ответа.

          Предметные области:

          1. "Структура и Иерархия":  Эта область включает запросы о структуре сущностей, их составных частях, **компонентах, элементах, подразделениях и составляющих**.  Агенты этой области отвечают на вопросы о том, **из каких частей состоит сущность**, из чего состоит сущность (дочерние элементы), частью чего она является (родительские элементы), и к какой декомпозиции она принадлежит (родительская декомпозиция).  Запросы в этой области направлены на понимание взаимосвязей 'часть-целое' и иерархического положения сущностей.
              Примеры запросов:
                - "Найди дочерние элементы дерева"
                - "Какие сущности входят в состав Солнечной системы?"
                - "В какую декомпозицию входит раздел 'Кулинария'?"
                - "Кто родители дерева?"
                - "Из каких компонентов состоит рецепт?"
                - "Какие элементы включает рецепт?"
                - "Подразделения рецепта?"
                - "Составные части компьютера"
                - "Компоненты автомобиля"
                - "Элементы атомного ядра"

          2. "Описание и Характеристики": Эта область включает запросы на получение описания, определения сущности. Агенты этой области предоставляют информацию о сущности, отвечая на вопросы 'что это такое?'. Агенты этой области нацелены на предоставление определений, описаний и ключевых характеристик запрашиваемой сущности.
              Примеры запросов:
                - "Дай описание рецепта"
                - "Что такое слон?"
                - "Описание для 'Сущность с точкой.' пожалуйста"
                - "Охарактеризуйте компьютер"
                - "Расскажите о Солнечной системе"

          3. "Классификация и Категоризация": Эта область включает запросы, которые помогают классифицировать сущности, определяя их принадлежность к различным категориям. Агенты этой области могут определить как самый широкий класс (максимальный класс), так и более узкие или общие классы (не максимальный класс) для заданной сущности.
              Примеры запросов:
                - "Какой максимальный класс объектов исследования у слона?"
                - "Какие элементы являются максимальными классами у 'рецепт борща'?"
                - "Какой не максимальный класс у слона?"
                - "Назови более общий класс для 'рецепт борща'"
                - "К какой категории относится рецепт?"
                - "Класс автомобиля"

          4. "Семантические Связи и Знания":  Эта область включает запросы, которые извлекают ключевую информацию и связи, связанные с сущностью. Агенты этой области ищут важные семантические элементы, аспекты знания и концепции, которые раскрывают сущность с разных сторон.
              Примеры запросов:
                - "Какие ключевые элементы рецепта?"
                - "Найди важные SC-элементы для 'Солнечная система'"
                - "Основные знания о дереве"
                - "Важные аспекты компьютера"

          5. "Общие Запросы": Эта область предназначена для обработки запросов, которые не относятся к поиску структуры, описаний, классификации или семантических связей сущностей. Сюда попадают запросы общего характера, не связанные напрямую с характеристиками или иерархией сущностей.
              Примеры запросов:
                - "Сколько будет 2 + 2?"
                - "Рецепты вкусных блюд"
                - "Погода на завтра"
                - "Новости спорта"

          Запрос пользователя: {link_query}

          Ответ (верни только название предметной области):
              """
        subject_area_prompt_answer = get_together_ai_response(api_key, subject_area_prompt).strip()

        if subject_area_prompt_answer == "Структура и Иерархия":
            self.structure_and_hierarchy(action_node, link_query, api_key)
            return ScResult.OK
        elif subject_area_prompt_answer == "Описание и Характеристики":
            self.description_and_characteristics(action_node, link_query, api_key)
            return ScResult.OK
        elif subject_area_prompt_answer == "Классификация и Категоризация":
            self.classification_and_categorization(action_node, link_query, api_key)
            return ScResult.OK
        elif subject_area_prompt_answer == "Семантические Связи и Знания":
            self.semantic_relationships_and_knowledge(action_node, link_query, api_key)
            return ScResult.OK
        elif subject_area_prompt_answer == "Общие Запросы":
            self.general_questions(link_query, api_key)
            return ScResult.OK
        else:
            print(f"ОШИБКА: Не задействована никакая предметная область. Ответ модели: {subject_area_prompt_answer}")
            return ScResult.ERROR
    
    def find_entity_by_name(self, entity_name, action_node):
        """Возвращает ноду по названию"""
        node_idtf_link_search_result = search_links_by_contents(entity_name)[0]

        if not node_idtf_link_search_result:
            self.logger.error("Не найден идентификатор: '{}'" @ entity_name)
            finish_action_with_status(action_node, False)
            return ScResult.ERROR

        for node_idtf_link in node_idtf_link_search_result:
            search_node_template = ScTemplate()
            search_node_template.triple_with_relation(
                sc_types.NODE_VAR >> 'node',
                sc_types.EDGE_D_COMMON_VAR,
                node_idtf_link,
                sc_types.EDGE_ACCESS_VAR_POS_PERM,
                ScKeynodes[SearchModuleIdentifiers.NREL_MAIN_IDTF]
            )

            search_node_result = template_search(search_node_template)[0]
            if len(search_node_result) == 0:
                continue

            node = search_node_result.get('node')
            return node
        else:
            self.logger.error("Не найден узел с основным идентификатором: '{}'" @ entity_name)
            finish_action_with_status(action_node, False)
            return ScResult.ERROR
        
    def call_agent_get_string_result(self, entity_name, action_node, action_agent):
        """Вызывает необходимого агента поиска информации и формирует строку для передачи в модель"""
        node = self.find_entity_by_name(entity_name, action_node)
            
        find_template_action, find_template_result = execute_agent(
            {
                node: False,
            },
            [
                CommonIdentifiers.ACTION,
                action_agent,
            ]
        )

        if not find_template_result:
            self.logger.error("Не найдено описание узла: '{}'" @ entity_name)
            finish_action_with_status(action_node, False)
            return ScResult.ERROR
        
        find_template_action_result = ScStructure(set_node=get_action_result(find_template_action))
        info_set = next(iter(find_template_action_result))

        set_results = ScSet(set_node=info_set)

        result_string = ""

        for result in set_results:

            find_lang_action, find_lang_result = execute_agent(
                {
                    result: False,
                },
                [
                    CommonIdentifiers.ACTION,
                    SearchModuleIdentifiers.ACTION_FIND_INFO,
                ]
            )

            find_lang_action_result = ScStructure(set_node=get_action_result(find_lang_action))
            info_link = next(iter(find_lang_action_result))

            answer = get_link_content_data(info_link)

            result_string = result_string + answer + "; "

        return result_string
    
    def structure_and_hierarchy(self, action_node, link_query, api_key):
        area_description_prompt = f"""
          Запрос пользователя: {link_query}

          Ты - система обработки запросов, которая классифицирует входящие запросы и извлекает из них название сущности, если это необходимо.  Твоя задача - обрабатывать запросы, относящиеся к предметной области "Структура и Иерархия".

          Предметная область "Структура и Иерархия":

          Эта область включает запросы о структуре сущностей, их составных частях и иерархических взаимосвязях.  Агенты этой области отвечают на вопросы о том, из чего состоит сущность (дочерние элементы), частью чего она является (родительские элементы), и к какой декомпозиции она принадлежит (родительская декомпозиция).  Запросы в этой области направлены на понимание взаимосвязей 'часть-целое' и иерархического положения сущностей.

          Типы запросов для предметной области "Структура и Иерархия":

          1. "children_needed":  запрос о дочерних элементах или сущностях, входящих в состав другой сущности.
              Примеры запросов: "дочерние элементы дерева", "что входит в состав Солнечной системы", "из чего состоит атом", "подразделы раздела 'Кулинария'", "компоненты рецептурного объекта".
              Ключевые слова и фразы-индикаторы: "дочерние элементы", "входят в состав", "состоит из", "из чего состоит", "что включает", "что содержит", "подразделы", "компоненты", "части".

          2. "parents_needed": запрос о родительских элементах или сущностях, частью которых является данная сущность.
              Примеры запросов: "родители дерева", "чем является Солнечная система", "частью чего является атом", "к чему относится рецепт", "более общее понятие для рецепта".
              Ключевые слова и фразы-индикаторы: "родители", "является частью", "включает в себя", "частью чего является", "к чему относится", "надсистема", "целое для", "более общее понятие", "категория для".

          3. "parent_decomposition_needed": запрос о том, В КАКИЕ ДЕКОМПОЗИЦИИ ВХОДИТ раздел или частью какой декомпозиции является раздел (т.е., ПОИСК РОДИТЕЛЬСКОЙ ДЕКОМПОЗИЦИИ).
              Примеры запросов: "в какую декомпозицию входит раздел 'Кулинария'", "какой декомпозиции принадлежит раздел 'Рецепты'", "декомпозиции для 'Раздел. Общие сведения'", "подразделы у раздела 'Кулинария' кроме Рецептов".
              Ключевые слова и фразы-индикаторы: "входит в декомпозицию", "в какой декомпозиции", "является частью декомпозиции", "в составе какой декомпозиции", "к какой декомпозиции принадлежит", "декомпозиции для", "декомпозиция раздела", "подразделы раздела".

          Извлечение сущности - КЛЮЧЕВОЕ ПРАВИЛО для предметной области "Структура и Иерархия":

          Если тип запроса "children_needed", "parents_needed" или "parent_decomposition_needed":

          **Абсолютный приоритет - текст в кавычках (").  Если в запросе ЕСТЬ текст в кавычках:**

          **ВНИМАНИЕ! ИЗВЛЕКАЙТЕ ВЕСЬ ТЕКСТ В КАВЫЧКАХ ПОЛНОСТЬЮ, ВКЛЮЧАЯ ПЕРВОЕ СЛОВО "Раздел.", "Объект.", "Сущность." и т.д., ЕСЛИ ОНО ЕСТЬ В КАВЫЧКАХ!**

          1. Извлеки **АБСОЛЮТНО ВЕСЬ** текст **НАЧИНАЯ С ПЕРВОЙ КАВЫЧКИ И ЗАКАНЧИВАЯ ПОСЛЕДНЕЙ**.
          2. Включай в извлеченный текст абсолютно все символы, которые находятся внутри кавычек, БЕЗ ИСКЛЮЧЕНИЙ. Это означает, что пробелы, знаки препинания, включая точку в конце, если она есть, и любые другие символы должны быть сохранены.
          3. Используй ИЗВЛЕЧЕННЫЙ ТЕКСТ БЕЗ ИЗМЕНЕНИЙ как значение для "entity_name".
          4. НИКАКОГО приведения к начальной форме, удаления пробелов, знаков препинания или любых других модификаций для текста в кавычках не допускается.  Точка в конце названия (если она есть в кавычках) - это ЧАСТЬ НАЗВАНИЯ, и ее удалять НЕЛЬЗЯ.

          **Если в запросе НЕТ кавычек:**

          Старайся выделить полное название основной сущности (раздела), о которой идет речь в запросе, и обязательно приведи ее к начальной форме (именительный падеж, единственное число).  Даже если в запросе сущность указана в другой падежной форме (например, "рецепта", "дерева"), в "entity_name" должно быть название сущности именно в начальной форме.  Старайся выделить наиболее полное и точное название сущности, даже если оно состоит из нескольких слов.

          Формат ответа:
          {{
            "decision": "children_needed" / "parents_needed" / "parent_decomposition_needed",
            "entity_name": "название сущности (в начальной форме или как в кавычках)"
          }}

          **Примеры:**

          Пример 1:
          Запрос: "Найди дочерние элементы дерева"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "дерево"
          }}

          Пример 2:
          Запрос: "Какие сущности входят в состав Солнечной системы?"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "Солнечная система"
          }}

          Пример 3:
          Запрос: "В какую декомпозицию входит раздел 'Кулинария'?"
          Ответ:
          {{
            "decision": "parent_decomposition_needed",
            "entity_name": "Кулинария"
          }}

          Пример 4:
          Запрос: "Кто родители дерева?"
          Ответ:
          {{
            "decision": "parents_needed",
            "entity_name": "дерево"
          }}

          Пример 5:
          Запрос: "Из каких компонентов состоит рецепт?"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "рецепт"
          }}

          Пример 6:
          Запрос: "Какие элементы включает рецепт?"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "рецепт"
          }}

          Пример 7:
          Запрос: "Подразделы рецепта?"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "рецепт"
          }}

          Пример 8:
          Запрос: "Составные части компьютера"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "компьютер"
          }}

          Пример 9:
          Запрос: "Компоненты автомобиля"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "автомобиль"
          }}

          Пример 10:
          Запрос: "Элементы атомного ядра"
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "атомное ядро"
          }}

          Пример 11:  **<-- Новый пример с длинным названием в кавычках**
          Запрос: "В какую декомпозицию входит раздел 'Раздел. Общие сведения о предметной области'?"
          Ответ:
          {{
            "decision": "parent_decomposition_needed",
            "entity_name": "Раздел. Общие сведения о предметной области"
          }}

          Пример 12:  **<-- Еще один новый пример**
          Запрос: "Найди дочерние элементы для 'Объект. Сложная иерархическая структура данных' "
          Ответ:
          {{
            "decision": "children_needed",
            "entity_name": "Объект. Сложная иерархическая структура данных"
          }}

          Твой ответ должен быть по структуре на указанный формат, но **НЕ НАДО УКАЗЫВАТЬ В ОТВЕТЕ ```json**.
          Если термин **ЗАДАН В ЛЮБЫХ КАВЫЧКАХ, ЕГО МЕНЯТЬ НЕ НАДО. ОН ДОЛЖЕН БЫТЬ ТАК.**
        """

        agent_answer = get_together_ai_response(api_key, area_description_prompt).strip()

        self.logger.info(f"JSON ответ решения от LLM: {agent_answer}")
        
        try:
            import json
            decision_response_json = json.loads(agent_answer)
            decision = decision_response_json.get("decision")
            entity_name = decision_response_json.get("entity_name", "") 
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка разбора JSON ответа LLM: {agent_answer}")
            decision = "general_query" 
            entity_name = "" 
            finish_action_with_status(action_node, False)
            return ScResult.ERROR

        if decision == "children_needed":
            self.logger.info(f"LLM решил вызвать агента для поиска дочерних сущностей. Сущность: '{entity_name}'")

            result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_INCLUDED_CHILDREN)

            answer_prompt = f"""
                    Сущность: "{entity_name}"
                    Дочерние сущности: {result_string}

                    **Правила обработки списка `result_string`:**

                    * **Разделитель: ТОЛЬКО ";".**
                    * **Нет ";" -  `result_string` цельная сущность (или пустая).**
                    * **Есть ";" - разделить на сущности ИСКЛЮЧИТЕЛЬНО по ";".**

                    **Формат ответа:**

                    Вывести:
                    1. "Сущность: {entity_name}"
                    2. "Дочерние сущности:"
                    3. Список дочерних сущностей в столбик (из `result_string` по правилам выше).

                    **Примеры:**

                    Пример 1:
                    `entity_name`: "дерево", `result_string`: "корень;ствол;ветви;листья"
                    Вывод:
                    Сущность: дерево
                    Дочерние сущности:
                    - корень
                    - ствол
                    - ветви
                    - листья

                    Пример 2:
                    `entity_name`: "книга", `result_string`: "Глава 1. Введение"
                    Вывод:
                    Сущность: книга
                    Дочерние сущности:
                    - Глава 1. Введение

                    Пример 3:
                    `entity_name`: "дом", `result_string`: ""
                    Вывод:
                    Сущность: дом
                    Дочерние сущности:
                    - (пусто)
                    """
            
            answer_response = get_together_ai_response(api_key, answer_prompt).strip()
            print(answer_response)
            return True

        elif decision == "parents_needed":
            self.logger.info(f"LLM решил вызвать агента для поиска родительских сущностей. Сущность: '{entity_name}'")

            result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_INCLUDED_IN_PARENTS)

            answer_prompt = f"""
                    Сущность: "{entity_name}"
                    Родительские сущности: {result_string}

                    **Правила обработки списка `result_string`:**

                    * **Разделитель: ТОЛЬКО ";".**
                    * **Нет ";" -  `result_string` цельная сущность (или пустая).**
                    * **Есть ";" - разделить на сущности ИСКЛЮЧИТЕЛЬНО по ";".**

                    **Формат ответа:**

                    Вывести:
                    1. "Сущность: {entity_name}"
                    2. "Родительские сущности:"
                    3. Список родительских сущностей в столбик (из `result_string` по правилам выше).

                    **Примеры:**

                    Пример 1:
                    `entity_name`: "рецепт", `result_string`: "кулинария;еда;процесс приготовления"
                    Вывод:
                    Сущность: рецепт
                    Родительские сущности:
                    - кулинария
                    - еда
                    - процесс приготовления

                    Пример 2:
                    `entity_name`: "объект", `result_string`: "Раздел. Предметная область функционального описания рецептов"
                    Вывод:
                    Сущность: объект
                    Родительские сущности:
                    - Раздел. Предметная область функционального описания рецептов

                    Пример 3:
                    `entity_name`: "объект", `result_string`: ""
                    Вывод:
                    Сущность: объект
                    Родительские сущности:
                    - (пусто)
                    """
            answer_response = get_together_ai_response(api_key, answer_prompt).strip()
            print(answer_response)
            return True

        elif decision == "parent_decomposition_needed":
            self.logger.info(f"LLM решил вызвать агента для поиска родительских декомпозиций. Сущность: '{entity_name}'")

            result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_PARENT_DECOMPOSITION)

            answer_prompt = f"""
                    Раздел: "{entity_name}"
                    Входит в декомпозиции: {result_string}

                    **Правила обработки списка `result_string`:**

                    * **Разделитель: ТОЛЬКО ";".**
                    * **Нет ";" -  `result_string` цельная декомпозиция (или пусто).**
                    * **Есть ";" - разделить на декомпозиции ИСКЛЮЧИТЕЛЬНО по ";".**

                    **Формат ответа:**

                    Вывести:
                    1. "Раздел: {entity_name}"
                    2. "Входит в декомпозиции:"
                    3. Список декомпозиций, в которые входит раздел, в столбик (из `result_string` по правилам выше).

                    **Примеры:**

                    Пример 1:
                    `entity_name`: "Рецепты супов", `result_string`: "Кулинария;Раздел рецептов"
                    Вывод:
                    Раздел: Рецепты супов
                    Входит в декомпозиции:
                    - Кулинария
                    - Раздел рецептов

                    Пример 2:
                    `entity_name`: "Раздел. Физика", `result_string`: "Наука"
                    Вывод:
                    Раздел: Раздел. Физика
                    Входит в декомпозиции:
                    - Наука

                    Пример 3:
                    `entity_name`: "Рецепты салатов", `result_string`: ""
                    Вывод:
                    Раздел: Рецепты салатов
                    Входит в декомпозиции:
                    - (пусто)
                    """
            
            answer_response = get_together_ai_response(api_key, answer_prompt).strip()
            print(answer_response)
            return True
        else:
            print(f"""Предметная область: Структура и Иерархия.
                      ОШИБКА: Никакой агент не был вызван.
                  """)
            return False
        
    def description_and_characteristics(self, action_node, link_query, api_key):
        area_description_prompt = f"""
          Запрос пользователя: {link_query}

          Ты - система обработки запросов, которая классифицирует входящие запросы и извлекает из них название сущности, если это необходимо.  Твоя задача - обрабатывать запросы, относящиеся к предметной области "Описание и Характеристики".

          Предметная область "Описание и Характеристики":

          Эта область включает запросы на получение описания, определения сущности. Агенты этой области предоставляют информацию о сущности, отвечая на вопросы 'что это такое?'. Агенты этой области нацелены на предоставление определений, описаний и ключевых характеристик запрашиваемой сущности.

          Типы запросов для предметной области "Описание и Характеристики":

          1. "description_needed": запрос на описание сущности или запрос определения сущности.
              Примеры запросов: "дай описание рецепта", "что такое слон?", "описание для 'Сущность с точкой.' пожалуйста", "охарактеризуйте компьютер", "расскажите о Солнечной системе", "дефиниция понятия 'информационная система'".
              Ключевые слова и фразы-индикаторы: "описание", "что такое", "что из себя представляет", "охарактеризуйте", "расскажите о", "дефиниция", "определите", "дать определение".

          Извлечение сущности - КЛЮЧЕВОЕ ПРАВИЛО для предметной области "Описание и Характеристики":

          Если тип запроса "description_needed":

          **Абсолютный приоритет - текст в кавычках (").  Если в запросе ЕСТЬ текст в кавычках:**

          **ВНИМАНИЕ! ИЗВЛЕКАЙТЕ ВЕСЬ ТЕКСТ В КАВЫЧКАХ ПОЛНОСТЬЮ, ВКЛЮЧАЯ ПЕРВОЕ СЛОВО "Раздел.", "Объект.", "Сущность." и т.д., ЕСЛИ ОНО ЕСТЬ В КАВЫЧКАХ!**

          1. Извлеки **АБСОЛЮТНО ВЕСЬ** текст **НАЧИНАЯ С ПЕРВОЙ КАВЫЧКИ И ЗАКАНЧИВАЯ ПОСЛЕДНЕЙ**.
          2. Включай в извлеченный текст абсолютно все символы, которые находятся внутри кавычек, БЕЗ ИСКЛЮЧЕНИЙ. Это означает, что пробелы, знаки препинания, включая точку в конце, если она есть, и любые другие символы должны быть сохранены.
          3. Используй ИЗВЛЕЧЕННЫЙ ТЕКСТ БЕЗ ИЗМЕНЕНИЙ как значение для "entity_name".
          4. НИКАКОГО приведения к начальной форме, удаления пробелов, знаков препинания или любых других модификаций для текста в кавычках не допускается.  Точка в конце названия (если она есть в кавычках) - это ЧАСТЬ НАЗВАНИЯ, и ее удалять НЕЛЬЗЯ.

          **Если в запросе НЕТ кавычек:**

          Старайся выделить полное название основной сущности (раздела), о которой идет речь в запросе, и обязательно приведи ее к начальной форме (именительный падеж, единственное число).  Даже если в запросе сущность указана в другой падежной форме (например, "рецепта", "дерева"), в "entity_name" должно быть название сущности именно в начальной форме.  Старайся выделить наиболее полное и точное название сущности, даже если оно состоит из нескольких слов.

          Формат ответа:
          {{
            "decision": "description_needed",
            "entity_name": "название сущности (в начальной форме или как в кавычках)"
          }}

          **Примеры:**

          Пример 1:
          Запрос: "Дай описание рецепта"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "рецепт"
          }}

          Пример 2:
          Запрос: "Что такое слон?"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "слон"
          }}

          Пример 3:
          Запрос: "Описание для 'Сущность с точкой.' пожалуйста"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "Сущность с точкой."
          }}

          Пример 4:
          Запрос: "Охарактеризуйте компьютер"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "компьютер"
          }}

          Пример 5:
          Запрос: "Расскажите о Солнечной системе"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "Солнечная система"
          }}

          Пример 6:
          Запрос: "Дефиниция понятия 'информационная система'"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "информационная система"
          }}

          Пример 7:  **<-- Новый пример с длинным названием в кавычках**
          Запрос: "Дайте описание для 'Раздел.  Новый раздел с длинным названием' пожалуйста"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "Раздел.  Новый раздел с длинным названием"
          }}

          Пример 8:  **<-- Еще один новый пример**
          Запрос: "Что из себя представляет 'Объект.  Важный объект для описания'?"
          Ответ:
          {{
            "decision": "description_needed",
            "entity_name": "Объект.  Важный объект для описания"
          }}

          Твой ответ должен быть по структуре на указанный формат, но **НЕ НАДО УКАЗЫВАТЬ В ОТВЕТЕ ```json**.
          Если термин **ЗАДАН В ЛЮБЫХ КАВЫЧКАХ, ЕГО МЕНЯТЬ НЕ НАДО. ОН ДОЛЖЕН БЫТЬ ТАК.**
        """

        agent_answer = get_together_ai_response(api_key, area_description_prompt).strip()

        self.logger.info(f"JSON ответ решения от LLM: {agent_answer}")
        
        try:
            import json
            decision_response_json = json.loads(agent_answer)
            decision = decision_response_json.get("decision")
            entity_name = decision_response_json.get("entity_name", "") 
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка разбора JSON ответа LLM: {agent_answer}")
            decision = "general_query" 
            entity_name = "" 
            finish_action_with_status(action_node, False)
            return ScResult.ERROR
        
        if decision == "description_needed":
            self.logger.info(f"LLM решил вызвать агента для описания сущности. Сущность: '{entity_name}'")

            node = self.find_entity_by_name(entity_name, action_node)
            
            find_description_action, find_description_result = execute_agent(
                {
                    node: False,
                },
                [
                    CommonIdentifiers.ACTION,
                    SearchModuleIdentifiers.ACTION_FIND_DESCRIPTION,
                ]
            )

            if not find_description_result:
                self.logger.error("Не найдено описание узла: '{}'" @ entity_name)
                finish_action_with_status(action_node, False)
                return ScResult.ERROR
            
            find_description_action_result = ScStructure(set_node=get_action_result(find_description_action))
            info_link = next(iter(find_description_action_result))

            answer = get_link_content_data(info_link)

            answer_prompt = f"""Можешь очистить полученный ответ от HTML тегов и вывести финальный ответ для польователя. Ответ, который нужно очистить: {answer}"""

            answer_response = get_together_ai_response(api_key, answer_prompt).strip()
            print(answer_response)
            return True
        else:
          print(f"""Предметная область: Структура и Иерархия.
                    ОШИБКА: Никакой агент не был вызван.
                """)
          return False
        
    def classification_and_categorization(self, action_node, link_query, api_key):
      area_description_prompt = f"""
          Запрос пользователя: {link_query}

          Ты - система обработки запросов, которая классифицирует входящие запросы и извлекает из них название сущности, если это необходимо.  Твоя задача - обрабатывать запросы, относящиеся к предметной области "Классификация и Категоризация".

          Предметная область "Классификация и Категоризация":

          Эта область включает запросы, которые помогают классифицировать сущности, определяя их принадлежность к различным категориям. Агенты этой области могут определить как самый широкий класс (максимальный класс), так и более узкие или общие классы (не максимальный класс) для заданной сущности.  Запросы в этой области направлены на определение места сущности в системе классов и категорий.

          Типы запросов для предметной области "Классификация и Категоризация":

          1. "max_class_needed": запрос на определение **максимального класса или категории**, к которой принадлежит сущность.  Максимальный класс - это наиболее общая и широкая категория, включающая данную сущность.
              Примеры запросов: "какой максимальный класс объектов исследования у слона?", "какие элементы являются максимальными классами у 'рецепт борща'?", "высшая категория для автомобиля", "самый общий класс для понятия 'информационная система'".
              Ключевые слова и фразы-индикаторы: "максимальный класс", "высшая категория", "класс", "категория", "самый общий класс", "верхний уровень классификации", "к какому классу относится".

          2. "not_max_class_needed": запрос на определение **немаксимального класса или категории**, к которой принадлежит сущность, или **более общих классов**, но не самых общих (максимальных).  Это могут быть промежуточные или просто более широкие категории, чем рассматриваемая сущность, но не являющиеся самыми общими.
              Примеры запросов: "какой не максимальный класс у слона?", "назови более общий класс для 'рецепт борща'", "не высшая категория для рецепта", "какой класс более общий чем 'компьютер'", "промежуточная категория для 'Солнечная система'".
              Ключевые слова и фразы-индикаторы: "не максимальный класс", "не высшая категория", "не класс", "не категория", "более общий класс", "подкласс", "промежуточная категория", "менее общий класс".

          Извлечение сущности - КЛЮЧЕВОЕ ПРАВИЛО для предметной области "Классификация и Категоризация":

          Если тип запроса "max_class_needed" или "not_max_class_needed":

          **Абсолютный приоритет - текст в кавычках (").  Если в запросе ЕСТЬ текст в кавычках:**

          **ВНИМАНИЕ! ИЗВЛЕКАЙТЕ ВЕСЬ ТЕКСТ В КАВЫЧКАХ ПОЛНОСТЬЮ, ВКЛЮЧАЯ ПЕРВОЕ СЛОВО "Раздел.", "Объект.", "Сущность." и т.д., ЕСЛИ ОНО ЕСТЬ В КАВЫЧКАХ!**

          1. Извлеки **АБСОЛЮТНО ВЕСЬ** текст **НАЧИНАЯ С ПЕРВОЙ КАВЫЧКИ И ЗАКАНЧИВАЯ ПОСЛЕДНЕЙ**.
          2. Включай в извлеченный текст абсолютно все символы, которые находятся внутри кавычек, БЕЗ ИСКЛЮЧЕНИЙ. Это означает, что пробелы, знаки препинания, включая точку в конце, если она есть, и любые другие символы должны быть сохранены.
          3. Используй ИЗВЛЕЧЕННЫЙ ТЕКСТ БЕЗ ИЗМЕНЕНИЙ как значение для "entity_name".
          4. НИКАКОГО приведения к начальной форме, удаления пробелов, знаков препинания или любых других модификаций для текста в кавычках не допускается.  Точка в конце названия (если она есть в кавычках) - это ЧАСТЬ НАЗВАНИЯ, и ее удалять НЕЛЬЗЯ.

          **Если в запросе НЕТ кавычек:**

          Старайся выделить полное название основной сущности (раздела), о которой идет речь в запросе, и обязательно приведи ее к начальной форме (именительный падеж, единственное число).  Даже если в запросе сущность указана в другой падежной форме (например, "рецепта", "дерева"), в "entity_name" должно быть название сущности именно в начальной форме.  Старайся выделить наиболее полное и точное название сущности, даже если оно состоит из нескольких слов.

          Формат ответа:
          {{
            "decision": "max_class_needed" / "not_max_class_needed",
            "entity_name": "название сущности (в начальной форме или как в кавычках)"
          }}

          **Примеры:**

          Пример 1:
          Запрос: "Какой максимальный класс объектов исследования у слона?"
          Ответ:
          {{
            "decision": "max_class_needed",
            "entity_name": "слон"
          }}

          Пример 2:
          Запрос: "Какие элементы являются максимальными классами у 'рецепт борща'?"
          Ответ:
          {{
            "decision": "max_class_needed",
            "entity_name": "рецепт борща"
          }}

          Пример 3:
          Запрос: "Какой не максимальный класс у слона?"
          Ответ:
          {{
            "decision": "not_max_class_needed",
            "entity_name": "слон"
          }}

          Пример 4:
          Запрос: "Назови более общий класс для 'рецепт борща'"
          Ответ:
          {{
            "decision": "not_max_class_needed",
            "entity_name": "рецепт борща"
          }}

          Пример 5:
          Запрос: "К какой категории относится рецепт?"
          Ответ:
          {{
            "decision": "max_class_needed",
            "entity_name": "рецепт"
          }}

          Пример 6:
          Запрос: "Класс автомобиля"
          Ответ:
          {{
            "decision": "max_class_needed",
            "entity_name": "автомобиль"
          }}

          Пример 7:  **<-- Новый пример с длинным названием в кавычках**
          Запрос: "Какой максимальный класс для 'Раздел.  Очень важный раздел для классификации'?"
          Ответ:
          {{
            "decision": "max_class_needed",
            "entity_name": "Раздел.  Очень важный раздел для классификации"
          }}

          Пример 8:  **<-- Еще один новый пример**
          Запрос: "Назови не максимальный класс для 'Объект.  Сложный объект классификации' "
          Ответ:
          {{
            "decision": "not_max_class_needed",
            "entity_name": "Объект.  Сложный объект классификации"
          }}

          Твой ответ должен быть по структуре на указанный формат, но **НЕ НАДО УКАЗЫВАТЬ В ОТВЕТЕ ```json**.
          Если термин **ЗАДАН В ЛЮБЫХ КАВЫЧКАХ, ЕГО МЕНЯТЬ НЕ НАДО. ОН ДОЛЖЕН БЫТЬ ТАК.**
        """
      
      agent_answer = get_together_ai_response(api_key, area_description_prompt).strip()

      self.logger.info(f"JSON ответ решения от LLM: {agent_answer}")
      
      try:
          import json
          decision_response_json = json.loads(agent_answer)
          decision = decision_response_json.get("decision")
          entity_name = decision_response_json.get("entity_name", "") 
      except json.JSONDecodeError:
          self.logger.error(f"Ошибка разбора JSON ответа LLM: {agent_answer}")
          decision = "general_query" 
          entity_name = "" 
          finish_action_with_status(action_node, False)
          return ScResult.ERROR
      
      if decision == "max_class_needed":
          self.logger.info(f"LLM решил вызвать агента для поиска максимального класса объектов исследования. Сущность: '{entity_name}'")

          result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_MAX_CLASS)

          answer_prompt = f"""
                  Сущность: "{entity_name}"
                  Максимальный класс: {result_string}

                  **Правила обработки списка `result_string`:**

                  * **Разделитель: ТОЛЬКО ";".**
                  * **Нет ";" -  `result_string` цельный максимальный класс (или пусто).**
                  * **Есть ";" - разделить на максимальные классы ИСКЛЮЧИТЕЛЬНО по ";".**

                  **Формат ответа:**

                  Вывести:
                  1. "Сущность: {entity_name}"
                  2. "Максимальный класс:"
                  3. Список максимальных классов в столбик (из `result_string` по правилам выше).

                  **Примеры:**

                  Пример 1:
                  `entity_name`: "слон", `result_string`: "Животные;Млекопитающие"
                  Вывод:
                  Сущность: слон
                  Максимальный класс:
                  - Животные
                  - Млекопитающие

                  Пример 2:
                  `entity_name`: "рецепт борща", `result_string`: "Рецепты"
                  Вывод:
                  Сущность: рецепт борща
                  Максимальный класс:
                  - Рецепты

                  Пример 3:
                  `entity_name`: "калькулятор", `result_string`: ""
                  Вывод:
                  Сущность: калькулятор
                  Максимальный класс:
                  - (пусто)
                  """
          
          answer_response = get_together_ai_response(api_key, answer_prompt).strip()

          print(answer_response)
          return True
      elif decision == "not_max_class_needed":
          self.logger.info(f"LLM решил вызвать агента для поиска немаксимального класса объектов исследования. Сущность: '{entity_name}'")

          result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_NOT_MAX_CLASS)

          answer_prompt = f"""
                  Сущность: "{entity_name}"
                  Более общий класс: {result_string}

                  **Правила обработки списка `result_string`:**

                  * **Разделитель: ТОЛЬКО ";".**
                  * **Нет ";" -  `result_string` цельный более общий класс (или пусто).**
                  * **Есть ";" - разделить на более общие классы ИСКЛЮЧИТЕЛЬНО по ";".**

                  **Формат ответа:**

                  Вывести:
                  1. "Сущность: {entity_name}"
                  2. "Более общий класс:"
                  3. Список более общих классов в столбик (из `result_string` по правилам выше).

                  **Примеры:**

                  Пример 1:
                  `entity_name`: "слон", `result_string`: "Млекопитающие;Животные"
                  Вывод:
                  Сущность: слон
                  Более общий класс:
                  - Млекопитающие
                  - Животные

                  Пример 2:
                  `entity_name`: "рецепт борща", `result_string`: "Блюда"
                  Вывод:
                  Сущность: рецепт борща
                  Более общий класс:
                  - Блюда

                  Пример 3:
                  `entity_name`: "калькулятор", `result_string`: ""
                  Вывод:
                  Сущность: калькулятор
                  Более общий класс:
                  - (пусто)
                  """
          
          answer_response = get_together_ai_response(api_key, answer_prompt).strip()

          print(answer_response)
          return True
      else:
          print(f"""Предметная область: Структура и Иерархия.
                    ОШИБКА: Никакой агент не был вызван.
                """)
          return False
      
    def semantic_relationships_and_knowledge(self, action_node, link_query, api_key):
        area_description_prompt = f"""
          Запрос пользователя: {link_query}

          Ты - система обработки запросов, которая классифицирует входящие запросы и извлекает из них название сущности, если это необходимо.  Твоя задача - обрабатывать запросы, относящиеся к предметной области "Семантические Связи и Знания".

          Предметная область "Семантические Связи и Знания":

          Эта область включает запросы, которые извлекают ключевую информацию и связи, связанные с сущностью. Агенты этой области ищут важные семантические элементы, аспекты знания и концепции, которые раскрывают сущность с разных сторон.  Запросы в этой области направлены на выявление значимых связей, характеристик и знаний, ассоциированных с сущностью.

          Типы запросов для предметной области "Семантические Связи и Знания":

          1. "key_sc_element_needed": запрос на поиск **ключевых SC-элементов (семантических элементов или элементов знания)**, связанных с сущностью.  SC-элементы представляют собой важные аспекты, характеристики, свойства или концепции, которые описывают сущность и ее место в общей системе знаний.
              Примеры запросов: "какие ключевые элементы рецепта?", "найди важные SC-элементы для 'Солнечная система'", "основные знания о дереве", "важные аспекты компьютера", "ключевые характеристики информационной системы", "семантические связи понятия 'рецепт борща'".
              Ключевые слова и фразы-индикаторы: "ключевые элементы", "важные элементы", "основные элементы знания", "SC-элементы", "семантические элементы", "аспекты знания", "ключевые характеристики", "важные аспекты", "семантические связи", "знания о".

          Извлечение сущности - КЛЮЧЕВОЕ ПРАВИЛО для предметной области "Семантические Связи и Знания":

          Если тип запроса "key_sc_element_needed":

          **Абсолютный приоритет - текст в кавычках (").  Если в запросе ЕСТЬ текст в кавычках:**

          **ВНИМАНИЕ! ИЗВЛЕКАЙТЕ ВЕСЬ ТЕКСТ В КАВЫЧКАХ ПОЛНОСТЬЮ, ВКЛЮЧАЯ ПЕРВОЕ СЛОВО "Раздел.", "Объект.", "Сущность." и т.д., ЕСЛИ ОНО ЕСТЬ В КАВЫЧКАХ!**

          1. Извлеки **АБСОЛЮТНО ВЕСЬ** текст **НАЧИНАЯ С ПЕРВОЙ КАВЫЧКИ И ЗАКАНЧИВАЯ ПОСЛЕДНЕЙ**.
          2. Включай в извлеченный текст абсолютно все символы, которые находятся внутри кавычек, БЕЗ ИСКЛЮЧЕНИЙ. Это означает, что пробелы, знаки препинания, включая точку в конце, если она есть, и любые другие символы должны быть сохранены.
          3. Используй ИЗВЛЕЧЕННЫЙ ТЕКСТ БЕЗ ИЗМЕНЕНИЙ как значение для "entity_name".
          4. НИКАКОГО приведения к начальной форме, удаления пробелов, знаков препинания или любых других модификаций для текста в кавычках не допускается.  Точка в конце названия (если она есть в кавычках) - это ЧАСТЬ НАЗВАНИЯ, и ее удалять НЕЛЬЗЯ.

          **Если в запросе НЕТ кавычек:**

          Старайся выделить полное название основной сущности (раздела), о которой идет речь в запросе, и обязательно приведи ее к начальной форме (именительный падеж, единственное число).  Даже если в запросе сущность указана в другой падежной форме (например, "рецепта", "дерева"), в "entity_name" должно быть название сущности именно в начальной форме.  Старайся выделить наиболее полное и точное название сущности, даже если оно состоит из нескольких слов.

          Формат ответа:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "название сущности (в начальной форме или как в кавычках)"
          }}

          **Примеры:**

          Пример 1:
          Запрос: "Какие ключевые элементы рецепта?"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "рецепт"
          }}

          Пример 2:
          Запрос: "Найди важные SC-элементы для 'Солнечная система'"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "Солнечная система"
          }}

          Пример 3:
          Запрос: "Основные знания о дереве"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "дерево"
          }}

          Пример 4:
          Запрос: "Важные аспекты компьютера"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "компьютер"
          }}

          Пример 5:
          Запрос: "Ключевые характеристики информационной системы"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "информационная система"
          }}

          Пример 6:
          Запрос: "Семантические связи понятия 'рецепт борща'"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "рецепт борща"
          }}

          Пример 7:  **<-- Новый пример с длинным названием в кавычках**
          Запрос: "Найди ключевые SC-элементы для 'Раздел. Машина обработки знаний подсистемы поддержки проектирования sc-агентов'"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "Раздел. Машина обработки знаний подсистемы поддержки проектирования sc-агентов"
          }}

          Пример 8:  **<-- Еще один новый пример**
          Запрос: "Какие важные элементы знаний есть у 'Объект. Сложная программная система'?"
          Ответ:
          {{
            "decision": "key_sc_element_needed",
            "entity_name": "Объект. Сложная программная система"
          }}

          Твой ответ должен быть по структуре на указанный формат, но **НЕ НАДО УКАЗЫВАТЬ В ОТВЕТЕ ```json**.
          Если термин **ЗАДАН В ЛЮБЫХ КАВЫЧКАХ, ЕГО МЕНЯТЬ НЕ НАДО. ОН ДОЛЖЕН БЫТЬ ТАК.**
        """

        agent_answer = get_together_ai_response(api_key, area_description_prompt).strip()

        self.logger.info(f"JSON ответ решения от LLM: {agent_answer}")
        
        try:
            import json
            decision_response_json = json.loads(agent_answer)
            decision = decision_response_json.get("decision")
            entity_name = decision_response_json.get("entity_name", "") 
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка разбора JSON ответа LLM: {agent_answer}")
            decision = "general_query" 
            entity_name = "" 
            finish_action_with_status(action_node, False)
            return ScResult.ERROR
        
        if decision == "key_sc_element_needed":
            self.logger.info(f"LLM решил вызвать агента для поиска ключевых sc-элементов. Сущность: '{entity_name}'")

            result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_KEY_SC_ELEMENT)

            answer_prompt = f"""
                    Сущность: "{entity_name}"
                    Ключевые SC-элементы: {result_string}

                    **Правила обработки списка `result_string`:**

                    * **Разделитель: ТОЛЬКО ";".**
                    * **Нет ";" -  `result_string` цельный ключевой SC-элемент (или пусто).**
                    * **Есть ";" - разделить на ключевые SC-элементы ИСКЛЮЧИТЕЛЬНО по ";".**

                    **Формат ответа:**

                    Вывести:
                    1. "Сущность: {entity_name}"
                    2. "Ключевые SC-элементы:"
                    3. Список ключевых SC-элементов в столбик (из `result_string` по правилам выше).

                    **Примеры:**

                    Пример 1:
                    `entity_name`: "рецепт", `result_string`: "Ингредиенты;Шаги приготовления;Время приготовления"
                    Вывод:
                    Сущность: рецепт
                    Ключевые SC-элементы:
                    - Ингредиенты
                    - Шаги приготовления
                    - Время приготовления

                    Пример 2:
                    `entity_name`: "Солнечная система", `result_string`: "Солнце;Планеты"
                    Вывод:
                    Сущность: Солнечная система
                    Ключевые SC-элементы:
                    - Солнце
                    - Планеты

                    Пример 3:
                    `entity_name`: "калькулятор", `result_string`: ""
                    Вывод:
                    Сущность: калькулятор
                    Ключевые SC-элементы:
                    - (пусто)
                    """
            
            answer_response = get_together_ai_response(api_key, answer_prompt).strip()

            print(answer_response)
            return True
        else:
          print(f"""Предметная область: Структура и Иерархия.
                  ОШИБКА: Никакой агент не был вызван.
              """)
          return False
        
    def general_questions(self, link_query, api_key):
        area_description_prompt = f"""
          Запрос пользователя: {link_query}

          Ты — Система Информационной Поддержки сотрудников.  Это общий запрос, не требующий поиска в базе знаний.

          Ответь на вопрос пользователя, используя свои собственные знания.

          Дай прямой ответ в виде обычного текста.
          """
        
        agent_answer = get_together_ai_response(api_key, area_description_prompt).strip()
        print(agent_answer)
        return True
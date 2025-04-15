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
        
        # --- Логика принятия решений с извлечением сущности ---
        decision_prompt = f"""
        Запрос пользователя: {link_query}

        Проанализируй запрос. Определи тип запроса:

        1. "children_needed":  запрос о дочерних элементах или сущностях, входящих в состав другой сущности (например, "дочерние элементы", "входят в", "состоит из").
        2. "description_needed": запрос на описание сущности ("описание", "что такое", "что из себя представляет").
        3. "parents_needed": запрос о родительских элементах или сущностях, частью которых является данная сущность (например, "родители", "является частью", "включает в себя").
        4. "parent_decomposition_needed": запрос о том, **В КАКИЕ ДЕКОМПОЗИЦИИ ВХОДИТ раздел** или частью какой декомпозиции является раздел (т.е., **ПОИСК РОДИТЕЛЬСКОЙ ДЕКОМПОЗИЦИИ**).  Например, "входит в декомпозицию", "в какой декомпозиции", "является частью декомпозиции", "в составе какой декомпозиции", "к какой декомпозиции принадлежит").
        5. "max_class_needed": запрос на определение **максимального класса или категории**, к которой принадлежит сущность (например, "максимальный класс объектов исследования", "высшая категория", "класс", "категория").
        6. "not_max_class_needed": запрос на определение **немаксимального класса или категории**, к которой принадлежит сущность, или **более общих классов** (например, "не максимальный класс", "не высшая категория", "не класс", "не категория", "более общий класс", "подкласс").
        7. "key_sc_element_needed": запрос на поиск **ключевых SC-элементов (семантических элементов или элементов знания)**, связанных с сущностью (например, "ключевые элементы", "важные элементы", "основные элементы знания", "SC-элементы").
        8. "general_query":  все остальные запросы, не относящиеся к поиску дочерних элементов, родительских элементов, описанию сущности, **родительской декомпозиции**, максимального класса, немаксимального класса или ключевых SC-элементов.

        **Извлечение сущности - КЛЮЧЕВОЕ ПРАВИЛО:**

        Если тип запроса "children_needed", "description_needed", "parents_needed", "parent_decomposition_needed", "max_class_needed", "not_max_class_needed" или "key_sc_element_needed":

        **Абсолютный приоритет - текст в кавычках (").  Если в запросе ЕСТЬ текст в кавычках:**

        1. **Извлеки ВЕСЬ текст В ТОЧНОСТИ между открывающей и закрывающей кавычками.**
        2. **Включай в извлеченный текст абсолютно все символы, которые находятся внутри кавычек, БЕЗ ИСКЛЮЧЕНИЙ.** Это означает, что пробелы, знаки препинания, **включая точку в конце, если она есть**, и любые другие символы должны быть сохранены.
        3. **Используй ИЗВЛЕЧЕННЫЙ ТЕКСТ БЕЗ ИЗМЕНЕНИЙ как значение для "entity_name".**
        4. **НИКАКОГО приведения к начальной форме, удаления пробелов, знаков препинания или любых других модификаций для текста в кавычках не допускается.**  **Точка в конце названия (если она есть в кавычках) - это ЧАСТЬ НАЗВАНИЯ, и ее удалять НЕЛЬЗЯ.**

        **Если в запросе НЕТ кавычек:**

        Старайся выделить **полное название основной сущности (раздела)**, о которой идет речь в запросе, **и обязательно приведи ее к начальной форме (именительный падеж, единственное число)**.  **Даже если в запросе сущность указана в другой падежной форме (например, "рецепта", "дерева"), в "entity_name" должно быть название сущности именно в начальной форме.**  **Старайся выделить наиболее полное и точное название сущности, даже если оно состоит из нескольких слов.**

        Иначе (если тип запроса "general_query") поле "entity_name" оставь пустым.

        Формат ответа:
        {{
          "decision": "children_needed" / "description_needed" / "parents_needed" / "parent_decomposition_needed" / "max_class_needed" / "not_max_class_needed" / "key_sc_element_needed" / "general_query",
          "entity_name": "название сущности (в начальной форме)" / ""
        }}

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
        Запрос: "Дай описание рецепта"
        Ответ:
        {{
          "decision": "description_needed",
          "entity_name": "рецепт"
        }}

        Пример 4:
        Запрос: "Что такое слон?"
        Ответ:
        {{
          "decision": "description_needed",
          "entity_name": "слон"
        }}

        Пример 5:
        Запрос: "Сколько будет 2 + 2?"
        Ответ:
        {{
          "decision": "general_query",
          "entity_name": ""
        }}

        Пример 6:
        Запрос: "Рецепты вкусных блюд"
        Ответ:
        {{
          "decision": "general_query",
          "entity_name": ""
        }}

        Пример 7:
        Запрос: "Дочерние элементы рецептурного объекта"
        Ответ:
        {{
          "decision": "children_needed",
          "entity_name": "рецептурный объект"
        }}

        Пример 8:
        Запрос: "Кто родители дерева?"
        Ответ:
        {{
          "decision": "parents_needed",
          "entity_name": "дерево"
        }}

        Пример 9:
        Запрос: "Частью чего является Солнечная система?"
        Ответ:
        {{
          "decision": "parents_needed",
          "entity_name": "Солнечная система"
        }}

        Пример 10:
        Запрос: "В какую декомпозицию входит раздел 'Кулинария'?"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Кулинария"
        }}

        Пример 11:
        Запрос: "Раздел 'Рецепты' является частью какой декомпозиции?"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Рецепты"
        }}

        Пример 12:
        Запрос: "В какой декомпозиции находится 'Раздел. Предметная область процессных моделей рецептурных производств'?"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Раздел. Предметная область процессных моделей рецептурных производств"
        }}

        Пример 13:
        Запрос: "Найди родительские элементы рецепта"
        Ответ:
        {{
          "decision": "parents_needed",
          "entity_name": "рецепт"
        }}

        Пример 14:
        Запрос: "Какой максимальный класс объектов исследования у слона?"
        Ответ:
        {{
          "decision": "max_class_needed",
          "entity_name": "слон"
        }}

        Пример 15:
        Запрос: "Какие элементы являются максимальными классами у 'рецепт борща'?"
        Ответ:
        {{
          "decision": "max_class_needed",
          "entity_name": "рецепт борща"
        }}

        Пример 16:
        Запрос: "Какой не максимальный класс у слона?"
        Ответ:
        {{
          "decision": "not_max_class_needed",
          "entity_name": "слон"
        }}

        Пример 17:
        Запрос: "Назови более общий класс для 'рецепт борща'"
        Ответ:
        {{
          "decision": "not_max_class_needed",
          "entity_name": "рецепт борща"
        }}

        Пример 18:
        Запрос: "Найди немаксимальный класс объектов исследования 'Раздел. Предметная область информационного обмена технологических рецептур.' "
        Ответ:
        {{
          "decision": "not_max_class_needed",
          "entity_name": "Раздел. Предметная область информационного обмена технологических рецептур."
        }}

        Пример 19:
        Запрос: "Описание для 'Сущность с точкой.' пожалуйста"
        Ответ:
        {{
          "decision": "description_needed",
          "entity_name": "Сущность с точкой."
        }}

        Пример 20:
        Запрос: "Какие ключевые элементы рецепта?"
        Ответ:
        {{
          "decision": "key_sc_element_needed",
          "entity_name": "рецепт"
        }}

        Пример 21:
        Запрос: "Найди важные SC-элементы для 'Солнечная система'"
        Ответ:
        {{
          "decision": "key_sc_element_needed",
          "entity_name": "Солнечная система"
        }}

        Пример 22:
        Запрос: "Какие еще есть подразделы у раздела 'Кулинария', кроме Рецептов?"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Кулинария"
        }}

        Пример 23:
        Запрос: "Декомпозиции для 'Раздел. Общие сведения о предметной области'"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Раздел. Общие сведения о предметной области"
        }}

        Пример 24:
        Запрос: "К какой декомпозиции принадлежит раздел 'Кулинария'?"
        Ответ:
        {{
          "decision": "parent_decomposition_needed",
          "entity_name": "Кулинария"
        }}


        Ответь только в формате JSON, как показано в примерах. Не ставь ```json.
        Если элемент вводится в кавычках, то передавай его полностью таким, без удаления знаков препинания и слов.
        """

        decision_response_json_str = get_together_ai_response(api_key, decision_prompt).strip()
        self.logger.info(f"JSON ответ решения от LLM: {decision_response_json_str}")
        
        try:
            import json
            decision_response_json = json.loads(decision_response_json_str)
            decision = decision_response_json.get("decision")
            entity_name = decision_response_json.get("entity_name", "") 
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка разбора JSON ответа LLM: {decision_response_json_str}")
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

        elif decision == "children_needed":
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

        elif decision == "in_decompositions_needed":
            self.logger.info(f"LLM решил вызвать агента для поиска дочерней декомпозиции. Сущность: '{entity_name}'")

            result_string = self.call_agent_get_string_result(entity_name, action_node, SearchModuleIdentifiers.ACTION_FIND_IN_DECOMPOSITIONS)

            answer_prompt = f"""
                    Раздел: "{entity_name}"
                    Декомпозиция раздела: {result_string}

                    **Правила обработки списка `result_string`:**

                    * **Разделитель: ТОЛЬКО ";".**
                    * **Нет ";" -  `result_string` цельная декомпозиция (или пусто).**
                    * **Есть ";" - разделить на декомпозиции ИСКЛЮЧИТЕЛЬНО по ";".**

                    **Формат ответа:**

                    Вывести:
                    1. "Раздел: {entity_name}"
                    2. "Декомпозиция раздела:"
                    3. Список декомпозиций, в которые входит раздел, в столбик (из `result_string` по правилам выше).

                    **Примеры:**

                    Пример 1:
                    `entity_name`: "Рецепты супов", `result_string`: "Кулинария;Раздел рецептов"
                    Вывод:
                    Раздел: Рецепты супов
                    Декомпозиция раздела:
                    - Кулинария
                    - Раздел рецептов

                    Пример 2:
                    `entity_name`: "Раздел. Физика", `result_string`: "Наука"
                    Вывод:
                    Раздел: Раздел. Физика
                    Декомпозиция раздела:
                    - Наука

                    Пример 3:
                    `entity_name`: "Рецепты салатов", `result_string`: ""
                    Вывод:
                    Раздел: Рецепты салатов
                    Декомпозиция раздела:
                    - (пусто)
                    """
            
            answer_response = get_together_ai_response(api_key, answer_prompt).strip()

            print(answer_response)

        elif decision == 'max_class_needed':
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

        elif decision == 'not_max_class_needed':
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

        elif decision == "key_sc_element_needed":
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
        
        return ScResult.OK
    
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
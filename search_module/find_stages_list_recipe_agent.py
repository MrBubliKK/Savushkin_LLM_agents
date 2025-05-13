import logging
from dataclasses import dataclass

from sc_client.models import ScAddr, ScTemplate, ScLinkContent, ScLinkContentType, ScConstruction
from sc_client.constants import sc_types, sc_type
from sc_client.client import template_search, generate_elements
from sc_kpm import ScKeynodes, ScAgentClassic, ScResult
from sc_kpm.identifiers import Idtf
from sc_kpm.sc_sets import ScSet, ScStructure
from sc_kpm.utils import get_element_system_identifier, search_element_by_non_role_relation, get_link_content_data, create_link
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    generate_action_result,
)

from .search_module_idtfs import SearchModuleIdentifiers

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="[%d-%b-%y %H:%M:%S]",
)


@dataclass(frozen=True)
class FindStagesListIdentifiers:
    PROCEDURE_STARTING_IMAGE: Idtf = "procedure_starting_image"
    STARTING_OF_PARALLEL_SEQUENCE_EXECUTION_IMAGE: Idtf = "starting_of_parallel_sequence_execution_image"
    UNIT_PROCEDURE_IMAGE: Idtf = "unit_procedure_image"
    PROCEDURE_FINISHING_IMAGE: Idtf = "procedure_finishing_image"
    ALLOCATION_ELEMENT_IMAGE: Idtf = "allocation_element_image"
    NREL_INCIDENCE: Idtf = "nrel_incidence"
    NREL_IMAGE_SIGN: Idtf = "nrel_image_sign"


class FindStagesListRecipeAgent(ScAgentClassic):
    def __init__(self):
        super().__init__(SearchModuleIdentifiers.ACTION_FIND_STAGES_LIST_RECIPE)  # Регистрируем действие

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("Agent finished: %s", "success" if is_successful else "fail")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        # 1. Получаем входной узел (для которого ищем ключевой элемент)
        input_node, = get_action_arguments(action_node, 1)
        scheme_structure = ScStructure(set_node=input_node)

        start_image_template = ScTemplate()
        start_image_template.triple(
            scheme_structure.set_node,
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            sc_types.NODE_VAR >> "start_procedure_node"
        )

        start_image_template.triple(
            ScKeynodes[FindStagesListIdentifiers.PROCEDURE_STARTING_IMAGE],
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            "start_procedure_node"
        )

        start_image_template_results = template_search(start_image_template)

        if len(start_image_template_results) > 1:
            logging.error("Слишком много точек начала процедуры.")
            return ScResult.ERROR_INVALID_PARAMS
        if len(start_image_template_results) < 1:
            logging.error("Меньше 1 параметра начала процедуры.")
            return ScResult.ERROR_INVALID_PARAMS
        
        start_image_node = start_image_template_results[0].get("start_procedure_node")

        scheme_dict = {}
        order = []
        stack = [start_image_node]
        
        while stack:
            current_node = stack.pop()

            #self.logger.info(f'(---) Process node: {get_element_system_identifier(current_node)}')
            logging.debug(f'(---) Process node: 88 {get_element_system_identifier(current_node)}')

            
            if current_node in order:
                continue

            order.append(current_node)

            next_node_template = ScTemplate()
            next_node_template.quintuple(
                current_node,
                sc_types.EDGE_D_COMMON_VAR,
                sc_types.NODE_VAR >> "connection_image_node",
                sc_types.EDGE_ACCESS_VAR_POS_PERM,
                ScKeynodes[FindStagesListIdentifiers.NREL_INCIDENCE]
            )

            next_node_template.quintuple(
                "connection_image_node",
                sc_types.EDGE_D_COMMON_VAR,
                sc_types.NODE_VAR >> "next_node",
                sc_types.EDGE_ACCESS_VAR_POS_PERM,
                ScKeynodes[FindStagesListIdentifiers.NREL_INCIDENCE]
            )

            next_node_template_results = template_search(next_node_template)
            next_nodes = [result.get("next_node") for result in next_node_template_results]
            scheme_dict[current_node] = next_nodes
            stack += next_nodes 

        result_strings = []
        for i, node in enumerate(order):
            node_string = f'{i}: '
            node_classes = get_node_classes(node)
            
            if ScKeynodes[FindStagesListIdentifiers.PROCEDURE_STARTING_IMAGE] in node_classes:
                node_string += 'Начало'
            if ScKeynodes[FindStagesListIdentifiers.STARTING_OF_PARALLEL_SEQUENCE_EXECUTION_IMAGE] in node_classes:
                node_string += 'Выбор'
            if ScKeynodes[FindStagesListIdentifiers.UNIT_PROCEDURE_IMAGE] in node_classes:
                node_string += get_idtf(node)
            if ScKeynodes[FindStagesListIdentifiers.ALLOCATION_ELEMENT_IMAGE] in node_classes:
                node_string += get_idtf(node)
            if ScKeynodes[FindStagesListIdentifiers.PROCEDURE_FINISHING_IMAGE] in node_classes:
                node_string += 'Завершение'

            if next_nodes := scheme_dict[node]:
                node_string += f' -> {', '.join(str(order.index(next_node)) for next_node in next_nodes)};'
            else:
                node_string += '.'

            result_strings.append(node_string)

        
        result_string = '\n'.join(result_strings)
        # print(result_string)

        link = create_link(result_string)

        generate_action_result(action_node, link)
        
        return ScResult.OK
    

def get_node_classes(node: ScAddr):
    class_template = ScTemplate()
    class_template.triple(
        sc_types.NODE_VAR_CLASS >> "class",
        sc_types.EDGE_ACCESS_VAR_POS_PERM,
        node 
    )
    class_template_results = template_search(class_template)
    classes = [result.get("class") for result in class_template_results]
    return classes


def get_idtf(node: ScAddr, lang='lang_ru'):
    description_template = ScTemplate()
    description_template.quintuple(
        node,
        sc_types.EDGE_D_COMMON_VAR,
        sc_types.LINK_VAR >> "description",
        sc_types.EDGE_ACCESS_VAR_POS_PERM,
        ScKeynodes[FindStagesListIdentifiers.NREL_IMAGE_SIGN]
    )
    description_template.triple(
        ScKeynodes[lang],
        sc_types.EDGE_ACCESS_VAR_POS_PERM,
        "description"
    )

    description_template_result = template_search(description_template)[0]
    description_link = description_template_result.get("description")
    description: str = get_link_content_data(description_link)
    print(description)
    return description

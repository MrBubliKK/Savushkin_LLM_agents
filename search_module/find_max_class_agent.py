import logging
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_types
from sc_client.client import template_search
from sc_kpm.utils import get_element_system_identifier
from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.utils.action_utils import (
    create_action_result,
    finish_action_with_status,
    get_action_arguments,
    generate_action_result,
)
from sc_kpm import ScKeynodes
from sc_kpm.sc_sets import ScSet

from .search_module_idtfs import SearchModuleIdentifiers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="[%d-%b-%y %H:%M:%S]",
)

class FindMaxClassAgent(ScAgentClassic):
    def __init__(self):
        super().__init__(SearchModuleIdentifiers.ACTION_FIND_MAX_CLASS)  # Регистрируем действие

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("Agent finished: %s", "success" if is_successful else "fail")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        input_node, = get_action_arguments(action_node, 1)

        max_class_template = ScTemplate()
        max_class_template = ScTemplate()
        max_class_template.triple_with_relation(
            input_node,
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            sc_types.NODE_VAR >> "max_class",  # Исходный узел
            sc_types.EDGE_ACCESS_VAR_POS_PERM, 
            ScKeynodes['rrel_maximum_studied_object_class']
        )

        search_results = template_search(max_class_template)

        if not search_results:
            self.logger.warning("Maximum studied object class not found for node %s", input_node)
            return ScResult.ERROR

        self.logger.info(f'{len(search_results)}')

        result_set = ScSet(*(result.get('max_class') for result in search_results))
        create_action_result(action_node, result_set.set_node)

        # for result in search_results:

        #     max_class_addr = result.get("max_class")

        #     max_class_idtf = get_element_system_identifier(max_class_addr)
        #     self.logger.info(f"Found maximum studied object class: {max_class_idtf}")
        #     """ for src, connector, trg in result:
             
        #         self.logger.info(f'{get_element_system_identifier(trg)}') """
        
        return ScResult.OK

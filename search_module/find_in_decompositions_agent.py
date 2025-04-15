import logging
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_types
from sc_client.client import template_search
from sc_kpm.utils import get_link_content_data, get_element_system_identifier
from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.utils.action_utils import (
    create_action_result,
    finish_action_with_status,
    get_action_arguments,
    generate_action_result
)
from sc_kpm import ScKeynodes
from sc_kpm.sc_sets import ScSet

from .search_module_idtfs import SearchModuleIdentifiers

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(name)s | %(message)s", 
    datefmt="[%d-%b-%y %H:%M:%S]"
)

class FindDecompositionsAgent(ScAgentClassic):
    def __init__(self):
        super().__init__(SearchModuleIdentifiers.ACTION_FIND_IN_DECOMPOSITIONS)

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("Agent finished: %s", "success" if is_successful else "fail")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        recipe, = get_action_arguments(action_node, 1)

        recipe_template = ScTemplate()
        recipe_template.triple_with_relation(
            sc_types.NODE_VAR >> 'tuple_node',
            sc_types.EDGE_D_COMMON_VAR,
            recipe,
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            ScKeynodes['nrel_section_decomposition']
        )
        recipe_template.triple(
            'tuple_node',
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            sc_types.NODE_VAR >> 'decompositions'
        )

        search_results = template_search(recipe_template)

        self.logger.info(f'{len(search_results)}')

        result_set = ScSet(*(result.get('decompositions') for result in search_results))

        create_action_result(action_node, result_set.set_node)

        return ScResult.OK
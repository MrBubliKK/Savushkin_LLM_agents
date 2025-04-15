import logging
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_types
from sc_client.client import template_search

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.utils.action_utils import (
    create_action_result,
    finish_action_with_status,
    get_action_arguments,
)
from sc_kpm import ScKeynodes

from .search_module_idtfs import SearchModuleIdentifiers

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class FindDescriptionAgent(ScAgentClassic):
    def __init__(self):
        super().__init__(SearchModuleIdentifiers.ACTION_FIND_DESCRIPTION)

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("FindDescriptionAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        entity, = get_action_arguments(action_node, 1)

        entity_template = ScTemplate()
        entity_template.triple_with_relation(
            sc_types.NODE_VAR >> "empty_node_1",
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            entity,
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            ScKeynodes['rrel_key_sc_element']
        )
        entity_template.triple_with_relation(
            sc_types.NODE_VAR >> "empty_node_2",
            sc_types.EDGE_D_COMMON_VAR,
            'empty_node_1',
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            ScKeynodes['nrel_sc_text_translation']
        )
        entity_template.triple_with_relation(
            'empty_node_2',
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            sc_types.LINK_VAR >> "description_link",
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            ScKeynodes['rrel_example']
        )
        entity_template.triple(
            ScKeynodes['lang_ru'],
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            'description_link'
        )

        assert entity.is_valid()

        search_results = template_search(entity_template)
        info_link = search_results[0].get('description_link')

        create_action_result(action_node, info_link)

        return ScResult.OK

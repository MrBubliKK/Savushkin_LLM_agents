import logging
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_types
from sc_client.client import template_search

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScSet
from sc_kpm.utils import get_link_content_data
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


class SearchAgent(ScAgentClassic):
    def __init__(self):
        super().__init__(SearchModuleIdentifiers.ACTION_FIND_INFO)

    def on_event(self, event_element: ScAddr, event_edge: ScAddr, action_element: ScAddr) -> ScResult:
        result = self.run(action_element)
        is_successful = result == ScResult.OK
        finish_action_with_status(action_element, is_successful)
        self.logger.info("SearchAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        recipe, = get_action_arguments(action_node, 1)

        recipe_template = ScTemplate()
        recipe_template.triple_with_relation(
            recipe,
            sc_types.EDGE_D_COMMON_VAR,
            sc_types.LINK_VAR >> 'info_link',
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            ScKeynodes['nrel_main_idtf'],
        )
        recipe_template.triple(
            ScKeynodes['lang_ru'],
            sc_types.EDGE_ACCESS_VAR_POS_PERM,
            'info_link'
        )

        assert recipe.is_valid()

        search_results = template_search(recipe_template)
        info_link = search_results[0].get('info_link')

        create_action_result(action_node, info_link)

        # info = get_link_content_data(info_link)

        # print(info)

        return ScResult.OK

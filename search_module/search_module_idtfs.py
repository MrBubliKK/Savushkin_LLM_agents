from dataclasses import dataclass

from sc_kpm.identifiers import Idtf


@dataclass(frozen=True)
class SearchModuleIdentifiers:
    ACTION_CALL_AGENT: Idtf = "action_call_agent"
    NREL_MAIN_IDTF: Idtf = 'nrel_main_idtf'
    ACTION_FIND_DESCRIPTION: Idtf = "action_find_description"
    ACTION_FIND_INCLUDED_CHILDREN: Idtf = "action_find_included_children"
    ACTION_FIND_INFO: Idtf = "action_find_info"
    ACTION_FIND_INCLUDED_IN_PARENTS: Idtf = "action_find_included_in_parents"
    ACTION_FIND_IN_DECOMPOSITIONS: Idtf = "action_find_in_decompositions"
    ACTION_FIND_MAX_CLASS: Idtf = "action_find_max_class"
    ACTION_FIND_NOT_MAX_CLASS: Idtf = "action_find_not_max_class"
    ACTION_FIND_KEY_SC_ELEMENT: Idtf = "action_find_key_sc_element"
    ACTION_FIND_PARENT_DECOMPOSITION: Idtf = "action_find_parent_decomposition"
    ACTION_FIND_STAGES_LIST: Idtf = "action_find_stages_list"
    PROCEDURE_STARTING_IMAGE: Idtf = ""

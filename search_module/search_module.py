from sc_kpm import ScModule
from .search_agent import SearchAgent
from .find_description_agent import FindDescriptionAgent
from .find_included_children_agent import FindIncludedChildrenAgent
from .find_included_in_parents_agent import FindIncludedInParentsAgent
from .find_in_decompositions_agent import FindDecompositionsAgent
from .find_max_class_agent import FindMaxClassAgent
from .find_not_max_class_agent import FindNotMaxClassAgent
from .find_key_sc_element_agent import FindKeyScElementAgent
from .find_parent_decomposition_agent import FindParentDecompositionAgent
from .find_stages_list_agent import FindStagesListAgent
from .call_agent import CallAgent


class SearchModule(ScModule):
    def __init__(self):
        super().__init__(
            SearchAgent(),
            FindDescriptionAgent(),
            CallAgent(),
            FindIncludedInParentsAgent(),
            FindDecompositionsAgent(),
            FindIncludedChildrenAgent(),
            FindMaxClassAgent(),
            FindNotMaxClassAgent(),
            FindKeyScElementAgent(),
            FindParentDecompositionAgent(),
            FindStagesListAgent()
        )

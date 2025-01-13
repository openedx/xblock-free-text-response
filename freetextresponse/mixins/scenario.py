"""
Mixin workbench behavior into XBlocks
"""
try:
    from xblock.utils.resources import ResourceLoader
except ModuleNotFoundError:
    from xblockutils.resources import ResourceLoader


loader = ResourceLoader(__name__)


class XBlockWorkbenchMixin(object):
    """
    Provide a default test workbench for the XBlock
    """

    @classmethod
    def workbench_scenarios(cls):
        """
        Gather scenarios to be displayed in the workbench
        """
        return loader.load_scenarios_from_path("../scenarios")

"""
Mixin workbench behavior into XBlocks
"""
try:
    from xblock.utils.resources import ResourceLoader
except ModuleNotFoundError:
    from xblockutils.resources import ResourceLoader


loader = ResourceLoader(__name__)


def _parse_title(title):
    """
    Parse the title of the scenario
    """
    title = title.split("-")
    title = " ".join(title)
    return title


def _parse_scenarios(scenarios):
    """
    Parse the content of the scenario files
    """
    parsed_scenarios = []
    for scenario in scenarios:
        title = _parse_title(scenario[0])
        parsed_scenarios.append((title, scenario[1]))
    return parsed_scenarios


class XBlockWorkbenchMixin(object):
    """
    Provide a default test workbench for the XBlock
    """

    @classmethod
    def workbench_scenarios(cls):
        """
        Gather scenarios to be displayed in the workbench
        """
        scenarios = loader.load_scenarios_from_path("../scenarios")
        return _parse_scenarios(scenarios)

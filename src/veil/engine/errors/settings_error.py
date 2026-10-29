class SettingsError(Exception):
    """The settings are not valid. The message lists every problem, one on each line.

    A message names the layer and the setting. It never repeats a value.
    """

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems

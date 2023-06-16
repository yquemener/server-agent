class Tool:
    def __init__(self):
        self.history = list()

    def context(self):
        # Returns the context that is necessary for the agent to create correct
        # requests
        return "Empty"

    def reset(self):
        self.history.clear()

    def conversation(self):
        # Returns the latest back and forth between the agent and the tool
        # self.history should be updated by execute_query and can contain an
        # abbreviated respsonse
        return "\n".join([f"{h[0]}: {h[1]}" for h in self.history])


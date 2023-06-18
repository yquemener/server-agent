from tools.tool import Tool


class MatrixModule(Tool):
    def __init__(self, room):
        super().__init__()
        self.room=room

    def execute_query(self, content):
        self.room.send_text(str(content))
        return f"Send to the user the message:{content}", "success"

import json
import os


class FlaskModule:
    def __init__(self, root_path):
        self.root_path = root_path
        self.directories = ['templates', 'static/css', 'static/html', 'pages']

        # Initialize necessary directories
        os.makedirs(self.root_path, exist_ok=True)
        for dir_name in self.directories:
            os.makedirs(os.path.join(self.root_path, dir_name), exist_ok=True)
        self.history = list()

    def reset(self):
        self.history.clear()

    def conversation(self):
        return "\n".join([f"{h[0]}: {h[1]}" for h in self.history])

    def execute_query(self, json_obj):
        file_type = json_obj['type']
        content = json_obj['content']
        url = json_obj['url']

        # Adjust URL for file system. Replace slashes with underscores for file name
        file_name_url = url.replace('/', '_') if url != '/' else 'index'

        # If URL has slashes, replace them with OS-specific separator for file paths
        url = url.replace('/', os.sep)

        # Determine the file path and file name based on the type of file
        if file_type == 'html template':
            file_dir = os.path.join(self.root_path, 'templates')
            file_name = f'{file_name_url}.html'
        elif file_type == 'css':
            file_dir = os.path.join(self.root_path, 'static/css')
            file_name = f'{file_name_url}.css'
        elif file_type == 'html static':
            file_dir = os.path.join(self.root_path, 'static/html')
            file_name = f'{file_name_url}.html'
        elif file_type == 'python':
            file_dir = os.path.join(self.root_path, 'pages')
            file_name = f'{file_name_url}.py'
        else:
            print(f"Unknown file type: {file_type}")
            return

        # Ensure the file directory exists
        os.makedirs(file_dir, exist_ok=True)

        # Define the file path
        file_path = os.path.join(file_dir, file_name)

        # If it's a python file, add boilerplate code
        if file_type == 'python':
            content = f'''from flask import Blueprint, render_template
    from app import app

    {file_name_url} = Blueprint('{file_name_url}', __name__)

    @app.route('/{url}')
    {content}

    app.register_blueprint({file_name_url})'''

        # Write the content to the file
        with open(file_path, 'w') as f:
            f.write(content)

        print(f"File {file_name} created successfully in directory {file_dir}.")

    def context(self):
        for root, dirs, files in os.walk(self.root_path):
            level = root.replace(self.root_path, '').count(os.sep)
            indent = ' ' * 4 * level
            print('{}{}/'.format(indent, os.path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print('{}{}'.format(subindent, f))

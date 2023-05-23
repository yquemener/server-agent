import sys
from bs4 import BeautifulSoup

def display_div_elements(soup):
    div_elements = soup.body.find_all('div', recursive=False)
    for index, div in enumerate(div_elements, start=1):
        div_id = div.get('id', '')
        div_class = div.get('class', '')
        print(f"{index}. Id: {div_id}, Class: {div_class}")
    return div_elements

def display_descendants_text(element):
    descendants_text = element.find_all(text=True, recursive=True)
    text = ' '.join(descendants_text).strip()
    print(f"Text inside descendants:\n{text}")

def navigate_html(file_name):
    # Read the HTML file
    with open(file_name, 'r') as file:
        html = file.read()

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    div_elements = display_div_elements(soup)

    while True:
        try:
            user_choice = input("Select a div element (enter number) or 'a' for all descendants: ")

            if user_choice == 'a':
                display_descendants_text(selected_div)
                break

            user_choice = int(user_choice)
            selected_div = div_elements[user_choice-1]
            div_elements = selected_div.find_all('div', recursive=False)

            if len(div_elements) == 0:
                print("Leaf element reached. Text inside:")
                print(selected_div.text.strip())
                break

            print("Children div elements:")
            for index, div in enumerate(div_elements, start=1):
                div_id = div.get('id', '')
                div_class = div.get('class', '')
                print(f"{index}. Id: {div_id}, Class: {div_class}")

        except (ValueError, IndexError):
            print("Invalid choice. Please select again.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python navigate_html.py <file_name>')
    else:
        file_name = sys.argv[1]
        navigate_html(file_name)


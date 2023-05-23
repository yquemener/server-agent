import wikipediaapi

def display_table_of_contents(page):
    table_of_contents = page.sections
    for index, section in enumerate(table_of_contents):
        print(f"{index + 1}. {section.title}")

def display_section_content(section):
    if section.text:
        print(section.text)
    for subsection in section.sections:
        display_section_content(subsection)

def main():
    # Ask for user input
    search_term = input("Enter a word to search on Wikipedia: ")

    # Fetch the Wikipedia page
    wiki_wiki = wikipediaapi.Wikipedia('en')
    page = wiki_wiki.page(search_term)

    if not page.exists():
        print("The page does not exist on Wikipedia.")
        return

    # Display the table of contents
    print("Table of Contents:")
    display_table_of_contents(page)

    # Ask for user input to select a section
    section_num = input("Enter the number of the section to download and display: ")
    section_num = int(section_num) - 1

    if section_num < 0 or section_num >= len(page.sections):
        print("Invalid section number.")
        return

    # Display the selected section content
    selected_section = page.sections[section_num]
    print("Selected Section Content:")
    display_section_content(selected_section)

if __name__ == '__main__':
    main()

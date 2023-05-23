import subprocess
from bs4 import BeautifulSoup
import urllib.parse

query = input("Entrez votre recherche: ")
url = 'https://html.duckduckgo.com/html/?q=' + query

curl_output = subprocess.check_output(['curl', url])
soup = BeautifulSoup(curl_output, 'html.parser')
links = soup.find_all('a', {'class': 'result__url'})

if links:
    for i in range(5):
        l=links[i].get('href')
        uddg = urllib.parse.parse_qs(urllib.parse.urlparse(l).query)['uddg'][0]
        decoded_url = urllib.parse.unquote(uddg)
        print(decoded_url)
else:
    print("Aucun lien trouvé pour cette recherche.")

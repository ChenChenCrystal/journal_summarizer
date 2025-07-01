def scrape(self):
    print("🔍 Scraping arXiv...")
    response = requests.get(self.journal_url, headers=self.headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    articles = []
    all_entries = soup.select('dl > dt')
    all_descriptions = soup.select('dl > dd')

    for dt, dd in zip(all_entries, all_descriptions):
        id_tag = dt.find('a', title='Abstract')
        if not id_tag:
            continue

        relative_link = id_tag['href']  # e.g., /abs/2506.24119
        full_url = self.base_url + relative_link

        title_tag = dd.find('div', class_='list-title mathjax')
        if not title_tag:
            continue
        title = title_tag.text.replace('Title:', '').strip()

        # 🧠 NEW: fetch abstract from the article detail page
        abstract = self.fetch_abstract(full_url)

        articles.append({
            'title': title,
            'abstract': abstract,
            'url': full_url,
            'journal': 'arXiv cs.AI'
        })

        time.sleep(1)  # be polite

    print(f"✅ Found {len(articles)} articles.")
    return articles

def fetch_abstract(self, url):
    try:
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')
        abstract_tag = soup.find('blockquote', class_='abstract')
        if abstract_tag:
            return abstract_tag.text.replace('Abstract:', '').strip()
        return "Abstract not found"
    except Exception as e:
        print(f"Error fetching abstract from {url}: {e}")
        return "Abstract not found"
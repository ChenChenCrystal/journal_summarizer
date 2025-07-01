#!/usr/bin/env python3

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

class ArticleScraper:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/114.0 Safari/537.36'
            )
        }
        self.journal_url = 'https://arxiv.org/list/cs.AI/recent'
        self.base_url = 'https://arxiv.org'

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

            relative_link = id_tag['href']
            full_url = self.base_url + relative_link

            title_tag = dd.find('div', class_='list-title mathjax')
            if not title_tag:
                continue
            title = title_tag.text.replace('Title:', '').strip()

            # 🔄 NEW: Fetch abstract from the article's detail page
            abstract = self.fetch_abstract(full_url)

            articles.append({
                'title': title,
                'abstract': abstract,
                'url': full_url,
                'journal': 'arXiv cs.AI'
            })

            time.sleep(1)

        print(f"✅ Found {len(articles)} articles.")
        return articles

    def fetch_abstract(self, url):
        try:
            res = requests.get(url, headers=self.headers)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, 'html.parser')
            tag = soup.find('blockquote', class_='abstract')
            return tag.text.replace('Abstract:', '').strip() if tag else "Abstract not found"
        except Exception as e:
            print(f"❌ Error fetching abstract from {url}: {e}")
            return "Abstract not found"

    def summarize_with_chatgpt(self, articles):
        if not self.openai_api_key:
            print("❌ No OpenAI API key found. Skipping summarization.")
            return articles

        summarized = []
        for article in articles:
            prompt = (
                f"Summarize the following AI research abstract in 2-3 sentences, highlighting the key findings and significance:\n\n"
                f"Title: {article['title']}\n\n"
                f"Abstract: {article['abstract']}\n\nSummary:"
            )

            try:
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {self.openai_api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'gpt-4',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.5,
                        'max_tokens': 300
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result['choices'][0]['message']['content'].strip()
                    article['ai_summary'] = summary
                else:
                    print(f"⚠️ OpenAI API error: {response.status_code} - {response.text}")
                    article['ai_summary'] = "Summary unavailable"

            except Exception as e:
                print(f"❌ Error summarizing: {e}")
                article['ai_summary'] = "Summary unavailable"

            summarized.append(article)
            time.sleep(1)

        return summarized

    def save_results(self, articles):
        os.makedirs('summaries', exist_ok=True)
        date_str = datetime.now().strftime('%Y-%m-%d')
        json_path = f'summaries/articles_{date_str}.json'
        md_path = f'summaries/articles_{date_str}.md'

        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(articles, jf, indent=2, ensure_ascii=False)

        with open(md_path, 'w', encoding='utf-8') as mf:
            mf.write(f"# arXiv cs.AI Summary – {date_str}\n\n")
            for article in articles:
                mf.write(f"## {article['title']}\n")
                mf.write(f"**URL:** {article['url']}\n\n")
                mf.write(f"**Abstract:** {article['abstract']}\n\n")
                mf.write(f"**AI Summary:** {article.get('ai_summary', 'Not available')}\n\n")
                mf.write("---\n\n")

        print(f"💾 Saved to: {json_path} and {md_path}")

    def run(self):
        articles = self.scrape()
        if not articles:
            print("⚠️ No articles scraped.")
            return

        summarized = self.summarize_with_chatgpt(articles)
        self.save_results(summarized)
        print("✅ Done.")

if __name__ == '__main__':
    scraper = ArticleScraper()
    scraper.run()
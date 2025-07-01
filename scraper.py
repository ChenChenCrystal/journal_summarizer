#!/usr/bin/env python3
"""
Article Scraper and Summarizer using ChatGPT API
"""

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

        self.journals = [
            {
                'name': 'Journal of Advertising',
                'url': 'https://www.tandfonline.com/action/showAxaArticles?journalCode=ujoa20',
                'title_selector': 'h5.issue-item__title a',
                'link_attr': 'href',
                'abstract_selector': 'div.abstractSection.abstractInFull'
            }
        ]

    def scrape(self):
        all_articles = []
        for journal in self.journals:
            print(f"Scraping: {journal['name']}")
            try:
                res = requests.get(journal['url'], headers=self.headers)
                res.raise_for_status()
                soup = BeautifulSoup(res.content, 'lxml')

                article_links = soup.select(journal['title_selector'])

                for tag in article_links[:10]:  # limit to 10
                    title = tag.get_text(strip=True)
                    link = tag.get(journal['link_attr'])
                    full_url = link if link.startswith('http') else f"https://www.tandfonline.com{link}"

                    abstract = self.fetch_abstract(full_url, journal['abstract_selector'])

                    all_articles.append({
                        'journal': journal['name'],
                        'title': title,
                        'url': full_url,
                        'abstract': abstract
                    })

                    time.sleep(1)
            except Exception as e:
                print(f"Failed to scrape {journal['name']}: {e}")
        return all_articles

    def fetch_abstract(self, url, selector):
        try:
            res = requests.get(url, headers=self.headers)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, 'lxml')
            tag = soup.select_one(selector)
            return tag.get_text(strip=True) if tag else "Abstract not found"
        except Exception as e:
            print(f"Error fetching abstract from {url}: {e}")
            return "Abstract not found"

    def summarize_with_chatgpt(self, articles):
        if not self.openai_api_key:
            print("No OpenAI API key found. Skipping summarization.")
            return articles

        summarized_articles = []
        for article in articles:
            prompt = f"""Summarize the following research abstract in 2-3 sentences, highlighting the main findings and significance:\n\nTitle: {article['title']}\n\nAbstract: {article['abstract']}\n\nSummary:"""

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
                    print(f"API error ({response.status_code}): {response.text}")
                    article['ai_summary'] = "Summary unavailable"
            except Exception as e:
                print(f"Error summarizing article '{article['title']}': {e}")
                article['ai_summary'] = "Summary unavailable"

            summarized_articles.append(article)
            time.sleep(1)  # Respect rate limits

        return summarized_articles

    def save_results(self, articles):
        os.makedirs('summaries', exist_ok=True)
        date_str = datetime.now().strftime('%Y-%m-%d')
        json_path = f'summaries/articles_{date_str}.json'
        md_path = f'summaries/articles_{date_str}.md'

        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(articles, jf, indent=2, ensure_ascii=False)

        with open(md_path, 'w', encoding='utf-8') as mf:
            mf.write(f"# Weekly Article Summary - {date_str}\n\n")
            for article in articles:
                mf.write(f"## {article['title']}\n")
                mf.write(f"**Journal:** {article['journal']}\n")
                mf.write(f"**URL:** {article['url']}\n")
                mf.write(f"**Abstract:** {article['abstract']}\n")
                mf.write(f"**AI Summary:** {article.get('ai_summary', 'Not available')}\n")
                mf.write("\n---\n\n")

        print(f"Saved {len(articles)} articles to: {json_path} and {md_path}")

    def run(self):
        print("🔍 Scraping articles...")
        articles = self.scrape()
        if not articles:
            print("No articles found.")
            return

        print(f"🧠 Summarizing {len(articles)} articles with ChatGPT...")
        summarized = self.summarize_with_chatgpt(articles)

        print("💾 Saving results...")
        self.save_results(summarized)
        print("✅ Done.")

if __name__ == '__main__':
    scraper = ArticleScraper()
    scraper.run()
#!/usr/bin/env python3

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List
from xml.etree import ElementTree


class PaperCollector:
    """Collect HCI/CMC + advertising/communication papers from compliant APIs."""

    ARXIV_API = "https://export.arxiv.org/api/query"
    ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}

    def __init__(self, max_results: int = 30):
        self.max_results = max_results
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.user_agent = (
            "journal_summarizer/1.1 "
            "(research automation; contact via repository owner)"
        )
        self.topics = [
            "HCI",
            "computer-mediated communication",
            "advertising",
            "marketing communication",
            "attention",
            "cognitive offloading",
            "generative AI",
            "virtual reality",
        ]

    def _http_get(self, url: str, params: Dict[str, str]) -> str:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{url}?{query}", headers={"User-Agent": self.user_agent}, method="GET"
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    def _http_post_json(self, url: str, payload: Dict) -> Dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    def build_arxiv_query(self) -> str:
        term_query = " OR ".join([f'all:"{term}"' for term in self.topics])
        return f"(cat:cs.HC OR cat:cs.CY OR cat:cs.CL) AND ({term_query})"

    def fetch_arxiv(self) -> List[Dict[str, str]]:
        print("🔍 Collecting papers from arXiv API (no HTML scraping)...")
        params = {
            "search_query": self.build_arxiv_query(),
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        response_text = self._http_get(self.ARXIV_API, params)
        root = ElementTree.fromstring(response_text)

        papers: List[Dict[str, str]] = []
        for entry in root.findall("atom:entry", self.ARXIV_NS):
            title = (entry.findtext("atom:title", default="", namespaces=self.ARXIV_NS)).strip()
            abstract = (
                entry.findtext("atom:summary", default="", namespaces=self.ARXIV_NS)
            ).strip()
            url = entry.findtext("atom:id", default="", namespaces=self.ARXIV_NS)
            published = entry.findtext(
                "atom:published", default="", namespaces=self.ARXIV_NS
            )
            if not title or not abstract or not url:
                continue

            papers.append(
                {
                    "title": " ".join(title.split()),
                    "abstract": " ".join(abstract.split()),
                    "url": url,
                    "source": "arXiv",
                    "published": published,
                }
            )

        print(f"✅ Found {len(papers)} papers.")
        return papers

    def summarize(self, papers: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not self.openai_api_key:
            print("⚠️ OPENAI_API_KEY not set; skipping AI summaries.")
            return papers

        summarized = []
        for i, paper in enumerate(papers, start=1):
            print(f"🧠 Summarizing {i}/{len(papers)}: {paper['title'][:80]}...")
            prompt = (
                "You are helping with a daily research brief for HCI/CMC in "
                "advertising and communication.\n"
                "Summarize this paper in 3 concise bullet points covering: \n"
                "1) research question/theory, 2) method/context, 3) practical "
                "implications for communication/advertising.\n"
                "Then add one line: 'Relevance tags:' with 2-4 tags chosen from "
                "[attention, cognitive-offloading, genAI, VR, CMC, HCI, advertising].\n\n"
                f"Title: {paper['title']}\n"
                f"Abstract: {paper['abstract']}"
            )

            summary = self._call_openai(prompt)
            paper["ai_summary"] = summary
            summarized.append(paper)
            time.sleep(0.3)

        return summarized

    def _call_openai(self, prompt: str) -> str:
        try:
            payload = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 350,
            }
            response = self._http_post_json(
                "https://api.openai.com/v1/chat/completions", payload
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            print(f"❌ Summary error: {exc}")
            return "Summary unavailable"

    def save_results(self, papers: List[Dict[str, str]]) -> None:
        os.makedirs("summaries", exist_ok=True)
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        json_path = f"summaries/articles_{date_str}.json"
        md_path = f"summaries/articles_{date_str}.md"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Daily HCI/CMC Paper Brief – {date_str} (UTC)\n\n")
            f.write(
                "Topics: attention, cognitive offloading, generative AI, virtual reality, "
                "advertising communication.\n\n"
            )
            for paper in papers:
                f.write(f"## {paper['title']}\n")
                f.write(f"- **Source:** {paper['source']}\n")
                f.write(f"- **Published:** {paper.get('published', 'unknown')}\n")
                f.write(f"- **URL:** {paper['url']}\n\n")
                f.write(f"**Abstract**\n{paper['abstract']}\n\n")
                f.write(f"**AI Summary**\n{paper.get('ai_summary', 'Not available')}\n\n")
                f.write("---\n\n")

        print(f"💾 Saved: {json_path} and {md_path}")

    def run(self) -> None:
        try:
            papers = self.fetch_arxiv()
        except urllib.error.URLError as exc:
            print(f"❌ Failed to fetch arXiv API: {exc}")
            return

        if not papers:
            print("⚠️ No papers collected.")
            return

        papers = self.summarize(papers)
        self.save_results(papers)
        print("✅ Daily brief generated.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and summarize HCI/CMC papers.")
    parser.add_argument("--max-results", type=int, default=30, help="Max papers from arXiv")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    collector = PaperCollector(max_results=args.max_results)
    collector.run()

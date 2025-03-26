import feedparser
from transformers import pipeline
import requests
import config
from datetime import datetime, timedelta

# 初始化翻译器（使用轻量模型）
translator = pipeline(
    "translation_en_to_zh",
    model="Helsinki-NLP/opus-mt-en-zh",
    max_length=128
)

def fetch_news():
    all_articles = []
    for rss_url in config.RSS_SOURCES:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]:  # 每个源取前5条
            article = {
                'title': entry.title,
                'link': entry.link,
                'summary': entry.get('summary', ''),
                'source': rss_url.split('/')[-2],
                'published': datetime(*entry.published_parsed[:6]),
            }
            all_articles.append(article)
    return all_articles

def translate_content(text):
    try:
        return translator(text)[0]['translation_text']
    except:
        return text[:100] + "..."  # 失败时截断原文

def filter_and_sort(articles):
    # 时效性过滤（保留48小时内）
    cutoff = datetime.now() - timedelta(hours=48)
    valid_articles = [a for a in articles if a['published'] > cutoff]

    # 简易评分系统
    scored = []
    for article in valid_articles:
        score = 0
        # 来源权重
        if 'bbc' in article['source'].lower(): score += 2
        if 'reuters' in article['source'].lower(): score += 1
        # 关键词匹配
        translated_title = translate_content(article['title'])
        article['zh_title'] = translated_title
        score += sum(kw in translated_title for kw in config.KEYWORDS)
        scored.append( (score, article) )

    # 按分数降序排列
    return sorted(scored, key=lambda x: -x[0])

def send_to_telegram(articles):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    
    message = "今日精选新闻：\n\n"
    for idx, (score, article) in enumerate(articles[:20]):
        message += f"{idx+1}. 【{article['source']}】{article['zh_title']}\n{article['link']}\n\n"

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={'chat_id': chat_id, 'text': message}
    )

if __name__ == "__main__":
    articles = fetch_news()
    sorted_articles = filter_and_sort(articles)
    send_to_telegram(sorted_articles)

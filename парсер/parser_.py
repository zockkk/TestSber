import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

def parse_lenta_news(pages=3):
    base_url = "https://lenta.ru/parts/news/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    all_news = []
    
    for page in range(1, pages + 1):
        url = f"{base_url}?page={page}" if page > 1 else base_url
        print(f"Парсинг страницы {page}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_cards = soup.find_all('li', class_='parts-page__item') or []
            
            for card in news_cards:
                try:
                    title_elem = card.find('h3', class_='card-full-news__title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = card.find('a', class_='card-full-news')
                    if not link_elem or not link_elem.get('href'):
                        continue
                        
                    link = link_elem['href']
                    if not link.startswith('http'):
                        link = 'https://lenta.ru' + link
                    
                    news_data = parse_news_page(link, headers)
                    
                    if news_data and news_data.get('date') and news_data.get('text'):
                        news_item = {
                            'title': title,
                            'url': link,
                            'date': news_data['date'],
                            'text': news_data['text']
                        }
                        all_news.append(news_item)
                        print(f"Добавлена новость: {title[:50]}...")
                    else:
                        print(f"Пропущена новость (неполные данные): {title[:50]}...")
                    
                except Exception as e:
                    print(f"Ошибка при обработке карточки: {str(e)[:100]}...")
                    continue
                
            time.sleep(2)
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при загрузке страницы {page}: {e}")
            continue
        except Exception as e:
            print(f"Общая ошибка при обработке страницы {page}: {e}")
            continue
    
    return all_news

def parse_custom_date(date_str):
    """
    Преобразует строку с датой в формате "ЧЧ:ММ, дд месяц(словом) гггг" в datetime
    """
    try:
        date_str = ' '.join(date_str.split())
        
        months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        time_part, date_part = date_str.split(', ')
        hours, minutes = map(int, time_part.split(':'))
        day, month_str, year = date_part.split()
        month = months.get(month_str.lower())
        
        if month:
            dt = datetime(int(year), month, int(day), hours, minutes)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        print(f"Ошибка парсинга даты '{date_str}': {e}")
    
    return date_str

def parse_news_page(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        date_element = soup.find('a', class_='topic-header__time')
        if date_element:
            date_text = date_element.text.strip()
            date = parse_custom_date(date_text)
        else:
            date = None
        
        text_blocks = soup.find_all('p', class_='topic-body__content-text')
        text = '\n'.join([p.text.strip() for p in text_blocks if p.text.strip()])
        
        return {
            'date': date,
            'text': text if text else None
        }
        
    except Exception as e:
        print(f"Ошибка при парсинге страницы новости {url}: {e}")
        return None

if __name__ == "__main__":
    news_data = parse_lenta_news(pages=3)
    
    import pandas as pd
    df = pd.DataFrame(news_data)
    df.to_csv('lenta_news.csv', index=False, encoding='utf-8-sig')
    print(f"Сохранено {len(df)} новостей в файл lenta_news.csv")
    
    print("Примеры собранных новостей:")
    for i, news in enumerate(news_data[:3], 1):
        print(f"\n{i}. {news['title']}")
        print(f"Дата: {news['date']}")
        print(f"Текст: {news['text'][:200]}...")
import json
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

def parse_hh():
    print("-> Сбор с HeadHunter...")
    items = []
    queries = ["спортивный фотограф", "фотограф спорт", "репортажный фотограф"]
    seen_ids = set()

    for q in queries:
        for area_id in [1, 2014]:  # Москва и МО
            url = "https://api.hh.ru/vacancies"
            params = {
                "text": q,
                "area": area_id,
                "per_page": 10,
                "order_by": "publication_time",
            }
            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    for vac in res.json().get("items", []):
                        v_id = f"hh_{vac['id']}"
                        if v_id in seen_ids:
                            continue
                        seen_ids.add(v_id)

                        price = "По договорённости"
                        sal = vac.get("salary")
                        if sal:
                            if sal.get("from") and sal.get("to"):
                                price = f"{sal['from']:,} – {sal['to']:,} ₽".replace(",", " ")
                            elif sal.get("from"):
                                price = f"от {sal['from']:,} ₽".replace(",", " ")
                            elif sal.get("to"):
                                price = f"до {sal['to']:,} ₽".replace(",", " ")

                        items.append({
                            "id": v_id,
                            "source": "HH",
                            "title": vac.get("name", "Фотограф"),
                            "company": vac.get("employer", {}).get("name", "Компания"),
                            "location": vac.get("area", {}).get("name", "Москва / МО"),
                            "price": price,
                            "tags": [vac.get("employment", {}).get("name", "Репортаж"), "Спорт"],
                            "url": vac.get("alternate_url", "https://hh.ru"),
                            "is_urgent": "срочно" in vac.get("name", "").lower(),
                            "deadline": "Свежее",
                            "description": "Съемка спортивных событий, динамичный репортаж. Подробности в первоисточнике."
                        })
            except Exception as e:
                print(f"Ошибка HH ({q}): {e}")
            time.sleep(0.3)
    return items

def parse_avito():
    print("-> Сбор с Авито...")
    items = []
    url = "https://www.avito.ru/moskva_i_mo/vakansii?q=спортивный+фотограф"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select('div[data-marker="item"]')[:8]
            for card in cards:
                title_el = card.select_one('h3[itemprop="name"]') or card.select_one('a[data-marker="item-title"]')
                price_el = card.select_one('meta[itemprop="price"]') or card.select_one('[data-marker="item-price"]')
                link_el = card.select_one('a[data-marker="item-title"]')
                geo_el = card.select_one('div[class*="geo-root"]')

                title = title_el.get_text(strip=True) if title_el else "Спортивный фотограф"
                link = f"https://www.avito.ru{link_el['href']}" if link_el and 'href' in link_el.attrs else "https://avito.ru"

                price = "По договорённости"
                if price_el:
                    pval = price_el.get("content") or price_el.get_text(strip=True)
                    if pval and any(c.isdigit() for c in pval):
                        price = f"{pval} ₽" if "₽" not in pval else pval

                loc = geo_el.get_text(strip=True) if geo_el else "Москва / МО"

                items.append({
                    "id": card.get("data-item-id", str(hash(link))),
                    "source": "AVITO",
                    "title": title,
                    "company": "Заказчик с Авито",
                    "location": loc,
                    "price": price,
                    "tags": ["Авито", "Спортсъемка"],
                    "url": link,
                    "is_urgent": "срочно" in title.lower(),
                    "deadline": "Актуально",
                    "description": "Заказ на фотосъемку с площадки Авито."
                })
    except Exception as e:
        print(f"Ошибка Avito: {e}")
    return items

def main():
    jobs = parse_hh() + parse_avito()
    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"Успешно сохранено {len(jobs)} вакансий прямо в файл vacancies.json!")

if __name__ == "__main__":
    main()

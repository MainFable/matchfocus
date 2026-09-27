import json
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

def parse_trudvsem():
    print("-> Сбор с портала Работа России (ТрудВсем)...")
    items = []
    queries = ["фотограф", "репортаж"]
    regions = [
        ("7700000000000", "Москва"),
        ("5000000000000", "Московская область")
    ]
    seen_ids = set()

    for reg_code, reg_name in regions:
        for q in queries:
            url = f"https://opendata.trudvsem.ru/api/v1/vacancies/region/{reg_code}"
            params = {"text": q, "limit": 25}
            try:
                res = requests.get(url, params=params, headers={"User-Agent": "MatchFocus/1.0"}, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    vacancies = data.get("results", {}).get("vacancies", [])
                    for entry in vacancies:
                        v = entry.get("vacancy", {})
                        raw_id = v.get("id") or v.get("vac_url") or str(hash(v.get("job-name", "")))
                        v_id = f"trud_{raw_id}"
                        if v_id in seen_ids:
                            continue
                        seen_ids.add(v_id)

                        name = v.get("job-name", "Специалист по съемке")

                        price = "По договорённости"
                        sal_min = v.get("salary_min")
                        sal_max = v.get("salary_max")
                        if sal_min and sal_max and sal_min != sal_max:
                            price = f"{sal_min:,} – {sal_max:,} ₽".replace(",", " ")
                        elif sal_min:
                            price = f"от {sal_min:,} ₽".replace(",", " ")
                        elif sal_max:
                            price = f"до {sal_max:,} ₽".replace(",", " ")

                        duty = v.get("duty") or "Обязанности уточняются у работодателя."
                        duty_clean = duty.replace("<p>", "").replace("</p>", "").replace("<br>", " ")

                        items.append({
                            "id": v_id,
                            "source": "Job / ТрудВсем",
                            "title": name,
                            "company": v.get("company", {}).get("name", "Организация / Клуб"),
                            "location": reg_name,
                            "price": price,
                            "tags": ["Репортаж", "Гос. сектор / Клубы"],
                            "url": v.get("vac_url", "https://trudvsem.ru"),
                            "is_urgent": False,
                            "deadline": "Актуально",
                            "description": duty_clean[:250] + ("..." if len(duty_clean) > 250 else "")
                        })
            except Exception as e:
                print(f"Ошибка запроса ТрудВсем ({q}): {e}")
            time.sleep(0.3)

    print(f"-> Итого собрано с ТрудВсем: {len(items)}")
    return items

def parse_avito():
    print("-> Сбор с Авито (Москва и МО)...")
    items = []
    queries = ["спортивный+фотограф", "фотограф+мероприятий", "фотограф+репортаж"]
    seen_ids = set()

    for q in queries:
        url = f"https://www.avito.ru/moskva_i_mo/vakansii?q={q}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            print(f"Запрос Авито: '{q}' -> Статус: {res.status_code}")
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.select('div[data-marker="item"]')
                print(f"  Найдено карточек на странице Авито: {len(cards)}")
                
                for card in cards[:10]:
                    link_el = card.select_one('a[data-marker="item-title"]')
                    title_el = card.select_one('h3[itemprop="name"]') or link_el
                    price_el = card.select_one('meta[itemprop="price"]') or card.select_one('[data-marker="item-price"]')
                    geo_el = card.select_one('div[class*="geo-root"]')

                    if not link_el or not title_el:
                        continue

                    raw_href = link_el.get("href", "")
                    link = f"https://www.avito.ru{raw_href}" if raw_href.startswith("/") else raw_href
                    card_id = card.get("data-item-id") or str(hash(link))
                    v_id = f"avito_{card_id}"

                    if v_id in seen_ids:
                        continue
                    seen_ids.add(v_id)

                    title = title_el.get_text(strip=True)
                    price = "По договорённости"
                    if price_el:
                        pval = price_el.get("content") or price_el.get_text(strip=True)
                        if pval and any(c.isdigit() for c in pval):
                            price = f"{pval} ₽" if "₽" not in pval else pval

                    loc = geo_el.get_text(strip=True) if geo_el else "Москва и область"

                    items.append({
                        "id": v_id,
                        "source": "Авито",
                        "title": title,
                        "company": "Заказчик с Авито",
                        "location": loc,
                        "price": price,
                        "tags": ["Авито", "Спорт / События"],
                        "url": link,
                        "is_urgent": "срочно" in title.lower(),
                        "deadline": "Актуально",
                        "description": "Свежее объявление о поиске фотографа на Авито. Перейдите по ссылке для связи с заказчиком."
                    })
            else:
                print(f"  Авито вернул статус {res.status_code} (возможна защита от ботов)")
        except Exception as e:
            print(f"Ошибка запроса Авито ({q}): {e}")
        time.sleep(1.0)

    print(f"-> Итого собрано с Авито: {len(items)}")
    return items

def main():
    trud_jobs = parse_trudvsem()
    avito_jobs = parse_avito()
    all_jobs = trud_jobs + avito_jobs

    if not all_jobs:
        print("Внешние базы не вернули данных, создаем демонстрационный спортивный пул...")
        all_jobs = [
            {
                "id": "match_1",
                "source": "Авито",
                "title": "Фотограф на турнир по футболу (выходные)",
                "company": "Организатор детско-юношеского первенства",
                "location": "Москва (САО)",
                "price": "от 6 000 ₽ / игровой день",
                "tags": ["Футбол", "Репортаж", "Турнир"],
                "url": "https://www.avito.ru",
                "is_urgent": True,
                "deadline": "Срочно",
                "description": "Требуется фотограф с длиннофокусной оптикой (70-200mm) для съемки матчей кубка."
            },
            {
                "id": "match_2",
                "source": "Job / ТрудВсем",
                "title": "Фотокорреспондент / оператор спортивных соревнований",
                "company": "Спортивный комплекс «Арена»",
                "location": "Московская область",
                "price": "65 000 – 85 000 ₽",
                "tags": ["Штат", "Спорт", "Арена"],
                "url": "https://trudvsem.ru",
                "is_urgent": False,
                "deadline": "Актуально",
                "description": "Репортажная съемка соревнований, подготовка репортажей для пресс-службы и медиаресурсов."
            }
        ]

    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    print(f"Завершено. В vacancies.json сохранено объектов: {len(all_jobs)}")

if __name__ == "__main__":
    main()

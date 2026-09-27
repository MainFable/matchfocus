import json
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

def parse_trudvsem():
    print("-> Сбор с портала Работа России (ТрудВсем)...")
    items = []
    
    # Целевые запросы для репортажа и спорта
    queries = [
        "спортивный фотограф",
        "фотограф",
        "репортаж",
        "фотокорреспондент",
        "видеооператор"
    ]
    
    # 77 - Москва, 50 - Московская область
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

                        name = v.get("job-name", "Фотограф / Репортаж")
                        name_lower = name.lower()

                        # Фильтруем случайные совпадения
                        if not any(w in name_lower for w in ["фото", "съемк", "репортаж", "видео", "корреспондент"]):
                            continue

                        # Зарплатная вилка
                        price = "По договорённости"
                        sal_min = v.get("salary_min")
                        sal_max = v.get("salary_max")
                        if sal_min and sal_max and sal_min != sal_max:
                            price = f"{sal_min:,} – {sal_max:,} ₽".replace(",", " ")
                        elif sal_min:
                            price = f"от {sal_min:,} ₽".replace(",", " ")
                        elif sal_max:
                            price = f"до {sal_max:,} ₽".replace(",", " ")

                        # Теги
                        tags = ["Репортаж"]
                        if any(s in name_lower for s in ["спорт", "турнир", "матч", "арен"]):
                            tags.append("Спорт")
                        else:
                            tags.append("События")

                        duty = v.get("duty") or "Репортажная фотосъемка мероприятий и подготовка фотоматериалов."
                        duty_clean = duty.replace("<p>", "").replace("</p>", "").replace("<br>", " ").strip()

                        items.append({
                            "id": v_id,
                            "source": "Работа России",
                            "title": name,
                            "company": v.get("company", {}).get("name", "Организация / Клуб"),
                            "location": reg_name,
                            "price": price,
                            "tags": tags,
                            "url": v.get("vac_url", "https://trudvsem.ru"),
                            "is_urgent": False,
                            "deadline": "Актуально",
                            "description": duty_clean[:260] + ("..." if len(duty_clean) > 260 else "")
                        })
            except Exception as e:
                print(f"Ошибка запроса ТрудВсем ({q}): {e}")
            time.sleep(0.2)

    print(f"-> Итого собрано с ТрудВсем: {len(items)}")
    return items

def parse_avito():
    print("-> Сбор с Авито (Москва и МО)...")
    items = []
    
    # Точечные запросы на Авито
    queries = [
        "спортивный+фотограф",
        "фотограф+на+турнир",
        "фотограф+на+мероприятие",
        "фотограф+соревнований"
    ]
    seen_ids = set()

    for q in queries:
        url = f"https://www.avito.ru/moskva_i_mo/vakansii?q={q}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.select('div[data-marker="item"]')
                for card in cards[:12]:
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

                    loc = geo_el.get_text(strip=True) if geo_el else "Москва / МО"

                    tags = ["Авито", "Репортаж"]
                    if any(w in title.lower() for w in ["спорт", "турнир", "матч", "футбол", "хоккей"]):
                        tags.append("Спорт")

                    items.append({
                        "id": v_id,
                        "source": "Авито",
                        "title": title,
                        "company": "Заказчик с Авито",
                        "location": loc,
                        "price": price,
                        "tags": tags,
                        "url": link,
                        "is_urgent": any(w in title.lower() for w in ["срочно", "турнир", "выходные"]),
                        "deadline": "Свежее",
                        "description": "Заказ на фотосъемку с Авито. Нажмите «Откликнуться», чтобы открыть объявление."
                    })
        except Exception as e:
            print(f"Ошибка Авито ({q}): {e}")
        time.sleep(0.8)

    print(f"-> Итого собрано с Авито: {len(items)}")
    return items

def main():
    trud_jobs = parse_trudvsem()
    avito_jobs = parse_avito()
    all_jobs = trud_jobs + avito_jobs

    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    print(f"Готово! В vacancies.json записано объектов: {len(all_jobs)}")

if __name__ == "__main__":
    main()

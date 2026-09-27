import json
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def parse_hh():
    print("-> Сбор с HeadHunter...")
    items = []
    
    # Расширенный спектр запросов
    queries = [
        "фотограф",
        "репортажный фотограф",
        "фотограф на мероприятие",
        "фотограф на турнир",
        "спортивный фотограф",
        "фотокорреспондент",
        "фотограф соревнований"
    ]
    seen_ids = set()

    # 1 - Москва, 2014 - Московская область
    for area_id in [1, 2014]:
        for q in queries:
            url = "https://api.hh.ru/vacancies"
            params = {
                "text": q,
                "area": area_id,
                "per_page": 20,
                "order_by": "publication_time",
            }
            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for vac in data.get("items", []):
                        v_id = f"hh_{vac['id']}"
                        if v_id in seen_ids:
                            continue
                        seen_ids.add(v_id)

                        name = vac.get("name", "Фотограф")

                        # Зарплатная вилка
                        price = "По договорённости"
                        sal = vac.get("salary")
                        if sal:
                            cur = "₽" if sal.get("currency") in ["RUR", "RUB", None] else sal.get("currency")
                            if sal.get("from") and sal.get("to"):
                                price = f"{sal['from']:,} – {sal['to']:,} {cur}".replace(",", " ")
                            elif sal.get("from"):
                                price = f"от {sal['from']:,} {cur}".replace(",", " ")
                            elif sal.get("to"):
                                price = f"до {sal['to']:,} {cur}".replace(",", " ")

                        # Определяем теги
                        tags = ["Репортаж"]
                        name_lower = name.lower()
                        if any(w in name_lower for w in ["спорт", "турнир", "матч", "соревнован"]):
                            tags.append("Спорт")
                        elif any(w in name_lower for w in ["мероприят", "событи", "ивент", "event"]):
                            tags.append("Ивенты")
                        else:
                            tags.append("Фотосъемка")

                        schedule = vac.get("schedule", {}).get("name")
                        if schedule:
                            tags.append(schedule)

                        snippet = vac.get("snippet", {})
                        desc = snippet.get("requirement") or snippet.get("responsibility") or "Репортажная и событийная съемка."
                        desc = desc.replace("<highlighttext>", "").replace("</highlighttext>", "")

                        items.append({
                            "id": v_id,
                            "source": "HH",
                            "title": name,
                            "company": vac.get("employer", {}).get("name", "Компания"),
                            "location": vac.get("area", {}).get("name", "Москва / МО"),
                            "price": price,
                            "tags": tags[:3],
                            "url": vac.get("alternate_url", "https://hh.ru"),
                            "is_urgent": any(w in name_lower for w in ["срочно", "выезд", "турнир", "выходного"]),
                            "deadline": "Свежее",
                            "description": desc
                        })
            except Exception as e:
                print(f"Ошибка запроса HH ({q}): {e}")
            time.sleep(0.15)

    print(f"-> Итого собрано с HH: {len(items)}")
    return items

def parse_trudvsem():
    print("-> Сбор с портала ТрудВсем (Работа России)...")
    items = []
    # 77 - Москва, 50 - Московская область
    for region_code in ["7700000000000", "5000000000000"]:
        url = f"https://opendata.trudvsem.ru/api/v1/vacancies/region/{region_code}"
        params = {"text": "фотограф", "limit": 40}
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                vacancies = data.get("results", {}).get("vacancies", [])
                for entry in vacancies:
                    v = entry.get("vacancy", {})
                    v_id = f"trud_{v.get('id', hash(v.get('vac_url', '')))}"
                    
                    price = "По договорённости"
                    sal_min = v.get("salary_min")
                    sal_max = v.get("salary_max")
                    if sal_min and sal_max and sal_min != sal_max:
                        price = f"{sal_min:,} – {sal_max:,} ₽".replace(",", " ")
                    elif sal_min:
                        price = f"от {sal_min:,} ₽".replace(",", " ")
                    elif sal_max:
                        price = f"до {sal_max:,} ₽".replace(",", " ")

                    items.append({
                        "id": v_id,
                        "source": "Job / ТрудВсем",
                        "title": v.get("job-name", "Фотограф репортажа / мероприятий"),
                        "company": v.get("company", {}).get("name", "Организация / Клуб"),
                        "location": "Москва и МО",
                        "price": price,
                        "tags": ["Репортаж", "События"],
                        "url": v.get("vac_url", "https://trudvsem.ru"),
                        "is_urgent": False,
                        "deadline": "Актуально",
                        "description": v.get("duty", "Съемка мероприятий и оперативная подготовка фотоматериалов.")
                    })
        except Exception as e:
            print(f"Ошибка ТрудВсем: {e}")
    print(f"-> Итого собрано с ТрудВсем: {len(items)}")
    return items

def main():
    hh_jobs = parse_hh()
    trud_jobs = parse_trudvsem()
    all_jobs = hh_jobs + trud_jobs

    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    print(f"Всего сохранено вакансий: {len(all_jobs)}")

if __name__ == "__main__":
    main()

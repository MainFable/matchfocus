import json
import time
import requests

HEADERS = {
    "User-Agent": "MatchFocusBot/1.0 (contact: support@matchfocus.local)",
    "Accept": "application/json",
}

def parse_hh():
    print("-> Сбор с HeadHunter...")
    items = []
    # Расширенный список релевантных запросов для спортивного и динамичного репортажа
    queries = [
        "спортивный фотограф",
        "фотограф спорт",
        "репортажный фотограф",
        "фотограф мероприятий",
        "фотограф матчей",
        "фотокорреспондент",
        "видеооператор спорт"
    ]
    seen_ids = set()

    # 1 - Москва, 2014 - Московская область
    for area_id in [1, 2014]:
        for q in queries:
            url = "https://api.hh.ru/vacancies"
            params = {
                "text": q,
                "area": area_id,
                "per_page": 15,
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

                        # Обработка вилки гонорара
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

                        # Теги специализации
                        emp = vac.get("employment", {}).get("name", "Репортаж")
                        schedule = vac.get("schedule", {}).get("name", "Проектная работа")
                        tags = [t for t in [emp, schedule, "Спорт / Экшн"] if t]

                        snippet = vac.get("snippet", {})
                        resp_text = snippet.get("requirement") or snippet.get("responsibility") or "Съемка спортивных соревнований, турниров и динамичных событий."
                        # Очистка от подсветки тегов HH
                        clean_desc = resp_text.replace("<highlighttext>", "").replace("</highlighttext>", "")

                        items.append({
                            "id": v_id,
                            "source": "HH",
                            "title": vac.get("name", "Спортивный фотограф"),
                            "company": vac.get("employer", {}).get("name", "Спортивная организация"),
                            "location": vac.get("area", {}).get("name", "Москва / МО"),
                            "price": price,
                            "tags": tags[:3],
                            "url": vac.get("alternate_url", "https://hh.ru"),
                            "is_urgent": any(w in vac.get("name", "").lower() for w in ["срочно", "выезд", "турнир"]),
                            "deadline": "Свежее",
                            "description": clean_desc
                        })
            except Exception as e:
                print(f"Ошибка запроса HH ({q}): {e}")
            time.sleep(0.2)

    print(f"-> Собрано с HH: {len(items)}")
    return items

def parse_trudvsem():
    print("-> Сбор с портала Работа России / ТрудВсем...")
    items = []
    # Регионы: 77 - Москва, 50 - Московская область
    for region_code in ["7700000000000", "5000000000000"]:
        url = f"http://opendata.trudvsem.ru/api/v1/vacancies/region/{region_code}"
        params = {"text": "фотограф", "limit": 20}
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
                        "company": v.get("company", {}).get("name", "Гос. учреждение / Клуб"),
                        "location": "Москва и МО",
                        "price": price,
                        "tags": ["Гос. сектор / Клубы", "Репортаж"],
                        "url": v.get("vac_url", "https://trudvsem.ru"),
                        "is_urgent": False,
                        "deadline": "Актуально",
                        "description": v.get("duty", "Съемка спортивных мероприятий и подготовка репортажного материала.")
                    })
        except Exception as e:
            print(f"Ошибка ТрудВсем: {e}")
    print(f"-> Собрано с ТрудВсем: {len(items)}")
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

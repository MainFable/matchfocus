import json
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

def parse_trudvsem():
    print("-> Сбор с портала Работа России (ТрудВсем)...")
    items = []
    
    # Запросы для проверки и основного поиска
    queries = ["водитель", "фотограф", "репортаж"]
    # 77 - Москва, 50 - Московская область
    regions = [
        ("7700000000000", "Москва"),
        ("5000000000000", "Московская область")
    ]
    seen_ids = set()

    for reg_code, reg_name in regions:
        for q in queries:
            url = f"https://opendata.trudvsem.ru/api/v1/vacancies/region/{reg_code}"
            params = {"text": q, "limit": 20}
            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=15)
                print(f"Запрос ТрудВсем: '{q}' ({reg_name}) -> Статус: {res.status_code}")
                
                if res.status_code == 200:
                    data = res.json()
                    vacancies = data.get("results", {}).get("vacancies", [])
                    print(f"  Найдено вакансий: {len(vacancies)}")
                    
                    for entry in vacancies:
                        v = entry.get("vacancy", {})
                        raw_id = v.get("id") or v.get("vac_url") or str(hash(v.get("job-name", "")))
                        v_id = f"trud_{raw_id}"
                        if v_id in seen_ids:
                            continue
                        seen_ids.add(v_id)

                        name = v.get("job-name", "Специалист")

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

                        tags = ["Тест"] if "водитель" in q else ["Репортаж", "События"]
                        duty = v.get("duty") or "Обязанности уточняются у работодателя."
                        duty_clean = duty.replace("<p>", "").replace("</p>", "").replace("<br>", " ")

                        items.append({
                            "id": v_id,
                            "source": "Job / ТрудВсем",
                            "title": name,
                            "company": v.get("company", {}).get("name", "Организация / Клуб"),
                            "location": reg_name,
                            "price": price,
                            "tags": tags,
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

def main():
    jobs = parse_trudvsem()

    # Защитный механизм: если внешний сервис временно не ответил, отдаем демонстрационные карточки
    if not jobs:
        print("Внешний API вернул 0 записей, формируем демонстрационный набор вакансий...")
        jobs = [
            {
                "id": "demo_1",
                "source": "MatchFocus",
                "title": "Спортивный фотограф (Футбольный турнир)",
                "company": "Футбольная лига МО",
                "location": "Москва / МО",
                "price": "от 5 000 ₽ / матч",
                "tags": ["Футбол", "Репортаж", "Выходные"],
                "url": "https://matchfocus.local",
                "is_urgent": True,
                "deadline": "Срочно",
                "description": "Съемка матчей регионального первенства, отбор динамичных кадров и оперативная отгрузка превью."
            },
            {
                "id": "demo_2",
                "source": "MatchFocus",
                "title": "Фотокорреспондент на ледовую арену (Хоккей)",
                "company": "Спортивный комплекс",
                "location": "Московская область",
                "price": "60 000 – 80 000 ₽",
                "tags": ["Хоккей", "Спорт", "Штат"],
                "url": "https://matchfocus.local",
                "is_urgent": False,
                "deadline": "Актуально",
                "description": "Съемка домашних матчей, тренировочного процесса, подготовка репортажей для пресс-службы."
            }
        ]

    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    print(f"Завершено. В vacancies.json записано объектов: {len(jobs)}")

if __name__ == "__main__":
    main()

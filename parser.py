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
    
    # Добавили тестовый запрос 'водитель' первым в списке
    queries = [
        "водитель",
        "фотограф",
        "репортажный фотограф",
        "спортивный фотограф"
    ]
    seen_ids = set()

    for q in queries:
        # 1 - Москва, 2014 - МО
        for area_id in [1, 2014]:
            url = "https://api.hh.ru/vacancies"
            params = {
                "text": q,
                "area": area_id,
                "per_page": 20,
                "order_by": "publication_time",
            }
            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=10)
                print(f"Запрос HH: '{q}' (регион {area_id}) -> Статус: {res.status_code}")
                
                if res.status_code == 200:
                    data = res.json()
                    vac_list = data.get("items", [])
                    print(f"  Найдено вакансий в ответе: {len(vac_list)}")
                    
                    for vac in vac_list:
                        v_id = f"hh_{vac['id']}"
                        if v_id in seen_ids:
                            continue
                        seen_ids.add(v_id)

                        name = vac.get("name", "Вакансия")

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

                        tags = ["Тест"] if "водитель" in q.lower() else ["Репортаж"]
                        schedule = vac.get("schedule", {}).get("name")
                        if schedule:
                            tags.append(schedule)

                        snippet = vac.get("snippet", {})
                        desc = snippet.get("requirement") or snippet.get("responsibility") or "Описание отсутствует."
                        desc = desc.replace("<highlighttext>", "").replace("</highlighttext>", "")

                        items.append({
                            "id": v_id,
                            "source": "HH",
                            "title": name,
                            "company": vac.get("employer", {}).get("name", "Прямой работодатель"),
                            "location": vac.get("area", {}).get("name", "Москва / МО"),
                            "price": price,
                            "tags": tags[:3],
                            "url": vac.get("alternate_url", "https://hh.ru"),
                            "is_urgent": False,
                            "deadline": "Свежее",
                            "description": desc
                        })
                else:
                    print(f"  Ошибка HH ответа: {res.text[:200]}")
            except Exception as e:
                print(f"Исключение при запросе HH ({q}): {e}")
            time.sleep(0.2)

    print(f"-> Итого сохранено с HH: {len(items)}")
    return items

def main():
    all_jobs = parse_hh()
    with open("vacancies.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)
    print(f"Готово! В файл vacancies.json записано объектов: {len(all_jobs)}")

if __name__ == "__main__":
    main()

import httpx

def main():
    r = httpx.get('http://localhost:8080/api/config')
    print('Config status:', r.status_code)
    print('Sources in config:', list(r.json()['sources'].keys()))

    r2 = httpx.get('http://localhost:8080/api/news?source=moneycontrol&limit=5')
    print('Moneycontrol status:', r2.status_code)
    data = r2.json()
    print('Moneycontrol count:', data['count'])
    print('Interactive sources counts:', data['filter_counts']['sources'])
    print("\n--- Moneycontrol by Location ---")
    for loc in ['bengaluru', 'odisha', 'india', 'global']:
        r = httpx.get(f'http://localhost:8080/api/news?location={loc}&source=moneycontrol')
        d = r.json()
        sample = d['articles'][0]['title'][:70] if d['articles'] else 'None'
        print(f"Moneycontrol + {loc.title()}: {d['count']} stories | Sample: {sample}")

    print("\n--- Moneycontrol by Topic ---")
    for top in ['job_market', 'technology', 'entertainment', 'general']:
        r = httpx.get(f'http://localhost:8080/api/news?topic={top}&source=moneycontrol')
        d = r.json()
        sample = d['articles'][0]['title'][:70] if d['articles'] else 'None'
        print(f"Moneycontrol + {top.title()}: {d['count']} stories | Sample: {sample}")

if __name__ == '__main__':
    main()

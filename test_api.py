import asyncio
from httpx import AsyncClient, ASGITransport
from main import app

async def run_api_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("1. Testing GET /api/config...")
        resp = await client.get("/api/config")
        assert resp.status_code == 200, f"Failed: {resp.status_code}"
        cfg = resp.json()
        print(f"   Locations found: {list(cfg['locations'].keys())}")
        print(f"   Topics found: {list(cfg['topics'].keys())}")

        print("\n2. Testing GET /api/news (All locations, Priority feed)...")
        resp = await client.get("/api/news?location=all&topic=priority&source=all")
        assert resp.status_code == 200
        data = resp.json()
        print(f"   Success! Articles returned: {data['count']}")
        print(f"   Interactive counts: Locations: {data['filter_counts']['locations']}, Sources: {data['filter_counts']['sources']}")

        print("\n3. Testing Location=Bengaluru + Topic=Technology...")
        resp = await client.get("/api/news?location=bengaluru&topic=technology&source=all")
        assert resp.status_code == 200
        beng_tech = resp.json()
        print(f"   Success! Bengaluru Tech articles: {beng_tech['count']}")
        if beng_tech['articles']:
            print(f"   Sample: [{beng_tech['articles'][0]['source_name']}] {beng_tech['articles'][0]['title']}")

        print("\n4. Testing Location=Odisha + Source=X (Twitter)...")
        resp = await client.get("/api/news?location=odisha&topic=priority&source=x")
        assert resp.status_code == 200
        odisha_x = resp.json()
        print(f"   Success! Odisha X articles: {odisha_x['count']}")
        if odisha_x['articles']:
            print(f"   Sample: {odisha_x['articles'][0]['title']}")

        print("\n5. Testing Location=India + Topic=Job Market...")
        resp = await client.get("/api/news?location=india&topic=job_market&source=all")
        assert resp.status_code == 200
        india_jobs = resp.json()
        print(f"   Success! India Job Market articles: {india_jobs['count']}")

        print("\n6. Testing Source=Moneycontrol...")
        resp = await client.get("/api/news?location=all&topic=priority&source=moneycontrol")
        assert resp.status_code == 200
        mc_news = resp.json()
        print(f"   Success! Moneycontrol articles: {mc_news['count']}")
        if mc_news['articles']:
            print(f"   Sample: [{mc_news['articles'][0]['source_name']}] {mc_news['articles'][0]['title']}")
            print(f"   Image URL: {mc_news['articles'][0]['image_url'][:60]}...")
            print(f"   Location: {mc_news['articles'][0]['location_name']}, Topic: {mc_news['articles'][0]['topic_name']}")

        print("\n7. Testing UI index.html...")
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Location Filter" in resp.text
        assert "Category & Priority" in resp.text
        assert "scrapingBanner" in resp.text
        print("   Success! Modern 3-tier UI and scrapingBanner verified.")

        print("\n8. Testing POST /api/news/refresh with active filters...")
        ref_resp = await client.post("/api/news/refresh?location=bengaluru&topic=technology&source=all&limit=20")
        assert ref_resp.status_code == 200
        assert "no-cache" in ref_resp.headers.get("Cache-Control", "")
        ref_data = ref_resp.json()
        assert ref_data["status"] == "success"
        assert "articles" in ref_data
        assert "filter_counts" in ref_data
        assert ref_data["last_refreshed"] > 0
        print(f"   Success! Refreshed articles returned: {ref_data['count']}")
        print(f"   Cache-Control header verified: {ref_resp.headers.get('Cache-Control')}")

    print("\n All 3-tier interactive filter & live refresh tests PASSED successfully!")

if __name__ == "__main__":
    asyncio.run(run_api_tests())

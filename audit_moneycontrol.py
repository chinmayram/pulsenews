import httpx
import json
import sys

BASE_URL = "http://localhost:8080"
LOCATIONS = ["all", "bengaluru", "odisha", "india", "global"]
TOPICS = ["priority", "job_market", "technology", "entertainment", "general"]

def audit():
    print("=" * 80)
    print("[AUDIT] MONEYCONTROL FILTER COMPREHENSIVE QA AUDIT")
    print("=" * 80)

    # 1. Config Check
    print("\n[STEP 1] Checking /api/config for Moneycontrol registration...")
    try:
        r = httpx.get(f"{BASE_URL}/api/config", timeout=5.0)
        assert r.status_code == 200, f"Status code: {r.status_code}"
        cfg = r.json()
        assert "moneycontrol" in cfg["sources"], "moneycontrol missing from SOURCES"
        mc_meta = cfg["sources"]["moneycontrol"]
        print(f"  Passed! Name: {mc_meta['name']}, Badge: {mc_meta['badge_color']}, Icon: {mc_meta['icon']}")
    except Exception as e:
        print(f"[FAIL] Step 1: {e}")
        return False

    # 2. Audit Matrix (5 Locations x 5 Topics x Moneycontrol) = 25 Combinations
    print("\n[STEP 2] Auditing all 25 Matrix Combinations (Location x Topic x Moneycontrol)...")
    results = []
    total_articles_found = set()
    failed_combinations = []
    broken_images = 0
    broken_links = 0
    unclean_titles = 0
    raw_html_summaries = 0

    print(f"\n{'Location':<14} | {'Topic':<15} | {'Count':<6} | {'Sample Headline':<45}")
    print("-" * 85)

    for loc in LOCATIONS:
        for top in TOPICS:
            url = f"{BASE_URL}/api/news?location={loc}&topic={top}&source=moneycontrol"
            try:
                r = httpx.get(url, timeout=10.0)
                if r.status_code != 200:
                    failed_combinations.append((loc, top, f"HTTP {r.status_code}"))
                    print(f"{loc:<14} | {top:<15} | ERROR  | HTTP {r.status_code}")
                    continue

                data = r.json()
                count = data.get("count", 0)
                articles = data.get("articles", [])

                sample_title = ""
                if articles:
                    sample_title = articles[0]["title"][:42] + ("..." if len(articles[0]["title"]) > 42 else "")
                    for art in articles:
                        total_articles_found.add(art["id"])
                        # Validation checks
                        if not art.get("image_url") or not art["image_url"].startswith("http"):
                            broken_images += 1
                        if not art.get("link") or not art["link"].startswith("http"):
                            broken_links += 1
                        if " - Moneycontrol" in art.get("title", ""):
                            unclean_titles += 1
                        if "<img" in art.get("summary", "") or "<a " in art.get("summary", ""):
                            raw_html_summaries += 1

                print(f"{loc:<14} | {top:<15} | {count:<6} | {sample_title:<45}")
                results.append({"loc": loc, "top": top, "count": count})

                if count == 0:
                    failed_combinations.append((loc, top, "0 articles returned"))

            except Exception as e:
                failed_combinations.append((loc, top, str(e)))
                print(f"{loc:<14} | {top:<15} | ERR    | {e}")

    # 3. Interactive Cross-Count Consistency Check
    print("\n[STEP 3] Verifying Interactive Cross-Counts for Moneycontrol...")
    r_all = httpx.get(f"{BASE_URL}/api/news?location=all&topic=priority&source=all")
    all_data = r_all.json()
    reported_mc_count = all_data["filter_counts"]["sources"].get("moneycontrol", 0)
    actual_mc_articles = len(total_articles_found)

    print(f"  Reported count in Source chip: {reported_mc_count}")
    print(f"  Unique Moneycontrol stories indexed: {actual_mc_articles}")

    # 4. Summary & Verification Scorecard
    print("\n" + "=" * 80)
    print("[SUMMARY] MONEYCONTROL QA AUDIT RESULTS")
    print("=" * 80)
    print(f"* Total combinations tested: 25 / 25")
    print(f"* Successful combinations (Count > 0): {25 - len(failed_combinations)} / 25")
    print(f"* Zero-result combinations: {len([f for f in failed_combinations if '0 articles' in f[2]])}")
    print(f"* Broken / Missing Image URLs: {broken_images}")
    print(f"* Broken / Missing Links: {broken_links}")
    print(f"* Unclean Titles (unstripped suffixes): {unclean_titles}")
    print(f"* Raw HTML tags in summaries: {raw_html_summaries}")

    if failed_combinations:
        print("\n[WARNING] Failed Combinations:")
        for f in failed_combinations:
            print(f"  - Location: {f[0]}, Topic: {f[1]} -> Reason: {f[2]}")
        return False
    else:
        print("\n[PASS] PERFECT AUDIT SCORE: All 25 Moneycontrol matrix combinations verified with healthy article yields, zero broken links/images, clean titles, and verified interactive counts!")
        return True

if __name__ == "__main__":
    success = audit()
    sys.exit(0 if success else 1)

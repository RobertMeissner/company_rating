import csv
import time

from playwright.sync_api import sync_playwright


def scrape_kununu():
    base_url = "https://www.kununu.com/de/search?location=city-66fc0692-e730-401b-a848-05048be53561&industry=6&score=4-5&spo=0"

    all_companies = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        current_page = 1
        has_more_pages = True

        while has_more_pages:
            print(f"Scraping page {current_page}...")

            # Navigate to the page
            url = base_url if current_page == 1 else f"{base_url}&page={current_page}"
            page.goto(url, wait_until="domcontentloaded")

            # Wait for content to load
            time.sleep(2)

            # Extract data from __NEXT_DATA__ script tag
            page_data = page.evaluate(
                """() => {
                const nextDataScript = document.getElementById('__NEXT_DATA__');
                if (!nextDataScript) return null;

                const jsonData = JSON.parse(nextDataScript.textContent);
                const queries = jsonData?.props?.pageProps?.dehydratedState?.queries || [];

                const profileQuery = queries.find(query => query.queryKey[0] === 'profiles');
                const profiles = profileQuery?.state?.data?.profiles || [];
                const pagination = profileQuery?.state?.data?.pagination || {};

                return {
                    profiles: profiles.map(profile => ({
                        name: profile.name,
                        rating: profile.score?.value || 'N/A',
                        slug: profile.slug,
                        countryCode: profile.countryCode
                    })),
                    pagination: pagination
                };
            }"""
            )

            if not page_data or not page_data.get("profiles"):
                print("No more data found")
                break

            # Add companies with full URLs
            for company in page_data["profiles"]:
                all_companies.append(
                    {
                        "name": company["name"],
                        "rating": company["rating"],
                        "url": f"https://www.kununu.com/{company['countryCode']}/{company['slug']}",
                    }
                )

            print(
                f"Found {len(page_data['profiles'])} companies on page {current_page}: {all_companies}"
            )

            # Check if there are more pages
            pagination = page_data.get("pagination", {})
            current_page_num = pagination.get("currentPage", current_page)
            total_pages = pagination.get("totalPages", 0)

            has_more_pages = current_page_num < total_pages
            current_page += 1

            # Be polite - add delay between requests
            time.sleep(2)

        browser.close()

    return all_companies


def save_to_csv(companies, filename="kununu_companies.csv"):
    """Save companies to CSV file"""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["COMPANY_NAME", "RATING", "URL"])

        for company in companies:
            writer.writerow([company["name"], company["rating"], company["url"]])

    print(f"\n✓ Results saved to {filename}")


def main():
    try:
        print("Starting scrape...\n")
        companies = scrape_kununu()

        # Print results
        print("\n=== RESULTS ===\n")
        print("COMPANY_NAME, RATING, URL")

        for company in companies:
            print(f"{company['name']}, {company['rating']}, {company['url']}")

        # Save to CSV
        save_to_csv(companies)

        print(f"\n✓ Scraped {len(companies)} companies")

    except Exception as error:
        print(f"Error during scraping: {error}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

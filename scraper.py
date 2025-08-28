import time
import csv
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


def get_product_detail(soup, label_text):
    """
    Finds a specific detail from the product details list.
    """
    try:
        details_section = soup.find('details', id='product-details')
        if not details_section: return "Not found"
        list_items = details_section.find_all('li')
        for item in list_items:
            item_text = item.get_text()
            if label_text in item_text:
                value = item_text.split(":", 1)[1].strip()
                return value
        return "Not found"
    except Exception:
        return "Not found"


def scrape_book_details(book_url, driver):
    """
    Scrapes the 11 data points from a single book page using the corrected selectors.
    """
    print(f"  -> Scraping: {book_url}")
    try:
        driver.get(book_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main-content")))

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        book_title = soup.find('h1', class_='book-title').get_text(strip=True)
        subtitle_tag = soup.find('h2', class_='is-size-5')
        book_sub_title = subtitle_tag.get_text(strip=True) if subtitle_tag else "Not found"
        about_book_div = soup.select_one("details#about-the-book div.content")
        about_book = about_book_div.get_text(strip=True) if about_book_div else "Not found"
        author_tag = soup.select_one("div.primary-details div.is-size-5 a")
        author = author_tag.get_text(strip=True) if author_tag else "Not found"
        about_author_div = soup.select_one("details#about-the-author div.content p")
        about_author = about_author_div.get_text(strip=True) if about_author_div else "Not found"
        image_link_tag = soup.select_one("details#resources-and-downloads a[href*='_hr.jpg']")
        image_link = image_link_tag['href'] if image_link_tag else "Not found"
        publisher_raw = get_product_detail(soup, "Publisher")
        publication_date = "Not found"
        publisher = publisher_raw
        if publisher_raw != "Not found" and "(" in publisher_raw:
            parts = publisher_raw.split("(")
            publisher = parts[0].strip()
            publication_date = parts[1].replace(")", "").strip()
        length_in_pages = get_product_detail(soup, "Length")
        isbn = get_product_detail(soup, "ISBN13")

        return {
            'book_title': book_title, 'book_sub_title': book_sub_title, 'about_book': about_book,
            'author': author, 'about_author': about_author, 'publisher': publisher,
            'publication_date': publication_date, 'length_in_pages': length_in_pages,
            'ISBN': isbn, 'image_link': image_link, 'book_link': book_url
        }
    except Exception as e:
        print(f"  [ERROR] Could not process {book_url}. Error: {e}")
        return None


def main():
    keywords_list = ["running", "endurance", "nutrition for athletes"]
    base_url = "https://www.simonandschuster.ca"

    print("Setting up undetectable browser driver...")
    driver = uc.Chrome(use_subprocess=True)
    driver.maximize_window()

    try:
        print("Navigating to base URL to handle cookie banner...")
        driver.get(base_url)
        cookie_wait = WebDriverWait(driver, 10)
        accept_button = cookie_wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        driver.execute_script("arguments[0].click();", accept_button)
        print("Cookie banner accepted.")
        time.sleep(2)
    except TimeoutException:
        print("Cookie banner not found or already accepted.")
    except Exception as e:
        print(f"An error occurred while handling the cookie banner: {e}")

    all_scraped_books = []
    scraped_urls = set()

    for keyword in keywords_list:
        print(f"\n--- Searching for keyword: '{keyword}' ---\n")
        try:
            driver.get(base_url)
            wait = WebDriverWait(driver, 15)
            search_bar = wait.until(EC.element_to_be_clickable((By.ID, "header-search-bar")))
            search_bar.click()
            search_bar.send_keys(keyword)
            search_bar.send_keys(Keys.RETURN)

            print("Waiting for book results...")
            wait.until(EC.visibility_of_element_located((By.ID, "search-results-container")))
            print("Book results loaded successfully.")

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            book_list_items = soup.select("div.search-result-item")
            if not book_list_items:
                print(f"No books found on the results page for '{keyword}'.")
                continue

            print(f"Found {len(book_list_items)} book items on the page.")
            for item in book_list_items:
                link_tag = item.find('a', href=True)

                # --- CORRECTED LINK CHECK ---
                # Check if the link is a full book URL instead of a relative one
                if link_tag and "/books/" in link_tag['href']:
                    # The link is already the full URL, no need to add base_url
                    full_url = link_tag['href']

                    if full_url not in scraped_urls:
                        scraped_urls.add(full_url)
                        book_data = scrape_book_details(full_url, driver)
                        if book_data:
                            all_scraped_books.append(book_data)

        except TimeoutException:
            print(f"[TIMEOUT] A timeout occurred for keyword '{keyword}'. Skipping.")
            driver.save_screenshot(f"debug_timeout_screenshot_{keyword}.png")
            continue
        except Exception as e:
            print(f"An error occurred while processing '{keyword}': {e}")
            continue

    driver.quit()

    if not all_scraped_books:
        print("No books were successfully scraped across all keywords.")
        return

    output_filename = "scraped_running_books.csv"
    print(f"\nScraping complete. Saving {len(all_scraped_books)} unique books to {output_filename}...")
    fieldnames = ['book_title', 'book_sub_title', 'about_book', 'author', 'about_author',
                  'publisher', 'publication_date', 'length_in_pages', 'ISBN', 'image_link', 'book_link']
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_scraped_books)

    print(f"Success! Your file '{output_filename}' is ready.")


if __name__ == "__main__":
    main()
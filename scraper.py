import requests
from bs4 import BeautifulSoup
import time
import csv


def get_product_detail(soup, label_text):
    """
    Helper function to find a specific detail from the product details section.
    """
    try:
        details_section = soup.find('div', id='product-details-content')
        if not details_section:
            return "Not found"

        items = details_section.find_all('div', class_='pdp-about-item')
        for item in items:
            if item.strong and label_text in item.strong.get_text(strip=True):
                value_span = item.strong.find_next_sibling('span')
                if value_span:
                    return value_span.get_text(strip=True).replace('\n', ' ').replace('\r', ' ')
        return "Not found"
    except Exception:
        return "Not found"


def scrape_book_details(book_url, headers):
    """
    Scrapes 11 specific data points from a single book page.
    """
    print(f"  -> Scraping: {book_url}")
    try:
        response = requests.get(book_url, headers=headers)
        response.raise_for_status()  # Check for request errors

        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Book Title
        book_title = soup.find('h1', class_='book-title').get_text(strip=True)

        # 2. Book Subtitle (handles cases where it's missing)
        subtitle_tag = soup.find('h2', class_='book-subtitle')
        book_sub_title = subtitle_tag.get_text(strip=True) if subtitle_tag else "Not found"

        # 3. About Book
        about_book_div = soup.find('div', id='book-description-content')
        about_book = about_book_div.get_text(strip=True) if about_book_div else "Not found"

        # 4. Author
        author_tag = soup.find('span', class_='author-name')
        author = author_tag.get_text(strip=True) if author_tag else "Not found"

        # 5. About Author (handles cases where it's missing)
        about_author_div = soup.find('div', id='author-bio-content')
        about_author = about_author_div.get_text(strip=True) if about_author_div else "Not found"

        # 6. Publisher (using helper function)
        publisher = get_product_detail(soup, "Publisher")

        # 7. Publication Date (using helper function)
        publication_date = get_product_detail(soup, "Publication Date")

        # 8. Length in Pages (using helper function)
        length_in_pages = get_product_detail(soup, "Pages")

        # 9. ISBN (using helper function)
        isbn = get_product_detail(soup, "ISBN-13")

        # 10. Image Link
        image_tag = soup.find('div', class_='book-cover-container').find('img')
        image_link = image_tag['src'] if image_tag else "Not found"

        # 11. Book Link
        book_link = book_url

        return {
            'book_title': book_title,
            'book_sub_title': book_sub_title,
            'about_book': about_book,
            'author': author,
            'about_author': about_author,
            'publisher': publisher,
            'publication_date': publication_date,
            'length_in_pages': length_in_pages,
            'ISBN': isbn,
            'image_link': image_link,
            'book_link': book_link
        }

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Could not fetch {book_url}: {e}")
        return None
    except AttributeError as e:
        print(f"  [ERROR] Could not find a required element on {book_url}: {e}")
        return None


def main():
    """
    Main function to crawl search results for a list of keywords and save data to CSV.
    """
    # Define your list of keywords here
    keywords_list = ["running", "endurance", "nutrition for athletes"]

    base_url = "https://www.simonandschuster.ca"
    headers = {
        'User-Agent': 'BookScraperBot/1.0 (for educational project)'
    }

    all_scraped_books = []
    scraped_urls = set()  # To prevent scraping the same book twice

    # Loop through each keyword in your list
    for keyword in keywords_list:
        # URL-encode the keyword to handle spaces, e.g., "nutrition for athletes"
        formatted_keyword = requests.utils.quote(keyword)
        search_url = f"{base_url}/search/books/Category-Health-Fitness/_/N-fn4/Ntt-{formatted_keyword}"

        print(f"\n--- Fetching search results for '{keyword}' ---\n")
        response = requests.get(search_url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to retrieve search page for '{keyword}'. Status code: {response.status_code}")
            continue  # Skip to the next keyword

        soup = BeautifulSoup(response.content, 'html.parser')

        book_links_container = soup.find('ul', class_='book-grid-listing')
        book_links = book_links_container.find_all('a') if book_links_container else []

        if not book_links:
            print(f"Could not find any book links for '{keyword}'.")
            continue

        for link in book_links:
            if 'href' in link.attrs and link['href'].startswith('/books/'):
                full_url = base_url + link['href']
                if full_url not in scraped_urls:
                    scraped_urls.add(full_url)  # Add URL to set to mark it as scraped
                    book_data = scrape_book_details(full_url, headers)
                    if book_data:
                        all_scraped_books.append(book_data)

                    # Respectful delay between requests
                    time.sleep(1.5)

    if not all_scraped_books:
        print("No books were successfully scraped across all keywords.")
        return

    # Save all collected data to a single CSV file
    output_filename = "scraped_running_books.csv"
    print(f"\nScraping complete. Saving {len(all_scraped_books)} unique books to {output_filename}...")

    fieldnames = [
        'book_title', 'book_sub_title', 'about_book', 'author', 'about_author',
        'publisher', 'publication_date', 'length_in_pages', 'ISBN',
        'image_link', 'book_link'
    ]

    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_scraped_books)

    print("Done! Your consolidated file is ready.")


if __name__ == "__main__":
    main()
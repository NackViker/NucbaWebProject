import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time

BASE_URL = "https://tassben.mitiendanube.com"
LIST_URL = f"{BASE_URL}/productos/"
OUTPUT_FILE = "productos_tassben.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProductScraper/1.0; +https://tassben.mitiendanube.com)"
}

def get_product_links(url):
    """Devuelve una lista con las URLs de productos de una página de listado."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/productos/" in href and href != "/productos/":
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)

    return sorted(list(links))

def get_next_page(soup):
    """Encuentra la URL de la siguiente página de productos (si existe)."""
    next_link = soup.find("a", string=lambda s: s and "Sig" in s)
    if next_link and next_link.get("href"):
        return urljoin(BASE_URL, next_link["href"])
    return None

def parse_product(url):
    """Extrae datos principales de un producto."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
    price_tag = soup.find("span", class_="price") or soup.find("span", string=lambda s: "$" in str(s))
    price = price_tag.get_text(strip=True) if price_tag else ""
    desc_tag = soup.select_one(".product-description, .descripcion, .description")
    description = desc_tag.get_text(" ", strip=True) if desc_tag else ""
    images = [urljoin(BASE_URL, img["src"]) for img in soup.find_all("img", src=True)]

    return {
        "nombre": title,
        "precio": price,
        "descripcion": description,
        "url": url,
        "imagenes": ", ".join(images)
    }

def scrape_all_products():
    """Recorre todas las páginas y guarda los productos en un CSV."""
    print("Iniciando scrapeo...")
    all_products = []
    page_url = LIST_URL
    seen = set()

    while page_url:
        print(f"📄 Página: {page_url}")
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        links = get_product_links(page_url)
        print(f" - Encontrados {len(links)} productos en esta página")

        for link in links:
            if link in seen:
                continue
            seen.add(link)
            try:
                product = parse_product(link)
                all_products.append(product)
                print(f"   ✅ {product['nombre']}")
                time.sleep(1)  # pausa corta para no sobrecargar el sitio
            except Exception as e:
                print(f"   ⚠️ Error al procesar {link}: {e}")

        page_url = get_next_page(soup)
        time.sleep(2)

    # Guardar CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre", "precio", "descripcion", "url", "imagenes"])
        writer.writeheader()
        writer.writerows(all_products)

    print(f"\n✅ Listo. Guardado en {OUTPUT_FILE} con {len(all_products)} productos.")

if __name__ == "__main__":
    scrape_all_products()

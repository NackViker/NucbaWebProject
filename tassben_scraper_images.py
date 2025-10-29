import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import json
import time
import os
from pathlib import Path

BASE_URL = "https://tassben.mitiendanube.com"
LIST_URL = f"{BASE_URL}/productos/"

# Carpetas locales
BASE_DIR = Path("products")
IMG_DIR = BASE_DIR / "images"
BASE_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

CSV_FILE = BASE_DIR / "productos_tassben.csv"
JSON_FILE = BASE_DIR / "productos_tassben.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProductScraper/3.0; +https://tassben.mitiendanube.com)"
}

def get_page_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def get_product_links(soup):
    """Extrae URLs de productos desde una página HTML."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/productos/" in href and href != "/productos/":
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)
    return sorted(list(links))

def get_next_page(soup):
    """Detecta la URL de la página siguiente (si existe)."""
    next_link = soup.find("a", string=lambda s: s and ("Sig" in s or "→" in s))
    if next_link and next_link.get("href"):
        return urljoin(BASE_URL, next_link["href"])
    return None

def download_image(url, product_name):
    """Descarga una imagen y la guarda localmente."""
    try:
        filename = f"{product_name[:50].replace(' ', '_').replace('/', '_')}_{os.path.basename(url)}"
        filepath = IMG_DIR / filename
        if not filepath.exists():
            img_data = requests.get(url, headers=HEADERS, timeout=20)
            img_data.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(img_data.content)
        return str(filepath)
    except Exception as e:
        print(f"   ⚠️ Error descargando {url}: {e}")
        return None

def parse_product(url):
    """Extrae datos principales de un producto individual."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
    price_tag = soup.find("span", class_="price") or soup.find("span", string=lambda s: "$" in str(s))
    price = price_tag.get_text(strip=True) if price_tag else ""
    desc_tag = soup.select_one(".product-description, .descripcion, .description")
    description = desc_tag.get_text(" ", strip=True) if desc_tag else ""
    image_urls = [urljoin(BASE_URL, img["src"]) for img in soup.find_all("img", src=True)]

    # Descargar imágenes localmente
    local_images = []
    for img_url in image_urls:
        local_path = download_image(img_url, title)
        if local_path:
            local_images.append(local_path)

    return {
        "nombre": title,
        "precio": price,
        "descripcion": description,
        "url": url,
        "imagenes": local_images
    }

def scrape_all_products():
    print("🚀 Iniciando scrapeo completo de productos...")
    all_products = []
    seen = set()
    page_url = LIST_URL

    while page_url:
        print(f"\n📄 Página: {page_url}")
        soup = get_page_soup(page_url)
        product_links = get_product_links(soup)
        print(f" - Encontrados {len(product_links)} productos en esta página")

        for link in product_links:
            if link in seen:
                continue
            seen.add(link)
            try:
                data = parse_product(link)
                all_products.append(data)
                print(f"   ✅ {data['nombre']}")
                time.sleep(1)
            except Exception as e:
                print(f"   ⚠️ Error en {link}: {e}")

        next_page = get_next_page(soup)
        if not next_page:
            break
        page_url = next_page
        time.sleep(2)

    # Guardar CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre", "precio", "descripcion", "url", "imagenes"])
        writer.writeheader()
        for p in all_products:
            writer.writerow({
                "nombre": p["nombre"],
                "precio": p["precio"],
                "descripcion": p["descripcion"],
                "url": p["url"],
                "imagenes": ", ".join(p["imagenes"])
            })
    print(f"\n💾 Archivo CSV guardado en: {CSV_FILE}")

    # Guardar JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"💾 Archivo JSON guardado en: {JSON_FILE}")

    print(f"\n✅ Total productos guardados: {len(all_products)}")
    print(f"🖼️ Imágenes guardadas en: {IMG_DIR}")

if __name__ == "__main__":
    scrape_all_products()

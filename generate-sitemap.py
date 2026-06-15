#!/usr/bin/env python3
"""
generate-sitemap.py
===================
Script untuk generate sitemap XML otomatis berdasarkan struktur folder.
Cara pakai: python generate-sitemap.py
"""

import os
import json
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# ==========================================
# KONFIGURASI
# ==========================================

BASE_URL = "https://rizchbali.com"
VERCEL_JSON = "vercel.json"
OUTPUT_DIR = "."

# File/folder yang diabaikan
IGNORE_FILES = {"blog-index.html", "generate-sitemap.py", "generate-sitemap-pro.py"}
IGNORE_FOLDERS = {".git", "images", "node_modules"}

# Prioritas default
PRIORITY = {
    "homepage": "1.0",
    "artikel_index": "0.9",
    "artikel": "0.8",
    "layanan_index": "0.9",
    "layanan": "0.8",
}

# ==========================================
# FUNGSI HELPER
# ==========================================

def get_lastmod(filepath):
    """Ambil tanggal modifikasi terakhir file."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def create_url_element(parent, loc, lastmod, changefreq, priority):
    """Buat elemen <url> untuk sitemap."""
    url = SubElement(parent, "url")
    SubElement(url, "loc").text = loc
    SubElement(url, "lastmod").text = lastmod
    SubElement(url, "changefreq").text = changefreq
    SubElement(url, "priority").text = priority
    return url

def prettify_xml(elem):
    """Format XML jadi rapi."""
    rough_string = tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def write_sitemap(filename, urls):
    """Tulis sitemap ke file."""
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    
    for url_data in urls:
        create_url_element(
            urlset,
            url_data["loc"],
            url_data["lastmod"],
            url_data["changefreq"],
            url_data["priority"]
        )
    
    xml_string = prettify_xml(urlset)
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_string)
    
    print(f"  ✅ {filename} ({len(urls)} URL)")

# ==========================================
# BACA VERCEL.JSON (URL LAMA YANG SUDAH INDEX)
# ==========================================

def get_vercel_urls():
    """Ambil URL clean dari vercel.json."""
    urls = []
    try:
        with open(VERCEL_JSON, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        for rewrite in config.get("rewrites", []):
            source = rewrite.get("source", "")
            dest = rewrite.get("destination", "")
            
            # Hanya ambil URL yang ke file .html (bukan folder)
            if source.startswith("/") and not source.endswith("/") and ".html" in dest:
                # Skip yang sudah ada handler khusus
                if source in {"/artikel"}:
                    continue
                    
                urls.append({
                    "loc": f"{BASE_URL}{source}",
                    "lastmod": get_lastmod(dest.lstrip("/")),
                    "changefreq": "monthly",
                    "priority": "0.8"
                })
    except FileNotFoundError:
        print(f"  ⚠️  {VERCEL_JSON} tidak ditemukan")
    
    return urls

# ==========================================
# SCAN FOLDER ARTIKEL
# ==========================================

def scan_artikel_folder():
    """Scan folder artikel/ untuk artikel baru."""
    urls = []
    base_path = "artikel"
    
    if not os.path.exists(base_path):
        return urls
    
    # Index artikel (blog-index.html)
    blog_index = os.path.join(base_path, "blog-index.html")
    if os.path.exists(blog_index):
        urls.append({
            "loc": f"{BASE_URL}/artikel",
            "lastmod": get_lastmod(blog_index),
            "changefreq": "weekly",
            "priority": PRIORITY["artikel_index"]
        })
    
    # Scan subfolder edukasi/
    edukasi_path = os.path.join(base_path, "edukasi")
    if os.path.exists(edukasi_path):
        for kategori in os.listdir(edukasi_path):
            kategori_path = os.path.join(edukasi_path, kategori)
            if not os.path.isdir(kategori_path) or kategori in IGNORE_FOLDERS:
                continue
            
            for judul in os.listdir(kategori_path):
                judul_path = os.path.join(kategori_path, judul)
                index_file = os.path.join(judul_path, "index.html")
                
                if os.path.isdir(judul_path) and os.path.exists(index_file):
                    clean_url = f"/artikel/edukasi/{kategori}/{judul}"
                    urls.append({
                        "loc": f"{BASE_URL}{clean_url}",
                        "lastmod": get_lastmod(index_file),
                        "changefreq": "monthly",
                        "priority": PRIORITY["artikel"]
                    })
    
    # Scan subfolder tips/
    tips_path = os.path.join(base_path, "tips")
    if os.path.exists(tips_path):
        for judul in os.listdir(tips_path):
            judul_path = os.path.join(tips_path, judul)
            index_file = os.path.join(judul_path, "index.html")
            
            if os.path.isdir(judul_path) and os.path.exists(index_file):
                clean_url = f"/artikel/tips/{judul}"
                urls.append({
                    "loc": f"{BASE_URL}{clean_url}",
                    "lastmod": get_lastmod(index_file),
                    "changefreq": "monthly",
                    "priority": PRIORITY["artikel"]
                })
    
    return urls

# ==========================================
# SCAN FOLDER LAYANAN
# ==========================================

def scan_layanan_folder():
    """Scan folder layanan-*/ untuk halaman wilayah."""
    urls = []
    layanan_list = ["layanan-sim", "layanan-skck", "layanan-dukcapil", 
                    "layanan-imigrasi", "layanan-paspor", "layanan-kendaraan"]
    
    for layanan in layanan_list:
        # Index layanan (pilar page)
        index_file = os.path.join(layanan, "index.html")
        if os.path.exists(index_file):
            urls.append({
                "loc": f"{BASE_URL}/{layanan}",
                "lastmod": get_lastmod(index_file),
                "changefreq": "weekly",
                "priority": PRIORITY["layanan_index"]
            })
        
        # Scan subfolder wilayah/
        wilayah_path = os.path.join(layanan, "wilayah")
        if os.path.exists(wilayah_path):
            for wilayah in os.listdir(wilayah_path):
                wilayah_folder = os.path.join(wilayah_path, wilayah)
                index_file = os.path.join(wilayah_folder, "index.html")
                
                if os.path.isdir(wilayah_folder) and os.path.exists(index_file):
                    clean_url = f"/{layanan}/{wilayah}"
                    urls.append({
                        "loc": f"{BASE_URL}{clean_url}",
                        "lastmod": get_lastmod(index_file),
                        "changefreq": "monthly",
                        "priority": PRIORITY["layanan"]
                    })
    
    return urls

# ==========================================
# GENERATE SITEMAP INDIVIDUAL
# ==========================================

def generate_sitemap_edukasi(all_urls):
    """Sitemap khusus artikel edukasi."""
    edukasi_urls = [u for u in all_urls if "/artikel/edukasi/" in u["loc"]]
    write_sitemap("sitemap-edukasi.xml", edukasi_urls)
    return edukasi_urls

def generate_sitemap_tips(all_urls):
    """Sitemap khusus artikel tips."""
    tips_urls = [u for u in all_urls if "/artikel/tips/" in u["loc"]]
    write_sitemap("sitemap-tips.xml", tips_urls)
    return tips_urls

def generate_sitemap_layanan(all_urls):
    """Sitemap khusus halaman layanan."""
    layanan_urls = [u for u in all_urls if any(l in u["loc"] for l in [
        "/layanan-sim", "/layanan-skck", "/layanan-dukcapil",
        "/layanan-imigrasi", "/layanan-paspor", "/layanan-kendaraan"
    ])]
    write_sitemap("sitemap-layanan.xml", layanan_urls)
    return layanan_urls

def generate_sitemap_per_layanan(all_urls):
    """Sitemap per kategori layanan."""
    layanan_map = {
        "sitemap-layanan-sim.xml": "/layanan-sim/",
        "sitemap-layanan-skck.xml": "/layanan-skck/",
        "sitemap-layanan-dukcapil.xml": "/layanan-dukcapil/",
        "sitemap-layanan-imigrasi.xml": "/layanan-imigrasi/",
        "sitemap-layanan-paspor.xml": "/layanan-paspor/",
        "sitemap-layanan-kendaraan.xml": "/layanan-kendaraan/",
    }
    
    for filename, prefix in layanan_map.items():
        urls = [u for u in all_urls if prefix in u["loc"]]
        write_sitemap(filename, urls)

# ==========================================
# GENERATE SITEMAP MASTER
# ==========================================

def generate_sitemap_master(all_urls):
    """Sitemap utama yang include semua URL."""
    # Tambah homepage
    homepage = {
        "loc": f"{BASE_URL}/",
        "lastmod": get_lastmod("index.html") if os.path.exists("index.html") else datetime.now().strftime("%Y-%m-%d"),
        "changefreq": "weekly",
        "priority": PRIORITY["homepage"]
    }
    
    master_urls = [homepage] + all_urls
    write_sitemap("sitemap.xml", master_urls)
    return master_urls

# ==========================================
# GENERATE SITEMAP INDEX (OPSIONAL)
# ==========================================

def generate_sitemap_index():
    """Buat sitemap index yang merujuk ke semua sitemap."""
    sitemapindex = Element("sitemapindex")
    sitemapindex.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    
    sitemaps = [
        "sitemap.xml",
        "sitemap-edukasi.xml",
        "sitemap-tips.xml",
        "sitemap-layanan.xml",
        "sitemap-layanan-sim.xml",
        "sitemap-layanan-skck.xml",
        "sitemap-layanan-dukcapil.xml",
        "sitemap-layanan-imigrasi.xml",
        "sitemap-layanan-paspor.xml",
        "sitemap-layanan-kendaraan.xml",
    ]
    
    for sitemap_file in sitemaps:
        if os.path.exists(sitemap_file):
            sitemap = SubElement(sitemapindex, "sitemap")
            SubElement(sitemap, "loc").text = f"{BASE_URL}/{sitemap_file}"
            SubElement(sitemap, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
    
    xml_string = prettify_xml(sitemapindex)
    
    with open("sitemap-index.xml", "w", encoding="utf-8") as f:
        f.write(xml_string)
    
    print(f"  ✅ sitemap-index.xml (10 sitemap)")

# ==========================================
# UPDATE ROBOTS.TXT
# ==========================================

def update_robots_txt():
    """Tambah sitemap ke robots.txt."""
    robots_content = f"""User-agent: *
Allow: /
Disallow: /images/

Sitemap: {BASE_URL}/sitemap.xml
Sitemap: {BASE_URL}/sitemap-edukasi.xml
Sitemap: {BASE_URL}/sitemap-tips.xml
Sitemap: {BASE_URL}/sitemap-layanan.xml
"""
    
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(robots_content)
    
    print("  ✅ robots.txt diperbarui")

# ==========================================
# MAIN
# ==========================================

def main():
    print("=" * 50)
    print("  GENERATE SITEMAP RIZCH BALI")
    print("=" * 50)
    print()
    
    # 1. Ambil URL dari vercel.json (artikel lama)
    print("📁 Scan vercel.json (URL lama)...")
    vercel_urls = get_vercel_urls()
    print(f"   Ditemukan {len(vercel_urls)} URL dari vercel.json")
    
    # 2. Scan folder artikel/ (artikel baru)
    print("\n📁 Scan folder artikel/...")
    artikel_urls = scan_artikel_folder()
    print(f"   Ditemukan {len(artikel_urls)} artikel")
    
    # 3. Scan folder layanan-*/ (halaman layanan)
    print("\n📁 Scan folder layanan/...")
    layanan_urls = scan_layanan_folder()
    print(f"   Ditemukan {len(layanan_urls)} halaman layanan")
    
    # 4. Gabung semua URL
    all_urls = vercel_urls + artikel_urls + layanan_urls
    
    # 5. Generate sitemap individual
    print("\n📝 Generate sitemap...")
    generate_sitemap_edukasi(all_urls)
    generate_sitemap_tips(all_urls)
    generate_sitemap_layanan(all_urls)
    generate_sitemap_per_layanan(all_urls)
    
    # 6. Generate sitemap master
    print("\n📝 Generate sitemap master...")
    master_urls = generate_sitemap_master(all_urls)
    
    # 7. Generate sitemap index
    print("\n📝 Generate sitemap index...")
    generate_sitemap_index()
    
    # 8. Update robots.txt
    print("\n📝 Update robots.txt...")
    update_robots_txt()
    
    print("\n" + "=" * 50)
    print(f"  SELESAI! Total {len(master_urls)} URL")
    print("=" * 50)

if __name__ == "__main__":
    main()
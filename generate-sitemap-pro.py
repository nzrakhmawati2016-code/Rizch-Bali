#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RIZCH Sitemap Generator Pro - Versi Otomatis
===========================================
Fitur:
- Auto-detect semua folder artikel (rekursif)
- Auto lastmod dari tanggal file system
- Auto priority SEO berdasarkan kedalaman folder
- Auto changefreq berdasarkan umur file
- Auto image sitemap (deteksi gambar di folder artikel)
- Auto sitemap index (master)
- Google Search Console friendly

Cara pakai:
1. Letakkan file ini di root project (sejajar dengan folder artikel/)
2. Jalankan: python generate-sitemap-pro.py
3. Script akan scan otomatis dan generate semua sitemap

Untuk auto-run tiap hari (Linux/Mac):
- crontab -e
- Tambah: 0 2 * * * cd /path/to/project && python generate-sitemap-pro.py

Untuk Vercel (serverless):
- Gunakan Vercel Cron Jobs (berbayar) atau GitHub Actions
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# KONFIGURASI
# ============================================================
BASE_URL = "https://rizchbali.com"
ARTICLE_DIR = "artikel"  # Folder root artikel
OUTPUT_DIR = "."  # Output di root project

# Format: (kedalaman_folder, priority)
# Semakin dangkal folder = semakin penting
PRIORITY_RULES = [
    (0, "1.0"),   # artikel/layanan-sim/index.html (index langsung)
    (1, "0.9"),   # artikel/layanan-sim/badung/index.html (1 subfolder)
    (2, "0.8"),   # artikel/edukasi/kendaraan/artikel.html (2 subfolder)
    (3, "0.7"),   # Lebih dalam
    (4, "0.6"),   # Sangat dalam
]

# Changefreq berdasarkan umur file (hari)
# File baru = update sering, file lama = jarang
CHANGEFREQ_RULES = [
    (7, "daily"),      # < 7 hari
    (30, "weekly"),    # < 30 hari
    (90, "monthly"),   # < 90 hari
    (365, "yearly"),   # < 1 tahun
    (float('inf'), "never"),  # > 1 tahun
]

# Gambar yang dideteksi untuk image sitemap
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

# ============================================================
# FUNGSI UTILITAS
# ============================================================

def get_file_age_days(filepath):
    """Hitung umur file dalam hari."""
    try:
        mtime = os.path.getmtime(filepath)
        file_date = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - file_date).days
    except:
        return 0

def get_file_lastmod(filepath):
    """Format lastmod dari tanggal file (ISO 8601)."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

def get_priority(depth):
    """Tentukan priority berdasarkan kedalaman folder."""
    for max_depth, priority in PRIORITY_RULES:
        if depth <= max_depth:
            return priority
    return "0.5"

def get_changefreq(age_days):
    """Tentukan changefreq berdasarkan umur file."""
    for max_age, freq in CHANGEFREQ_RULES:
        if age_days < max_age:
            return freq
    return "never"

def find_images(article_dir, html_file):
    """Cari gambar di folder artikel yang sama."""
    images = []
    article_folder = os.path.dirname(html_file)

    if os.path.exists(article_folder):
        for file in os.listdir(article_folder):
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                rel_path = os.path.relpath(os.path.join(article_folder, file), ".")
                image_url = f"{BASE_URL}/{rel_path.replace(chr(92), '/')}"
                images.append(image_url)

    return images

def escape_xml(text):
    """Escape karakter khusus XML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# ============================================================
# SCANNER FOLDER
# ============================================================

def scan_folders():
    """Scan semua folder artikel dan kelompokkan per kategori."""
    sitemap_data = {}

    if not os.path.exists(ARTICLE_DIR):
        print(f"ERROR: Folder '{ARTICLE_DIR}' tidak ditemukan!")
        sys.exit(1)

    # Walk rekursif semua folder di artikel/
    for root, dirs, files in os.walk(ARTICLE_DIR):
        # Lewati folder yang bukan artikel (misal: images, assets)
        if any(skip in root for skip in ["images", "assets", "css", "js", "node_modules"]):
            continue

        html_files = [f for f in files if f.endswith('.html')]

        if not html_files:
            continue

        # Tentukan nama sitemap berdasarkan folder
        rel_path = os.path.relpath(root, ARTICLE_DIR)
        parts = rel_path.replace(chr(92), '/').split('/')

        # Logika penamaan sitemap
        if parts[0] == 'edukasi':
            sitemap_name = 'sitemap-edukasi'
        elif parts[0] == 'tips':
            sitemap_name = 'sitemap-tips'
        elif parts[0].startswith('layanan-'):
            sitemap_name = f"sitemap-{parts[0]}"
        elif parts[0] == 'berita':
            sitemap_name = 'sitemap-berita'
        else:
            # Fallback: pakai nama folder pertama
            sitemap_name = f"sitemap-{parts[0]}"

        if sitemap_name not in sitemap_data:
            sitemap_data[sitemap_name] = []

        for html_file in html_files:
            full_path = os.path.join(root, html_file)
            rel_file = os.path.relpath(full_path, ".")
            url = f"{BASE_URL}/{rel_file.replace(chr(92), '/')}"

            # Hitung kedalaman folder
            depth = len([p for p in parts if p and p != '.'])
            if html_file != 'index.html':
                depth += 1

            # Info file
            age_days = get_file_age_days(full_path)
            lastmod = get_file_lastmod(full_path)
            priority = get_priority(depth)
            changefreq = get_changefreq(age_days)

            # Cari gambar
            images = find_images(ARTICLE_DIR, full_path)

            sitemap_data[sitemap_name].append({
                'url': url,
                'lastmod': lastmod,
                'changefreq': changefreq,
                'priority': priority,
                'images': images,
                'is_index': html_file == 'index.html'
            })

    return sitemap_data

# ============================================================
# GENERATOR SITEMAP XML
# ============================================================

def generate_sitemap_xml(name, urls):
    """Generate file sitemap XML."""

    # Sort: index dulu, kemudian alfabetis
    urls.sort(key=lambda x: (not x['is_index'], x['url']))

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
    ]

    for item in urls:
        xml_parts.append('  <url>')
        xml_parts.append(f"    <loc>{escape_xml(item['url'])}</loc>")
        xml_parts.append(f"    <lastmod>{item['lastmod']}</lastmod>")
        xml_parts.append(f"    <changefreq>{item['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{item['priority']}</priority>")

        # Tambah image sitemap jika ada gambar
        for img_url in item['images'][:5]:  # Max 5 gambar per URL
            xml_parts.append('    <image:image>')
            xml_parts.append(f"      <image:loc>{escape_xml(img_url)}</image:loc>")
            xml_parts.append('    </image:image>')

        xml_parts.append('  </url>')

    xml_parts.append('</urlset>')

    return '\n'.join(xml_parts)

def generate_master_sitemap(sitemap_files):
    """Generate sitemap.xml (master index)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for sitemap_file in sorted(sitemap_files):
        xml_parts.append('  <sitemap>')
        xml_parts.append(f"    <loc>{BASE_URL}/{sitemap_file}</loc>")
        xml_parts.append(f"    <lastmod>{now}</lastmod>")
        xml_parts.append('  </sitemap>')

    xml_parts.append('</sitemapindex>')

    return '\n'.join(xml_parts)

# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*60)
    print("  RIZCH Sitemap Generator Pro")
    print("  Auto-detect | Auto-priority | Auto-image | Auto-index")
    print("="*60 + "\n")

    # Step 1: Scan folder
    print("[1/4] Scanning folders...")
    sitemap_data = scan_folders()

    if not sitemap_data:
        print("WARNING: Tidak ada file HTML ditemukan!")
        return

    print(f"       Found {len(sitemap_data)} sitemap categories\n")

    # Step 2: Generate sitemap per kategori
    print("[2/4] Generating sitemap files...")
    generated_files = []
    total_urls = 0

    for name, urls in sitemap_data.items():
        xml_content = generate_sitemap_xml(name, urls)
        filename = f"{name}.xml"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        generated_files.append(filename)
        total_urls += len(urls)

        image_count = sum(len(u['images']) for u in urls)
        print(f"       {filename:30} | {len(urls):3} URLs | {image_count:3} images")

    print()

    # Step 3: Generate master sitemap
    print("[3/4] Generating master sitemap.xml...")
    master_xml = generate_master_sitemap(generated_files)
    master_path = os.path.join(OUTPUT_DIR, "sitemap.xml")

    with open(master_path, 'w', encoding='utf-8') as f:
        f.write(master_xml)

    print(f"       sitemap.xml (master) with {len(generated_files)} sitemaps\n")

    # Step 4: Summary
    print("[4/4] Done!\n")
    print("="*60)
    print(f"  Total sitemaps : {len(generated_files) + 1}")
    print(f"  Total URLs     : {total_urls}")
    print(f"  Output folder  : {os.path.abspath(OUTPUT_DIR)}")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Upload sitemap.xml ke Google Search Console")
    print("  2. URL: https://rizchbali.com/sitemap.xml")
    print("  3. Google akan auto-index artikel baru\n")

if __name__ == "__main__":
    main()
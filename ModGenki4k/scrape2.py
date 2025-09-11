import os
import requests
import typer
import csv
from time import sleep
from urllib.parse import urlparse
from colorama import init, Fore, Style

app = typer.Typer(help="Pexels Smile Scraper – download high-quality smile images with credits")

# Initialize Colorama for cross-platform color support
init(autoreset=True)

def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in s).strip()

@app.command()
def scrape(
    query: str = typer.Option("african face", help="Search query for images"),
    num_images: int = typer.Option(100, help="Total number of images to download"),
    resolution: str = typer.Option("original", help="Image resolution (e.g., original, large)"),
):
    DOWNLOAD_DIR = os.path.expanduser(f"~/Downloads/{query.replace(' ', '_')}")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    API_KEY = os.getenv("PEXELS_API_KEY", "LMcPx1udI3e8GcThoGJthJRPXaSYxTpxo4xMynNYSIHgbu1Ulbhp1siV")
    headers = {"Authorization": API_KEY}
    BASE_URL = "https://api.pexels.com/v1/search"

    page = 1
    downloaded = 0
    photographers = {}

    typer.echo(Fore.CYAN + f"Starting scrape for '{query}'...")

    while downloaded < num_images:
        params = {"query": query, "per_page": min(80, num_images - downloaded), "page": page}
        resp = requests.get(BASE_URL, headers=headers, params=params)
        if resp.status_code != 200:
            typer.echo(Fore.RED + f"Error: Received status {resp.status_code}")
            raise typer.Exit(code=1)

        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            typer.echo(Fore.YELLOW + "No more photos available.")
            break

        for photo in photos:
            if downloaded >= num_images:
                break

            img_url = photo["src"].get(resolution)
            if not img_url:
                continue

            fname = f"{photo['id']}_{safe_filename(photo['photographer'])}.jpg"
            dest_path = os.path.join(DOWNLOAD_DIR, fname)

            if os.path.exists(dest_path):
                typer.echo(Fore.YELLOW + f"[SKIPPED] {fname} already exists")
                continue

            img_resp = requests.get(img_url)
            if img_resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(img_resp.content)
                downloaded += 1
                typer.echo(Fore.GREEN + f"[{downloaded}/{num_images}] Downloaded: {fname}")
                photographers[photo["photographer"]] = photo.get("photographer_url")
            else:
                typer.echo(Fore.RED + f"[ERROR] Failed to download {fname}: status {img_resp.status_code}")

        page += 1
        sleep(1)
        

    typer.echo(Style.BRIGHT + Fore.MAGENTA + f"\nDone! {downloaded} images downloaded to '{DOWNLOAD_DIR}'\n")
    typer.echo(Style.BRIGHT + "Photographer Credits:")
    
    #Converting the dict into the CSV
    csv_path = os.path.join(DOWNLOAD_DIR, f"{query}_photographers.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, )
        writer.writerow(["Photographer", "Profile URL"])
        
        #Add then do the looping of photographer's dictionary
        for name, url in photographers.items():
            typer.echo(f". {name}: {url}")
            writer.writerow([name, url])
            
        typer.echo(Style.BRIGHT + Fore.CYAN + f"Photographer credits exported to: {csv_path}")

if __name__ == "__main__":
    app()

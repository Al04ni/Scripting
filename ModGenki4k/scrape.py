import os
import requests
import typer
import csv
from time import sleep
from urllib.parse import urlparse
from colorama import init, Fore, Style
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = typer.Typer(help="Pexels Smile Scraper")

# Initialize Colorama for cross-platform color support
init(autoreset=True)

def create_session():
    """Create a requests session with retry capabilities"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def download_image(session, url, dest_path, max_retries=3):
    """Download an image with retry logic"""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=30, stream=True)
            response.raise_for_status()  # Raise exception for bad status codes
            
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
            return True
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            if attempt < max_retries - 1:
                sleep(2)  # Wait before retrying
                continue
            else:
                print(f"Failed to download after {max_retries} attempts: {e}")
                return False
    return False

def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in s).strip()

@app.command()
def scrape(
    query: str = typer.Option("face", help="Search query for images"),
    num_images: int = typer.Option(1000, help="Total number of images to download"),
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
    
    # Create a session for API requests
    api_session = create_session()

    typer.echo(Fore.CYAN + f"Starting scrape for '{query}'...")

    while downloaded < num_images:
        params = {"query": query, "per_page": min(80, num_images - downloaded), "page": page}
        resp = api_session.get(BASE_URL, headers=headers, params=params)
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

            # Download the image with retry logic
            if download_image(api_session, img_url, dest_path):
                downloaded += 1
                typer.echo(Fore.GREEN + f"[{downloaded}/{num_images}] Downloaded: {fname}")
                photographers[photo["photographer"]] = photo.get("photographer_url")
            else:
                typer.echo(Fore.RED + f"[ERROR] Failed to download {fname}")

        page += 1
        sleep(1)  # Be respectful to the API

    typer.echo(Style.BRIGHT + Fore.MAGENTA + f"\nDone! {downloaded} images downloaded to '{DOWNLOAD_DIR}'\n")
    typer.echo(Style.BRIGHT + "Photographer Credits:")
    
    # Converting the dict into the CSV
    csv_path = os.path.join(DOWNLOAD_DIR, f"{query}_photographers.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Photographer", "Profile URL"])
        
        # Add then do the looping of photographer's dictionary
        for name, url in photographers.items():
            typer.echo(f". {name}: {url}")
            writer.writerow([name, url])
            
        typer.echo(Style.BRIGHT + Fore.CYAN + f"Photographer credits exported to: {csv_path}")

if __name__ == "__main__":
    app()
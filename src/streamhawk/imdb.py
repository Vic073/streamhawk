"""
IMDb metadata fetching client.
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import re


@dataclass
class MovieMetadata:
    """Movie metadata dataclass."""
    imdb_id: str
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    plot: Optional[str] = None
    poster_url: Optional[str] = None
    genres: list = None
    duration: Optional[str] = None
    directors: list = None
    actors: list = None
    
    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.directors is None:
            self.directors = []
        if self.actors is None:
            self.actors = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'imdb_id': self.imdb_id,
            'title': self.title,
            'year': self.year,
            'rating': self.rating,
            'plot': self.plot,
            'poster_url': self.poster_url,
            'genres': self.genres,
            'duration': self.duration,
            'directors': self.directors,
            'actors': self.actors
        }
    
    def format_filename(self, template: str = "%(title)s (%(year)s).%(ext)s") -> str:
        """Format output filename using metadata."""
        year_str = str(self.year) if self.year else "Unknown"
        filename = template.replace("%(title)s", self.title or "Unknown")
        filename = filename.replace("%(year)s", year_str)
        filename = filename.replace("%(imdb_id)s", self.imdb_id)
        return filename


class IMDbClient:
    """Client for fetching IMDb metadata via omdbapi or similar."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.omdbapi.com/"
        self.cache: Dict[str, MovieMetadata] = {}
    
    async def fetch_metadata(self, imdb_id: str, 
                             use_fallback: bool = True) -> Optional[MovieMetadata]:
        """
        Fetch movie metadata from IMDb.
        
        Args:
            imdb_id: IMDb ID (e.g., tt0816692)
            use_fallback: Use web scraping if API fails
            
        Returns:
            MovieMetadata object or None
        """
        # Check cache
        if imdb_id in self.cache:
            return self.cache[imdb_id]
        
        # Try API first if key available
        if self.api_key:
            metadata = await self._fetch_from_api(imdb_id)
            if metadata:
                self.cache[imdb_id] = metadata
                return metadata
        
        # Fallback to web scraping
        if use_fallback:
            metadata = await self._fetch_from_web(imdb_id)
            if metadata:
                self.cache[imdb_id] = metadata
                return metadata
        
        # Return minimal metadata
        return MovieMetadata(imdb_id=imdb_id, title=f"Movie_{imdb_id}")
    
    async def _fetch_from_api(self, imdb_id: str) -> Optional[MovieMetadata]:
        """Fetch from OMDb API."""
        try:
            import aiohttp
            
            params = {
                'i': imdb_id,
                'apikey': self.api_key,
                'plot': 'short'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if data.get('Response') == 'False':
                        return None
                    
                    # Parse year
                    year_str = data.get('Year', '')
                    year = None
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                    
                    # Parse rating
                    rating = None
                    imdb_rating = data.get('imdbRating', 'N/A')
                    if imdb_rating != 'N/A':
                        try:
                            rating = float(imdb_rating)
                        except ValueError:
                            pass
                    
                    return MovieMetadata(
                        imdb_id=imdb_id,
                        title=data.get('Title', 'Unknown'),
                        year=year,
                        rating=rating,
                        plot=data.get('Plot'),
                        poster_url=data.get('Poster') if data.get('Poster') != 'N/A' else None,
                        genres=data.get('Genre', '').split(', ') if data.get('Genre') else [],
                        duration=data.get('Runtime'),
                        directors=data.get('Director', '').split(', ') if data.get('Director') else [],
                        actors=data.get('Actors', '').split(', ') if data.get('Actors') else []
                    )
                    
        except Exception:
            return None
    
    async def _fetch_from_web(self, imdb_id: str) -> Optional[MovieMetadata]:
        """Fetch from IMDb web page (fallback method)."""
        try:
            from playwright.async_api import async_playwright
            
            url = f"https://www.imdb.com/title/{imdb_id}/"
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # Extract title
                title = await page.evaluate("""() => {
                    const el = document.querySelector('h1[data-testid="hero-title-block__title"]');
                    return el ? el.textContent.trim() : null;
                }""")
                
                # Extract year
                year_text = await page.evaluate("""() => {
                    const el = document.querySelector('a[href*="releaseinfo"]');
                    return el ? el.textContent.trim() : null;
                }""")
                year = None
                if year_text:
                    match = re.search(r'\d{4}', year_text)
                    if match:
                        year = int(match.group())
                
                # Extract rating
                rating_text = await page.evaluate("""() => {
                    const el = document.querySelector('[data-testid="hero-rating-bar__aggregate-rating__score"] span');
                    return el ? el.textContent.trim() : null;
                }""")
                rating = None
                if rating_text:
                    try:
                        rating = float(rating_text)
                    except ValueError:
                        pass
                
                # Extract plot
                plot = await page.evaluate("""() => {
                    const el = document.querySelector('[data-testid="plot"] span');
                    return el ? el.textContent.trim() : null;
                }""")
                
                # Extract poster
                poster = await page.evaluate("""() => {
                    const el = document.querySelector('[data-testid="hero-media__poster"] img, .ipc-media img');
                    return el ? el.src : null;
                }""")
                
                await browser.close()
                
                return MovieMetadata(
                    imdb_id=imdb_id,
                    title=title or f"Movie_{imdb_id}",
                    year=year,
                    rating=rating,
                    plot=plot,
                    poster_url=poster
                )
                
        except Exception:
            return None
    
    def get_suggested_filename(self, imdb_id: str, metadata: MovieMetadata = None,
                               template: str = "%(title)s (%(year)s).%(ext)s") -> str:
        """Get suggested filename based on metadata."""
        if metadata:
            return metadata.format_filename(template)
        return f"{imdb_id}.mp4"
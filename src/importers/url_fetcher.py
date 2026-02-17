"""URL fetching with OAuth support for Google Docs.

Provides:
- URLFetcher: Fetch content from public URLs
- GoogleDocsClient: OAuth flow and Google Docs content fetching
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class FetchResult:
    """Result of URL fetch operation."""
    content: str
    content_type: str
    source_url: str
    fetched_at: str

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'content': self.content,
            'content_type': self.content_type,
            'source_url': self.source_url,
            'fetched_at': self.fetched_at
        }


@dataclass
class TokenData:
    """OAuth token data."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: str

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at
        }


class URLFetcher:
    """Fetch content from public URLs."""

    def __init__(self, timeout: int = 30, max_size: int = 10 * 1024 * 1024):
        """
        Initialize URL fetcher.

        Args:
            timeout: Request timeout in seconds (default: 30)
            max_size: Maximum content size in bytes (default: 10MB)
        """
        self.timeout = timeout
        self.max_size = max_size

    def fetch(self, url: str) -> FetchResult:
        """
        Fetch content from public URL.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with content and metadata

        Raises:
            ValueError: If URL is invalid or inaccessible
            requests.RequestException: If network error occurs
        """
        if not url or not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {url}")

        try:
            # Fetch with timeout and follow redirects
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()

            # Check content size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_size:
                raise ValueError(f"Content too large: {content_length} bytes (max: {self.max_size})")

            # Read content in chunks to enforce size limit
            content_chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                total_size += len(chunk)
                if total_size > self.max_size:
                    raise ValueError(f"Content exceeds maximum size: {self.max_size} bytes")
                content_chunks.append(chunk)

            content = b''.join(content_chunks).decode('utf-8', errors='replace')

            # Get content type from headers
            content_type = response.headers.get('content-type', 'text/plain').split(';')[0].strip()

            return FetchResult(
                content=content,
                content_type=content_type,
                source_url=response.url,  # Final URL after redirects
                fetched_at=datetime.now(timezone.utc).isoformat()
            )

        except requests.exceptions.Timeout:
            raise ValueError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"HTTP error {e.response.status_code}: {e.response.reason}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error: {str(e)}")
        except UnicodeDecodeError:
            raise ValueError("Content is not valid text")


class GoogleDocsClient:
    """OAuth flow and Google Docs content fetching."""

    SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Google Docs client.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI (e.g., http://localhost:5003/api/import/oauth/google/callback)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'redirect_uris': [self.redirect_uri],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )

        return auth_url

    def exchange_code(self, code: str) -> TokenData:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            TokenData with access token, refresh token, and expiry

        Raises:
            ValueError: If code exchange fails
        """
        try:
            flow = Flow.from_client_config(
                {
                    'web': {
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'redirect_uris': [self.redirect_uri],
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://oauth2.googleapis.com/token',
                    }
                },
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )

            flow.fetch_token(code=code)

            credentials = flow.credentials

            # Calculate expiry time
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=credentials.expiry.timestamp() - datetime.now(timezone.utc).timestamp())

            return TokenData(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=expires_at.isoformat()
            )

        except Exception as e:
            raise ValueError(f"Failed to exchange authorization code: {str(e)}")

    def fetch_document(self, doc_id: str, access_token: str) -> FetchResult:
        """
        Fetch Google Doc content as plain text.

        Args:
            doc_id: Google Doc ID (from URL: docs.google.com/document/d/{doc_id}/...)
            access_token: OAuth access token

        Returns:
            FetchResult with document content

        Raises:
            ValueError: If document fetch fails
        """
        try:
            # Create credentials from token
            credentials = Credentials(token=access_token)

            # Build Docs API service
            service = build('docs', 'v1', credentials=credentials)

            # Fetch document
            document = service.documents().get(documentId=doc_id).execute()

            # Extract text content
            content = self._extract_text(document)

            # Get document title
            title = document.get('title', 'Untitled')

            return FetchResult(
                content=content,
                content_type='text/plain',
                source_url=f"https://docs.google.com/document/d/{doc_id}/edit",
                fetched_at=datetime.now(timezone.utc).isoformat()
            )

        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Document not found: {doc_id}")
            elif e.resp.status == 403:
                raise ValueError("Access denied. You may not have permission to view this document.")
            else:
                raise ValueError(f"Google Docs API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to fetch document: {str(e)}")

    def _extract_text(self, document: dict) -> str:
        """
        Extract plain text from Google Doc structure.

        Args:
            document: Google Doc JSON structure

        Returns:
            Plain text content
        """
        text_parts = []

        body = document.get('body', {})
        content = body.get('content', [])

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                paragraph_text = self._extract_paragraph_text(paragraph)
                if paragraph_text:
                    text_parts.append(paragraph_text)

            elif 'table' in element:
                table = element['table']
                table_text = self._extract_table_text(table)
                if table_text:
                    text_parts.append(table_text)

        return '\n\n'.join(text_parts)

    def _extract_paragraph_text(self, paragraph: dict) -> str:
        """Extract text from paragraph element."""
        text_parts = []

        elements = paragraph.get('elements', [])
        for elem in elements:
            if 'textRun' in elem:
                text_run = elem['textRun']
                content = text_run.get('content', '')
                text_parts.append(content)

        return ''.join(text_parts).strip()

    def _extract_table_text(self, table: dict) -> str:
        """Extract text from table element."""
        table_rows = []

        rows = table.get('tableRows', [])
        for row in rows:
            cells = row.get('tableCells', [])
            cell_texts = []

            for cell in cells:
                cell_content = cell.get('content', [])
                cell_text_parts = []

                for element in cell_content:
                    if 'paragraph' in element:
                        paragraph = element['paragraph']
                        paragraph_text = self._extract_paragraph_text(paragraph)
                        if paragraph_text:
                            cell_text_parts.append(paragraph_text)

                cell_texts.append(' '.join(cell_text_parts))

            table_rows.append(' | '.join(cell_texts))

        return '\n'.join(table_rows)

    @staticmethod
    def extract_doc_id(url: str) -> str:
        """
        Extract document ID from Google Docs URL.

        Args:
            url: Google Docs URL or doc ID

        Returns:
            Document ID

        Raises:
            ValueError: If URL is invalid
        """
        # If already just an ID, return it
        if '/' not in url and len(url) > 20:
            return url

        # Extract from URL
        # Format: https://docs.google.com/document/d/{doc_id}/...
        if 'docs.google.com/document/d/' in url:
            parts = url.split('/document/d/')
            if len(parts) > 1:
                doc_id = parts[1].split('/')[0]
                return doc_id

        raise ValueError(f"Invalid Google Docs URL: {url}")

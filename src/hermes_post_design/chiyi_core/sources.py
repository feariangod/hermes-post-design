"""Source loading for local files, data URLs, and remote HTTP(S) images."""
from __future__ import annotations

import base64
import ipaddress
import os
import re
import socket
import threading
from collections.abc import MutableMapping
from pathlib import Path
from typing import Iterator, Mapping, Protocol
from urllib.parse import urljoin, urlparse, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool

from hermes_post_design.chiyi_core.models import ImageSource, LoadedSource
from hermes_post_design.chiyi_core.images import MAX_IMAGE_BYTES, inspect_image, MIME_TO_FORMAT


class DownloadResponse(Protocol):
    """Protocol for HTTP download response."""
    status_code: int
    headers: Mapping[str, str]
    peer_ip: str | None

    def iter_bytes(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Iterate response body in chunks."""
        ...

    def close(self) -> None:
        """Close the response."""
        ...


def _sanitize_filename_from_url(raw_filename: str, real_ext: str) -> str:
    """
    Sanitize filename extracted from URL path.

    Args:
        raw_filename: Raw filename from URL path (already unquoted)
        real_ext: Real file extension (e.g., "jpg", "png")

    Returns:
        Sanitized filename with correct extension
    """
    # Remove path separators
    filename = raw_filename.replace('\\', '_').replace('/', '_')

    # Remove control characters, keep printable ASCII and Unicode
    filename = ''.join(c if c.isprintable() else '_' for c in filename)

    # Get stem (remove extension)
    stem = filename.rsplit('.', 1)[0] if '.' in filename else filename
    if not stem:
        stem = 'image'

    # Build final filename with real extension
    final = f"{stem}.{real_ext}"

    # Limit total length
    if len(final) > 200:
        # Truncate stem to fit
        max_stem_len = 200 - len(real_ext) - 1  # -1 for dot
        stem = stem[:max_stem_len]
        final = f"{stem}.{real_ext}"

    return final


def _sanitize_filename_from_local(path: Path, real_ext: str) -> str:
    """
    Sanitize filename from local path.

    Args:
        path: Local file path
        real_ext: Real file extension (e.g., "jpg", "png")

    Returns:
        Sanitized filename with correct extension
    """
    # Use basename only
    stem = path.stem
    if not stem:
        stem = 'image'

    # Check if extension matches
    expected_ext = f".{real_ext}"
    if path.suffix.lower() == expected_ext:
        return path.name

    # Extension doesn't match, fix it
    return f"{stem}.{real_ext}"


def _is_windows_drive_path(value: str) -> bool:
    r"""Check if value starts with Windows drive letter pattern (C:\ or C:/)."""
    return bool(re.match(r'^[A-Za-z]:[\\/]', value))


def _has_url_scheme(value: str) -> bool:
    """Check if value has a URL scheme (but not Windows drive)."""
    if _is_windows_drive_path(value):
        return False

    # Check for scheme pattern: letters followed by colon
    match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):(.+)', value)
    return match is not None


def _is_symlink_or_reparse(path: Path) -> bool:
    """
    Check if path itself is a symlink or Windows reparse point.

    Checks the path itself only, not parents.
    Returns True if symlink, broken symlink, or reparse point detected.
    """
    try:
        # Check if it's a symlink (works for both broken and valid)
        if path.is_symlink():
            return True
    except FileNotFoundError:
        # Path doesn't exist - not a symlink issue
        return False
    except OSError:
        # If we can't check, be conservative
        return True

    # On Windows, check for reparse points via lstat
    if os.name == 'nt':
        try:
            stat_result = path.lstat()
            # Check if FILE_ATTRIBUTE_REPARSE_POINT is set (0x400)
            if hasattr(stat_result, 'st_file_attributes'):
                if stat_result.st_file_attributes & 0x400:
                    return True
        except FileNotFoundError:
            return False
        except OSError:
            return True

    return False


def _has_symlink_parent(path: Path) -> bool:
    """
    Check if any parent component is a symlink or reparse point.

    Traverses from path's parent up to root, checking each component.
    Returns True if any parent is a symlink or reparse point.
    """
    try:
        # Start from parent
        current = path.parent

        while True:
            # Check if current component is symlink or reparse
            if _is_symlink_or_reparse(current):
                return True

            # Move to parent
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent

    except (OSError, RuntimeError):
        # Conservative: if we can't verify, reject
        return True

    return False


def _load_local_file(value: str) -> LoadedSource:
    """
    Load a local file as image source.

    Args:
        value: File path string

    Returns:
        LoadedSource with sanitized filename, data, and MIME type

    Raises:
        ValueError: If file doesn't exist, is not regular file, is symlink,
                   has symlink parent, exceeds size limit, or format validation fails
    """
    # Expand user home directory
    path = Path(value).expanduser()

    # Make lexically absolute (don't resolve)
    if not path.is_absolute():
        path = Path.cwd() / path

    # Check if path itself is symlink or reparse point BEFORE checking existence
    # This handles broken symlinks correctly
    try:
        if path.is_symlink():
            raise ValueError("Symlinks not allowed in local image path")
    except FileNotFoundError:
        # Path doesn't exist, will be caught by lstat below
        pass
    except OSError:
        # Can't determine, be conservative
        raise ValueError("Symlinks not allowed in local image path")

    # lstat before open (don't follow symlinks)
    try:
        lstat_result = path.lstat()
    except FileNotFoundError:
        raise ValueError("File not found in local image path")
    except OSError:
        raise ValueError("Cannot access local image file")

    # Check if any parent is symlink or reparse point
    if _has_symlink_parent(path):
        raise ValueError("Symlinks not allowed in local image path")

    # Check if regular file
    import stat
    if not stat.S_ISREG(lstat_result.st_mode):
        raise ValueError("Not a regular file in local image path")

    # Check size
    file_size = lstat_result.st_size
    if file_size == 0:
        raise ValueError("Local image file is empty")

    if file_size > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Local image file exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB"
        )

    # Get identity (dev, ino) - check if available
    dev = lstat_result.st_dev
    ino = lstat_result.st_ino
    identity_available = (dev != 0 and ino != 0)

    # Open with O_RDONLY and available flags
    flags = os.O_RDONLY
    if hasattr(os, 'O_BINARY'):
        flags |= os.O_BINARY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW

    fd = None
    try:
        fd = os.open(path, flags)

        # fstat the opened fd
        fstat_result = os.fstat(fd)

        # Verify it's still regular
        if not stat.S_ISREG(fstat_result.st_mode):
            raise ValueError("Not a regular file in local image path")

        # Verify identity if available
        if identity_available:
            if fstat_result.st_dev != dev or fstat_result.st_ino != ino:
                raise ValueError("Local image file identity changed during open")

        # Verify size matches
        if fstat_result.st_size != file_size:
            raise ValueError("Local image file size changed during open")

        # Read in bounded loop until complete or overflow
        chunks = bytearray()
        remaining = MAX_IMAGE_BYTES + 1

        while remaining > 0:
            try:
                chunk = os.read(fd, remaining)
            except InterruptedError:
                continue

            if not chunk:
                break

            if not isinstance(chunk, bytes):
                raise ValueError("Local image file read returned non-bytes")

            chunks.extend(chunk)

            if len(chunks) > MAX_IMAGE_BYTES:
                raise ValueError(
                    f"Local image file exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB"
                )

            remaining = MAX_IMAGE_BYTES + 1 - len(chunks)

        data = bytes(chunks)

        # Fix 6: Verify complete read - check that data length matches file_size
        if len(data) != file_size:
            raise ValueError("Local image file size mismatch or incomplete read")

        # fstat again after read
        fstat_after = os.fstat(fd)

        # Verify identity still matches if available
        if identity_available:
            if fstat_after.st_dev != dev or fstat_after.st_ino != ino:
                raise ValueError("Local image file identity changed during read")

        # Verify size still matches
        if fstat_after.st_size != file_size:
            raise ValueError("Local image file size changed during read")

    finally:
        if fd is not None:
            os.close(fd)

    # Verify actual bytes read
    if len(data) == 0:
        raise ValueError("Local image file is empty")

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Local image file exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB"
        )

    # Inspect image to get real format
    info = inspect_image(data)

    # Sanitize filename
    filename = _sanitize_filename_from_local(path, info.format)

    return LoadedSource(
        filename=filename,
        data=data,
        mime_type=info.mime_type,
    )


def _load_data_url(value: str) -> LoadedSource:
    """
    Load a data URL as image source.

    Args:
        value: Data URL string (must start with case-insensitive "data:")

    Returns:
        LoadedSource with filename based on format, data, and MIME type

    Raises:
        ValueError: If data URL is malformed, not base64, unsupported format,
                   exceeds size limit, or MIME mismatch
    """
    # Case-insensitive check for "data:" prefix
    if not value.lower().startswith('data:'):
        raise ValueError("Data URL must start with 'data:'")

    # Remove prefix (preserve case for rest of parsing)
    rest = value[5:]

    # Split on first comma
    if ',' not in rest:
        raise ValueError("Data URL missing comma separator")

    header, payload = rest.split(',', 1)

    # Parse header case-insensitively
    header_lower = header.lower()

    # Must contain ';base64'
    if ';base64' not in header_lower:
        raise ValueError("Data URL must use base64 encoding")

    # Extract media type (before ;base64)
    parts = header_lower.split(';')
    media_type = parts[0].strip()

    # Must be image/...
    if not media_type.startswith('image/'):
        raise ValueError("Data URL is not an image type")

    # Extract format from media type
    # Supported: image/png, image/jpeg, image/webp, image/gif
    if media_type not in ('image/png', 'image/jpeg', 'image/webp', 'image/gif'):
        raise ValueError(f"Data URL has unsupported image format")

    # Verify only base64 parameter exists
    base64_params = [p.strip() for p in parts[1:] if p.strip()]
    if len(base64_params) != 1 or base64_params[0] != 'base64':
        raise ValueError("Data URL has unexpected parameters")

    # Pre-decode size check: constant-space upper bound on payload length
    # Base64 expands by ~4/3, so max_encoded = 4 * ((MAX + 2) // 3)
    max_encoded = 4 * ((MAX_IMAGE_BYTES + 2) // 3)

    if len(payload) > max_encoded:
        raise ValueError("Data URL payload too large (estimated size exceeds limit)")

    # Decode base64 with strict validation (no whitespace/invalid chars allowed)
    try:
        data = base64.b64decode(payload, validate=True)
    except Exception:
        raise ValueError("Data URL has invalid base64 encoding")

    # Check actual decoded size
    if len(data) == 0:
        raise ValueError("Data URL has empty payload")

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Data URL payload exceeds size limit")

    # Inspect image and verify MIME matches
    info = inspect_image(data, declared_mime=media_type)

    # Generate filename based on real format
    filename = f"image.{info.format}"

    return LoadedSource(
        filename=filename,
        data=data,
        mime_type=info.mime_type,
    )


def _normalize_ip(ip_str: str) -> str:
    """
    Normalize and validate IP address is globally routable.

    Args:
        ip_str: IP address string

    Returns:
        Canonical IP address string

    Raises:
        ValueError: If IP is not globally routable (private, loopback, etc.)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        raise ValueError("Invalid IP address format")

    # Handle IPv4-mapped IPv6 addresses
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    # Check is_global (public internet)
    if not ip.is_global:
        raise ValueError("IP address is not globally routable")

    # Additional explicit checks for non-public ranges
    if ip.is_private:
        raise ValueError("IP address is not globally routable")
    if ip.is_loopback:
        raise ValueError("IP address is not globally routable")
    if ip.is_link_local:
        raise ValueError("IP address is not globally routable")
    if ip.is_multicast:
        raise ValueError("IP address is not globally routable")
    if ip.is_reserved:
        raise ValueError("IP address is not globally routable")
    if ip.is_unspecified:
        raise ValueError("IP address is not globally routable")

    return str(ip)


def _ascii_hostname(host: str) -> str:
    """
    Convert hostname to ASCII form using IDNA encoding.

    Args:
        host: Hostname string (may be domain or IP)

    Returns:
        ASCII hostname string (punycode for IDN, canonical IP, or lowercased ASCII)

    Raises:
        ValueError: If hostname contains control characters, NUL, or is empty
    """
    # Check for empty
    if not host:
        raise ValueError("Hostname is empty")

    # Check for control characters, NUL
    if '\x00' in host or any(c < '\x20' or c == '\x7f' for c in host):
        raise ValueError("Hostname contains invalid control characters")

    # Try to parse as IP address - if valid, return canonical form
    try:
        ip = ipaddress.ip_address(host)
        return str(ip)
    except ValueError:
        pass

    # Not an IP - treat as domain name, encode to IDNA/ASCII
    try:
        ascii_host = host.encode('idna').decode('ascii').lower()
        return ascii_host
    except (ValueError, UnicodeError):
        raise ValueError("Invalid hostname format")


def _safe_url(url: str) -> str:
    """
    Sanitize URL for error messages.

    Removes userinfo, query, fragment, and control characters.
    Limits length to 300 characters.

    Args:
        url: Raw URL string

    Returns:
        Sanitized URL string safe for error messages
    """
    try:
        parsed = urlparse(url)

        # Remove userinfo from netloc
        netloc = parsed.netloc
        if '@' in netloc:
            netloc = netloc.split('@', 1)[1]

        # Build safe URL without query and fragment
        safe = f"{parsed.scheme}://{netloc}{parsed.path}"

        # Remove control characters
        safe = ''.join(c for c in safe if c.isprintable())

        # Limit length
        if len(safe) > 300:
            safe = safe[:297] + "..."

        return safe
    except Exception:
        return "<url>"


def _validate_remote_url(url: str) -> tuple:
    """
    Validate and parse remote URL.

    Args:
        url: URL string to validate

    Returns:
        Tuple of (parsed_url, hostname, port)

    Raises:
        ValueError: If URL is invalid, has disallowed components, or malformed
    """
    # Check for NUL, CR, LF in original string (urlparse silently removes them)
    if '\x00' in url or '\r' in url or '\n' in url:
        raise ValueError("URL contains invalid control characters")

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")

    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("URL scheme must be http or https")

    # Reject username/password
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")

    # Reject fragment
    if parsed.fragment:
        raise ValueError("URL must not contain fragment")

    # Require hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have hostname")

    # Parse and validate port
    if parsed.port is not None:
        try:
            port = parsed.port
            if not isinstance(port, int):
                raise ValueError("Invalid port")
        except ValueError:
            raise ValueError("Invalid port")

        if port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
    else:
        # Default port based on scheme
        port = 443 if parsed.scheme == 'https' else 80

    return (parsed, hostname, port)


def _default_resolver(host: str, port: int) -> tuple[str, ...]:
    """
    Default DNS resolver using socket.getaddrinfo.

    Args:
        host: Hostname to resolve
        port: Port number

    Returns:
        Tuple of normalized IP address strings (deduplicated, stable order)

    Raises:
        ValueError: If resolution fails or any IP is non-global
    """
    try:
        results = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except Exception:
        raise ValueError("DNS resolution failed") from None

    # Extract IPs, normalize immediately, dedupe by canonical form
    seen_canonical = set()
    canonical_ips = []

    for family, socktype, proto, canonname, sockaddr in results:
        ip_str = sockaddr[0]

        # Normalize immediately - rejects private/invalid
        try:
            canonical = _normalize_ip(ip_str)
        except ValueError:
            # Any private/invalid IP fails the whole resolution
            raise

        # Dedupe by canonical form
        if canonical not in seen_canonical:
            seen_canonical.add(canonical)
            canonical_ips.append(canonical)

    if not canonical_ips:
        raise ValueError("DNS resolution failed") from None

    return tuple(canonical_ips)


class _PinnedAddressAdapter(HTTPAdapter):
    """HTTPAdapter that pins connection to a specific IP address."""

    def __init__(self, *, original_hostname: str, pinned_ip: str, scheme: str, port: int):
        """
        Initialize pinned adapter.

        Args:
            original_hostname: Original hostname for SNI/Host header (ASCII form)
            pinned_ip: IP address to connect to
            scheme: 'http' or 'https'
            port: Port number

        Raises:
            ValueError: If parameters are invalid
        """
        super().__init__()

        # Validate scheme
        if scheme not in ('http', 'https'):
            raise ValueError("Scheme must be http or https")

        # Validate hostname
        if not original_hostname:
            raise ValueError("Original hostname is required")

        # Validate pinned_ip is public and canonical
        try:
            normalized = _normalize_ip(pinned_ip)
            if normalized != pinned_ip:
                raise ValueError("Pinned IP must be canonical normalized form")
        except ValueError:
            raise ValueError("Pinned IP is not globally routable")

        # Validate port
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("Port must be integer between 1 and 65535")

        self.original_hostname = original_hostname
        self.pinned_ip = pinned_ip
        self.scheme = scheme
        self.port = port
        self._closed = False  # Fix 5: Add closed flag for idempotence

        # Create single connection pool
        if scheme == 'https':
            self._pool = HTTPSConnectionPool(
                host=pinned_ip,
                port=port,
                server_hostname=original_hostname,
                assert_hostname=original_hostname,
            )
        else:
            self._pool = HTTPConnectionPool(
                host=pinned_ip,
                port=port,
            )

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Return the pinned connection pool."""
        return self._pool

    def get_connection(self, url, proxies=None):
        """Return the pinned connection pool (compatibility)."""
        return self._pool

    def send(self, request, **kwargs):
        """Send request through pinned pool, ignoring proxies."""
        # Force proxies to empty dict
        kwargs['proxies'] = {}
        return super().send(request, **kwargs)

    def request_url(self, request, proxies):
        """Return path_url only (no scheme/host)."""
        return request.path_url

    def add_headers(self, request, **kwargs):
        """Set Host header to original hostname."""
        super().add_headers(request, **kwargs)

        # Fix 2: Build Host header with IPv6 bracket handling
        # Check if original_hostname is an IPv6 address
        is_ipv6 = False
        try:
            ip = ipaddress.ip_address(self.original_hostname)
            is_ipv6 = isinstance(ip, ipaddress.IPv6Address)
        except ValueError:
            # Not an IP, it's a domain name
            pass

        # Build Host header
        if self.scheme == 'https' and self.port == 443:
            # Default HTTPS port
            if is_ipv6:
                host_header = f"[{self.original_hostname}]"
            else:
                host_header = self.original_hostname
        elif self.scheme == 'http' and self.port == 80:
            # Default HTTP port
            if is_ipv6:
                host_header = f"[{self.original_hostname}]"
            else:
                host_header = self.original_hostname
        else:
            # Non-default port: add :port
            if is_ipv6:
                host_header = f"[{self.original_hostname}]:{self.port}"
            else:
                host_header = f"{self.original_hostname}:{self.port}"

        request.headers['Host'] = host_header

    def close(self):
        """Close the pinned pool (idempotent)."""
        # Fix 5: Make close idempotent
        if self._closed:
            return
        self._closed = True

        if hasattr(self, '_pool') and self._pool:
            try:
                self._pool.close()
            except Exception:
                pass

        try:
            super().close()
        except Exception:
            pass


class _RequestsDownloader:
    """HTTP downloader using requests library."""

    def __init__(self, session=None):
        """
        Initialize downloader.

        Args:
            session: Optional requests.Session to use. If None, creates owned session.
        """
        self._closed = False
        self._lock = threading.RLock()

        if session is None:
            self._session = requests.Session()
            self._session.trust_env = False
            self._owns_session = True
        else:
            self._session = session
            self._owns_session = False

    def __call__(self, url: str, approved_ips: tuple[str, ...]) -> DownloadResponse:
        """
        Download from URL.

        Args:
            url: URL to download
            approved_ips: Tuple of approved IP addresses

        Returns:
            DownloadResponse object

        Raises:
            ValueError: If request fails
        """
        safe_url = _safe_url(url)

        # Validate URL
        try:
            parsed, hostname, port = _validate_remote_url(url)
        except ValueError:
            raise ValueError(f"Invalid URL: {safe_url}") from None

        # Fix 1: Convert hostname to ASCII form using IDNA
        try:
            ascii_hostname = _ascii_hostname(hostname)
        except ValueError:
            raise ValueError(f"Invalid hostname in URL: {safe_url}") from None

        # Fix 2: Build origin prefix with ASCII hostname and IPv6 bracket handling
        # Check if ascii_hostname is IPv6 address
        is_ipv6 = False
        try:
            ip = ipaddress.ip_address(ascii_hostname)
            is_ipv6 = isinstance(ip, ipaddress.IPv6Address)
        except ValueError:
            # Not an IP, it's a domain name
            pass

        # Build hostpart for origin prefix
        if is_ipv6:
            hostpart = f"[{ascii_hostname}]"
        else:
            hostpart = ascii_hostname

        # Format: scheme://hostpart[:port]/ (port only if non-default)
        if (parsed.scheme == 'https' and port == 443) or (parsed.scheme == 'http' and port == 80):
            # Default port - omit from prefix
            origin_prefix = f"{parsed.scheme}://{hostpart}/"
        else:
            # Non-default port - include it
            origin_prefix = f"{parsed.scheme}://{hostpart}:{port}/"

        # Validate approved_ips
        if not approved_ips or len(approved_ips) == 0:
            raise ValueError(f"No approved IPs for {safe_url}")

        # Validate and normalize all approved IPs
        normalized_approved = []
        for ip_str in approved_ips:
            try:
                normalized = _normalize_ip(ip_str)
            except ValueError:
                raise ValueError(f"Invalid or private IP in approved list for {safe_url}") from None
            normalized_approved.append(normalized)

        # Deduplicate
        seen = set()
        unique_approved = []
        for ip in normalized_approved:
            if ip not in seen:
                seen.add(ip)
                unique_approved.append(ip)

        if not unique_approved:
            raise ValueError(f"No valid approved IPs for {safe_url}")

        # Select first IP (deterministic)
        pinned_ip = unique_approved[0]

        # Thread-safe session manipulation
        with self._lock:
            # Fix 3: Snapshot adapters before modification - handle Mock sessions
            adapters_obj = getattr(self._session, 'adapters', None)
            if isinstance(adapters_obj, MutableMapping):
                # Real session with mapping adapters - snapshot as list
                adapters_before = list(adapters_obj.items())
                old_adapter = None  # Will use mapping restore mode
            else:
                # Mock session or non-mapping adapters - use fallback mode
                adapters_before = None
                old_adapter = self._session.get_adapter(url)

            # Create pinned adapter
            pinned_adapter = _PinnedAddressAdapter(
                original_hostname=ascii_hostname,  # Fix 1: Use ASCII hostname
                pinned_ip=pinned_ip,
                scheme=parsed.scheme,
                port=port
            )

            # Fix 4: Mount in try block to handle mount failures
            try:
                self._session.mount(origin_prefix, pinned_adapter)
            except Exception:
                # Mount failed - close adapter once and restore
                try:
                    pinned_adapter.close()
                except Exception:
                    pass
                try:
                    self._restore_adapters(adapters_before, origin_prefix, old_adapter)
                except Exception:
                    pass
                raise ValueError(f"Failed to mount adapter for {safe_url}") from None

            try:
                # Make request
                try:
                    response = self._session.get(
                        url,
                        stream=True,
                        allow_redirects=False,
                        timeout=(15, 60),
                    )
                except Exception:
                    # Close pinned adapter on failure
                    pinned_adapter.close()
                    raise ValueError(f"HTTP request failed for {safe_url}") from None

                # Fix 3: Restore adapter mapping to exact original state
                try:
                    self._restore_adapters(adapters_before, origin_prefix, old_adapter)
                except Exception:
                    # Failed to restore - close both and fail
                    try:
                        response.close()
                    except Exception:
                        pass
                    pinned_adapter.close()
                    raise ValueError(f"Failed to restore session state for {safe_url}") from None

                # Wrap response with cleanup
                try:
                    wrapped = _RequestsResponseWrapper(response, safe_url, cleanup=pinned_adapter)
                except Exception:
                    # Wrapper construction failed - close both
                    try:
                        response.close()
                    except Exception:
                        pass
                    pinned_adapter.close()
                    raise ValueError(f"HTTP response invalid for {safe_url}") from None

                return wrapped

            except Exception:
                # Any failure after mount: restore adapters
                try:
                    self._restore_adapters(adapters_before, origin_prefix, old_adapter)
                except Exception:
                    pass
                raise

    def _restore_adapters(self, adapters_snapshot, origin_prefix, old_adapter) -> None:
        """
        Restore session adapters to exact snapshot state.

        Args:
            adapters_snapshot: List of (prefix, adapter) tuples from before modification,
                             or None for fallback mode
            origin_prefix: Origin prefix that was mounted
            old_adapter: Old adapter to restore in fallback mode
        """
        if adapters_snapshot is not None:
            # Mapping mode: clear and restore from snapshot
            adapters_obj = getattr(self._session, 'adapters', None)
            if not isinstance(adapters_obj, MutableMapping):
                raise ValueError("Session adapters changed from MutableMapping")
            adapters_obj.clear()
            adapters_obj.update(adapters_snapshot)
        else:
            # Fallback mode: mount old adapter back
            self._session.mount(origin_prefix, old_adapter)

    def close(self) -> None:
        """Close owned session (idempotent)."""
        if self._owns_session and not self._closed and hasattr(self, '_session'):
            self._closed = True
            self._session.close()


class _RequestsResponseWrapper:
    """Wrapper for requests.Response implementing DownloadResponse protocol."""

    def __init__(self, response: requests.Response, safe_url: str, cleanup=None):
        """
        Initialize wrapper.

        Args:
            response: requests.Response object
            safe_url: Safe URL string for error messages
            cleanup: Optional object with close() method to call on wrapper close

        Raises:
            Exception: If response object is malformed
        """
        self._response = response
        self._safe_url = safe_url
        self._closed = False
        self._cleanup = cleanup

        # Extract status code (strict type check)
        if type(response.status_code) is int:
            self.status_code = response.status_code
        else:
            try:
                self.status_code = int(response.status_code)
            except (ValueError, TypeError):
                self.status_code = response.status_code

        # Normalize headers to lowercase keys
        self.headers = {k.lower(): v for k, v in response.headers.items()}

        # Extract peer IP
        self.peer_ip = self._extract_peer_ip()

    def _extract_peer_ip(self) -> str | None:
        """Extract peer IP from urllib3 connection."""
        try:
            # Try raw._connection.sock
            if hasattr(self._response.raw, '_connection'):
                conn = self._response.raw._connection
                if hasattr(conn, 'sock') and conn.sock:
                    peer = conn.sock.getpeername()
                    if peer:
                        return peer[0]

            # Try raw.connection.sock
            if hasattr(self._response.raw, 'connection'):
                conn = self._response.raw.connection
                if hasattr(conn, 'sock') and conn.sock:
                    peer = conn.sock.getpeername()
                    if peer:
                        return peer[0]

            # Try raw._fp.fp.raw._sock
            if hasattr(self._response.raw, '_fp'):
                fp = self._response.raw._fp
                if hasattr(fp, 'fp'):
                    fp2 = fp.fp
                    if hasattr(fp2, 'raw'):
                        raw_sock = fp2.raw
                        if hasattr(raw_sock, '_sock'):
                            sock = raw_sock._sock
                            if sock:
                                peer = sock.getpeername()
                                if peer:
                                    return peer[0]
        except Exception:
            pass

        return None

    def iter_bytes(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Iterate response body in chunks."""
        return self._response.iter_content(chunk_size=chunk_size)

    def close(self) -> None:
        """Close response and cleanup (idempotent)."""
        if not self._closed:
            self._closed = True
            try:
                self._response.close()
            finally:
                if self._cleanup:
                    try:
                        self._cleanup.close()
                    except Exception:
                        pass


class SourceLoader:
    """
    Configurable image source loader with security controls.

    Args:
        resolver: DNS resolver function (host, port) -> tuple[str, ...]
        downloader: HTTP downloader function (url, approved_ips) -> DownloadResponse
        max_redirects: Maximum number of redirects to follow (default 3)
    """

    def __init__(
        self,
        *,
        resolver=None,
        downloader=None,
        max_redirects: int = 3,
    ):
        # Validate max_redirects
        if isinstance(max_redirects, bool):
            raise TypeError("max_redirects must be int, not bool")
        if not isinstance(max_redirects, int):
            raise TypeError("max_redirects must be int")
        if max_redirects < 0:
            raise ValueError("max_redirects must be non-negative")

        self.max_redirects = max_redirects
        self.resolver = resolver or _default_resolver

        # Track whether we own the downloader
        if downloader is None:
            self._downloader_obj = _RequestsDownloader()
            self.downloader = self._downloader_obj
            self._owns_downloader = True
        else:
            self.downloader = downloader
            self._owns_downloader = False

    def close(self) -> None:
        """
        Close the loader and clean up resources.

        Only closes owned default downloader if it has a close method.
        Injected downloaders are not closed.
        """
        if self._owns_downloader and hasattr(self, '_downloader_obj'):
            self._downloader_obj.close()

    def _load_remote_http(self, value: str) -> LoadedSource:
        """
        Load a remote HTTP(S) URL as image source.

        Args:
            value: HTTP(S) URL string

        Returns:
            LoadedSource with sanitized filename, data, and MIME type

        Raises:
            ValueError: If URL is malformed, resolves to private IP, download fails,
                       or format validation fails
        """
        current_url = value
        redirect_count = 0

        while True:
            # Validate URL
            parsed, hostname, port = _validate_remote_url(current_url)
            safe_url = _safe_url(current_url)

            # Resolve DNS - catch only resolver exceptions and map to DNS errors
            try:
                resolved_ips = self.resolver(hostname, port)
            except Exception:
                raise ValueError(f"DNS resolution failed for {safe_url}") from None

            # Force result to be tuple and non-empty
            if not isinstance(resolved_ips, tuple):
                raise ValueError(f"DNS resolution failed for {safe_url}")
            if len(resolved_ips) == 0:
                raise ValueError(f"DNS resolution returned no IPs for {safe_url}")

            # Normalize and deduplicate IPs - let _normalize_ip errors propagate
            normalized_set = set()
            normalized_list = []
            for ip_str in resolved_ips:
                try:
                    normalized = _normalize_ip(ip_str)
                except ValueError as e:
                    # Re-raise with context about private/non-public IPs
                    raise ValueError(f"DNS resolved to private or non-public IP for {safe_url}") from None
                if normalized not in normalized_set:
                    normalized_set.add(normalized)
                    normalized_list.append(normalized)

            approved_ips = tuple(normalized_list)

            # Download through a sanitized exception boundary.  Injected
            # downloaders are untrusted and may include the full URL or other
            # secrets in their exception text.
            try:
                response = self.downloader(current_url, approved_ips)
            except Exception:
                raise ValueError(f"HTTP request failed for {safe_url}") from None

            if response is None:
                raise ValueError(f"HTTP request failed for {safe_url}")

            # From this point onward, every non-None response is owned by this
            # method and must be closed even if protocol validation fails.
            try:
                if (
                    not hasattr(response, 'status_code')
                    or not hasattr(response, 'headers')
                    or not hasattr(response, 'peer_ip')
                ):
                    raise ValueError(f"Invalid HTTP response from {safe_url}")

                # Verify status is int (strict type check)
                if type(response.status_code) is not int:
                    raise ValueError(f"Invalid HTTP response from {safe_url}")

                # Verify peer IP
                if response.peer_ip is None:
                    raise ValueError(f"Cannot verify peer IP for {safe_url}")

                # Normalize peer IP
                try:
                    normalized_peer = _normalize_ip(response.peer_ip)
                except ValueError:
                    raise ValueError(f"Peer IP is not globally routable for {safe_url}") from None

                # Check peer is in approved list
                if normalized_peer not in approved_ips:
                    raise ValueError(f"Peer IP mismatch for {safe_url}")

                # Handle 3xx redirects
                if 300 <= response.status_code < 400:
                    # Check redirect limit
                    if redirect_count >= self.max_redirects:
                        raise ValueError(f"Too many redirects for {safe_url}")

                    # Get Location header (case-insensitive)
                    location = None
                    for key, value in response.headers.items():
                        if key.lower() == 'location':
                            location = value
                            break

                    if not location:
                        raise ValueError(f"Redirect missing Location header for {safe_url}")

                    # Validate Location header BEFORE urljoin (urljoin silently removes CRLF)
                    if not isinstance(location, str) or not location:
                        raise ValueError(f"Invalid redirect Location for {safe_url}") from None
                    if '\x00' in location or '\r' in location or '\n' in location:
                        raise ValueError(f"Invalid redirect Location for {safe_url}") from None

                    # Resolve relative URL
                    next_url = urljoin(current_url, location)

                    # Validate next URL before continuing
                    try:
                        _validate_remote_url(next_url)
                    except ValueError:
                        raise ValueError(f"Invalid redirect Location for {safe_url}") from None

                    # Update for next iteration
                    current_url = next_url
                    redirect_count += 1
                    # Continue - finally will close the response
                    continue

                # Handle non-2xx status
                if not (200 <= response.status_code < 300):
                    raise ValueError(f"HTTP {response.status_code} for {safe_url}")

                # Validate Content-Type (case-insensitive)
                content_type = None
                for key, value in response.headers.items():
                    if key.lower() == 'content-type':
                        content_type = value
                        break

                if not content_type:
                    raise ValueError(f"Missing Content-Type header for {safe_url}")

                # Parse MIME type (remove parameters)
                mime_type = content_type.split(';')[0].strip().lower()

                if mime_type not in MIME_TO_FORMAT:
                    raise ValueError(f"Unsupported Content-Type for {safe_url}")

                # Stream download with size limit
                try:
                    # Get iterator explicitly
                    iterator = response.iter_bytes(chunk_size=8192)
                except Exception:
                    raise ValueError(f"Image response stream failed for {safe_url}") from None

                chunks = []
                total_size = 0

                try:
                    while True:
                        try:
                            chunk = next(iterator)
                        except StopIteration:
                            break
                        except Exception:
                            raise ValueError(f"Image response stream failed for {safe_url}") from None

                        # Validate chunk is bytes
                        if not isinstance(chunk, bytes):
                            raise ValueError(f"Image response stream failed for {safe_url}")

                        if chunk:
                            total_size += len(chunk)
                            # Check size limit - raise immediately without consuming more
                            if total_size > MAX_IMAGE_BYTES:
                                raise ValueError(
                                    f"Response exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB for {safe_url}"
                                )
                            chunks.append(chunk)
                except ValueError:
                    # Our own ValueError should propagate as-is
                    raise

                data = b''.join(chunks)

                if len(data) == 0:
                    raise ValueError(f"Empty response body for {safe_url}")

                # Inspect and validate image
                try:
                    info = inspect_image(data, declared_mime=mime_type)
                except ValueError:
                    # Map inspection errors to safe message
                    raise ValueError(f"Image MIME mismatch or invalid response from {safe_url}") from None

                # Generate filename from final URL path
                path_parts = parsed.path.split('/')
                raw_filename = path_parts[-1] if path_parts and path_parts[-1] else 'image'

                # Unquote (percent-decode) the filename
                try:
                    raw_filename = unquote(raw_filename)
                except Exception:
                    raw_filename = 'image'

                # Sanitize filename
                filename = _sanitize_filename_from_url(raw_filename, info.format)

                return LoadedSource(
                    filename=filename,
                    data=data,
                    mime_type=info.mime_type,
                )

            finally:
                # Always close response once
                try:
                    response.close()
                except Exception:
                    pass

    def load_sources(
        self,
        primary: ImageSource,
        references: tuple[ImageSource, ...]
    ) -> tuple[LoadedSource, ...]:
        """
        Load image sources (local files, data URLs, or remote HTTP(S)).

        Args:
            primary: Primary image source (must be first in output)
            references: Reference image sources (0-15 allowed)

        Returns:
            Tuple of LoadedSource with primary first, then references in order

        Raises:
            ValueError: If total sources > 16 or input validation fails
        """
        # Pre-validate total count BEFORE any I/O
        total = 1 + len(references)
        if total > 16:
            raise ValueError(f"Maximum 16 sources allowed, got {total}")

        # Validate primary
        if not isinstance(primary, ImageSource):
            raise ValueError("primary must be ImageSource")

        # Validate references
        if not isinstance(references, tuple):
            raise ValueError("references must be tuple")

        # Collect all sources for validation
        all_sources = [primary] + list(references)

        # Validate each source
        for src in all_sources:
            if not isinstance(src, ImageSource):
                raise ValueError("All sources must be ImageSource")
            if not isinstance(src.value, str):
                raise ValueError("Source value must be string")

            # Strip and check non-empty
            stripped = src.value.strip()
            if not stripped:
                raise ValueError("Source value must be non-empty")

            # Check for NUL bytes
            if '\x00' in src.value:
                raise ValueError("Source value must not contain NUL bytes")

        # Load each source
        results = []
        for src in all_sources:
            value = src.value.strip()  # Use stripped value for processing

            # Dispatch based on source type
            # Case-insensitive data: check
            if value.lower().startswith('data:'):
                loaded = _load_data_url(value)
            # Case-insensitive http/https check
            elif value.lower().startswith('http://') or value.lower().startswith('https://'):
                loaded = self._load_remote_http(value)
            # Check for other URL schemes (not Windows drive)
            elif _has_url_scheme(value):
                # Has a URL scheme but not http/https and not Windows drive
                parsed = urlparse(value)
                scheme = parsed.scheme.lower()
                if scheme in ('ftp', 'file', 'javascript', 'ws', 'wss', 'mailto', 'tel'):
                    raise ValueError(f"URL scheme not supported: {scheme}. Use HTTP or HTTPS URLs.")
                else:
                    raise ValueError(f"URL scheme not supported: {scheme}. Use HTTP or HTTPS URLs.")
            else:
                # Local file
                loaded = _load_local_file(value)

            results.append(loaded)

        return tuple(results)


def load_sources(
    primary: ImageSource,
    references: tuple[ImageSource, ...]
) -> tuple[LoadedSource, ...]:
    """
    Load image sources using a new SourceLoader instance.

    This is a convenience function that creates a fresh SourceLoader for each call
    and ensures proper cleanup.

    Args:
        primary: Primary image source (must be first in output)
        references: Reference image sources (0-15 allowed)

    Returns:
        Tuple of LoadedSource with primary first, then references in order

    Raises:
        ValueError: If total sources > 16 or input validation fails
    """
    loader = SourceLoader()
    try:
        return loader.load_sources(primary, references)
    finally:
        loader.close()

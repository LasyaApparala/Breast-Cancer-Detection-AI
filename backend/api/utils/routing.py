"""
Routing utility for deciding sync vs async classification processing.
Requirements: 11.1, 11.2
"""


def should_process_async(files: list, total_size_bytes: int) -> bool:
    """
    Determine whether a classification request should be processed asynchronously.

    Async processing is required when:
    - Total uploaded data exceeds 10 MB, OR
    - Any file is a DICOM file (requires CNN inference via the Imaging Pipeline)

    Args:
        files: List of uploaded file objects (UploadFile or similar with content_type attr).
        total_size_bytes: Total size of all files in bytes.

    Returns:
        True if the request should be processed asynchronously, False for synchronous.
    """
    has_dicom = any(
        getattr(f, "content_type", "") == "application/dicom" for f in files
    )
    return total_size_bytes > 10 * 1024 * 1024 or has_dicom

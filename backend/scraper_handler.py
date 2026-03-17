"""AWS Lambda handler for scheduled journal scraping."""
import logging
from app.scrapers.monitor import JournalMonitor
from app.utils.storage import read_json_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Scrape journals and generate digests for all users."""
    monitor = JournalMonitor()
    users = read_json_file("users.json")

    results = {"success": 0, "failed": 0, "errors": []}

    for email, user_data in users.items():
        try:
            monitor.generate_digest(user_id=email)
            results["success"] += 1
            logger.info(f"Generated digest for user: {email}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"user": email, "error": str(e)})
            logger.error(f"Failed to generate digest for user {email}: {e}")

    logger.info(f"Scraper complete: {results['success']} succeeded, {results['failed']} failed")
    return results

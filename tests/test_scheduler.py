import os
from unittest.mock import patch, MagicMock
from app.scheduler import start_scheduler, run_scrape_and_analyze

@patch("app.scheduler.AsyncIOScheduler")
@patch("app.scheduler.CronTrigger")
def test_start_scheduler_default_schedule(mock_cron_trigger, mock_asyncio_scheduler):
    # Setup mocks
    mock_scheduler_instance = MagicMock()
    mock_asyncio_scheduler.return_value = mock_scheduler_instance
    mock_trigger_instance = MagicMock()
    mock_cron_trigger.from_crontab.return_value = mock_trigger_instance

    # Ensure no environment variable for SCRAPE_SCHEDULE
    if "SCRAPE_SCHEDULE" in os.environ:
        del os.environ["SCRAPE_SCHEDULE"]

    # Call the function
    scheduler = start_scheduler()

    # Assertions
    mock_asyncio_scheduler.assert_called_once()
    mock_cron_trigger.from_crontab.assert_called_once_with("0 2 * * 1,4")
    mock_scheduler_instance.add_job.assert_called_once_with(
        run_scrape_and_analyze,
        mock_trigger_instance
    )
    mock_scheduler_instance.start.assert_called_once()
    assert scheduler == mock_scheduler_instance

@patch("app.scheduler.AsyncIOScheduler")
@patch("app.scheduler.CronTrigger")
def test_start_scheduler_custom_schedule(mock_cron_trigger, mock_asyncio_scheduler):
    # Setup mocks
    mock_scheduler_instance = MagicMock()
    mock_asyncio_scheduler.return_value = mock_scheduler_instance
    mock_trigger_instance = MagicMock()
    mock_cron_trigger.from_crontab.return_value = mock_trigger_instance

    # Set custom environment variable
    custom_cron = "0 12 * * *"
    with patch.dict(os.environ, {"SCRAPE_SCHEDULE": custom_cron}):
        # Call the function
        scheduler = start_scheduler()

    # Assertions
    mock_asyncio_scheduler.assert_called_once()
    mock_cron_trigger.from_crontab.assert_called_once_with(custom_cron)
    mock_scheduler_instance.add_job.assert_called_once_with(
        run_scrape_and_analyze,
        mock_trigger_instance
    )
    mock_scheduler_instance.start.assert_called_once()
    assert scheduler == mock_scheduler_instance

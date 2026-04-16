try:
    from .job_runner import start_scheduler
except ImportError:
    from job_runner import start_scheduler


if __name__ == "__main__":
    start_scheduler()

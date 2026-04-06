from redis import Redis
from rq import Queue
from app.config import get_settings

def check_queue():
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(settings.rq_queue_name, connection=connection)
    
    print(f"Jobs in queue '{settings.rq_queue_name}': {len(queue)}")
    for job_id in queue.job_ids:
        job = queue.fetch_job(job_id)
        if job:
            print(f"Job: {job.id} | Status: {job.get_status()} | Func: {job.func_name}")

if __name__ == "__main__":
    check_queue()

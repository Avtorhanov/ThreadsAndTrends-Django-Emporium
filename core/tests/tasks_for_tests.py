from django_tasks import task

CALLS: list[str] = []


@task()
def record_call():
    CALLS.append("called")


def not_a_task():
    return None

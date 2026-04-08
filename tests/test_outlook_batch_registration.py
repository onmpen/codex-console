import asyncio

from src.web.routes import registration


def test_start_outlook_batch_registration_schedules_registration_type(monkeypatch):
    captured = {}

    def fake_schedule(background_tasks, coroutine_func, *args):
        captured["background_tasks"] = background_tasks
        captured["coroutine_func"] = coroutine_func
        captured["args"] = args

    monkeypatch.setattr(registration, "_schedule_async_job", fake_schedule)

    request = registration.OutlookBatchRegistrationRequest(
        service_ids=[1, 2, 3],
        skip_registered=False,
        registration_type="parent",
    )

    response = asyncio.run(registration._start_outlook_batch_registration_internal(request))

    try:
        assert response.to_register == 3
        assert response.service_ids == [1, 2, 3]
        assert captured["coroutine_func"] is registration.run_outlook_batch_registration
        assert captured["args"][-1] == "parent"
    finally:
        registration.batch_tasks.pop(response.batch_id, None)


def test_run_outlook_batch_registration_passes_registration_type(monkeypatch):
    created_service_ids = []
    captured = {}

    class DummyDb:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_get_db():
        return DummyDb()

    def fake_create_registration_task(db, task_uuid, proxy, email_service_id):
        created_service_ids.append(email_service_id)

    async def fake_run_batch_registration(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(registration, "get_db", fake_get_db)
    monkeypatch.setattr(registration.crud, "create_registration_task", fake_create_registration_task)
    monkeypatch.setattr(registration, "run_batch_registration", fake_run_batch_registration)

    asyncio.run(
        registration.run_outlook_batch_registration(
            batch_id="batch-1",
            service_ids=[1, 2, 3],
            skip_registered=False,
            proxy=None,
            interval_min=5,
            interval_max=30,
            concurrency=2,
            mode="pipeline",
            registration_type="parent",
        )
    )

    assert created_service_ids == [1, 2, 3]
    assert captured["email_service_type"] == "outlook"
    assert captured["registration_type"] == "parent"
